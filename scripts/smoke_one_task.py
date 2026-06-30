#!/usr/bin/env python3
"""
Single-task smoke test: dispatch ONE real task through the full stack.

What this exercises (when all services are up):
  - Real LLM call (via configured provider)
  - Real calibration engine: pre-registers a prediction, runs trusted_confidence
  - Real audit entry written to Postgres decision_log
  - Real Kafka event published via event_bus tool
  - Spend guardrail check (prints tokens used)

Usage:
  export LLM_PROVIDER=openai
  export LLM_API_KEY=sk-...
  export LLM_BASE_URL=https://api.openai.com/v1    # optional
  export LLM_MODEL_DEFAULT=gpt-4o-mini             # optional
  export DATABASE_URL=postgresql://...             # optional (defaults to local pg)
  python3 scripts/smoke_one_task.py

To switch providers without code changes:
  LLM_PROVIDER=anthropic LLM_API_KEY=sk-ant-... LLM_MODEL_FRONTIER=claude-haiku-4-5-20251001 \\
      python3 scripts/smoke_one_task.py

  LLM_PROVIDER=ollama LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL_DEFAULT=qwen2.5:7b \\
      python3 scripts/smoke_one_task.py

Exit codes:
  0 — LLM + calibration + DB audit legs all passed
  1 — at least one required leg failed (partial success printed per leg)
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

# Ensure repo root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _check_env():
    provider = os.environ.get("LLM_PROVIDER", "ollama")
    api_key = os.environ.get("LLM_API_KEY", "")
    if provider != "ollama" and not api_key:
        print("[SMOKE] ERROR: LLM_API_KEY not set (required for non-ollama providers).")
        print("        Set LLM_PROVIDER=ollama + LLM_BASE_URL if you want a local model.")
        sys.exit(1)
    return provider


def _print_section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main():
    provider = _check_env()

    from runtime.base_agent.provider_config import validate_all_tiers, resolve_tier_config
    from runtime.base_agent.llm_client import client_for_tier
    from runtime.base_agent.model_tiers import tier_for
    from runtime.base_agent.spend_guardrail import SpendGuardrail, SpendCapExceeded
    from runtime.base_agent.structured_output import get_validated_output
    from runtime.escalation.escalation_gate import EscalationGate

    _print_section("SMOKE: config validation")
    try:
        validate_all_tiers()
        print("[OK] validate_all_tiers() passed")
    except Exception as exc:
        print(f"[FAIL] validate_all_tiers(): {exc}")
        sys.exit(1)

    agent_id = "ceo-agent"
    tier = tier_for(agent_id)
    cfg = resolve_tier_config(tier)
    print(f"[OK] agent={agent_id} tier={tier} provider={cfg.provider} model={cfg.model}")

    # ── CALIBRATION LEG ──────────────────────────────────────────────────────
    _print_section("SMOKE: calibration engine leg (in-memory prediction ledger)")
    cal_ok = False
    prediction_id = None
    trusted_conf = None
    try:
        from calibration import create_calibration_engine
        cal = create_calibration_engine()  # in-memory; no DB required
        ledger = cal["ledger"]
        trust = cal["trust"]

        from calibration.ledger.prediction_ledger import PredictionRegistration
        reg = PredictionRegistration(
            claim="smoke test: quarterly financial report review will surface no anomalies",
            probability=0.78,
            confidence_basis={"source": "smoke_one_task"},
            producing_agent_id=agent_id,
            producing_prompt_version="smoke-1.0",
            resolution_criterion="auditor confirms no anomalies found",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=7),
            ground_truth_source="external_auditor",
            horizon_class="short",
            domain="general",
            claim_type="general",
        )
        prediction_id = ledger.pre_register(reg)

        from runtime.confidence.confidence_v2 import ConfidenceV2
        conf_engine = ConfidenceV2(trust_controller=trust)
        trusted_out = conf_engine.get_trusted(
            agent_id=agent_id, stated=0.78,
            domain="general", claim_type="general", horizon_class="short",
        )
        trusted_conf = trusted_out.trusted_confidence
        cal_ok = True
        print(f"[OK] prediction_id={prediction_id}")
        print(f"[OK] stated_confidence=0.78 trusted_confidence={trusted_conf:.4f}")
        if trusted_out.degraded:
            print(f"[WARN] confidence degraded (n_samples={trusted_out.n_samples})")
    except Exception as exc:
        print(f"[FAIL] calibration engine: {exc}")

    # ── LLM LEG ──────────────────────────────────────────────────────────────
    _print_section("SMOKE: LLM call leg")
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"},
        },
        "required": ["action", "confidence"],
    }
    messages = [
        {"role": "system", "content": "You are an AI agent. Respond in strict JSON."},
        {
            "role": "user",
            "content": (
                "Evaluate this task: 'Review the quarterly financial report.' "
                "Respond ONLY with JSON matching: "
                '{"action": "...", "confidence": 0.0-1.0, "reasoning": "..."}'
            ),
        },
    ]

    llm_ok = False
    llm_result = None
    try:
        client = client_for_tier(tier)
        guardrail = SpendGuardrail(agent_id=agent_id, escalation=EscalationGate())
        gate = EscalationGate()
        result = get_validated_output(client, cfg.model, messages, schema, gate, guardrail=guardrail)
        llm_result = result
        llm_ok = True
        print(f"[OK] LLM returned: {json.dumps(result, indent=2)}")
        print(f"[OK] tokens_used={guardrail.tokens_used}")
    except SpendCapExceeded as exc:
        print(f"[BLOCKED] SpendCapExceeded: {exc}")
    except Exception as exc:
        print(f"[FAIL] LLM call: {exc}")

    # ── AUDIT LOG LEG ────────────────────────────────────────────────────────
    _print_section("SMOKE: decision_log (audit) leg (real Postgres)")
    audit_ok = False
    log_id = None
    chain_hash = None
    try:
        import psycopg2, hashlib
        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://agentco:password@localhost:5433/agentco?host=/tmp"
        )
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        log_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chain_hash
                  FROM decision_log
                 WHERE chain_hash ~ '^[0-9a-f]{64}$'
                   AND prev_hash ~ '^[0-9a-f]{64}$'
                 ORDER BY timestamp DESC, log_id DESC
                 LIMIT 1
                """
            )
            row = cur.fetchone()
            prev_hash = row[0] if row else "0" * 64
            audit_fields = {
                "log_id": log_id,
                "timestamp": ts,
                "prev_hash": prev_hash,
                "agent_id": agent_id,
                "action_type": "decision",
                "input_summary": "smoke: quarterly financial report review",
                "output_summary": json.dumps(llm_result or {"smoke": True}),
                "confidence_score": round(float(trusted_conf or 0.78), 3),
                "risk_level": "low",
                "human_approved": False,
                "human_approver_id": None,
                "downstream_events": [],
                "session_id": None,
            }
            canonical_order = [
                "log_id",
                "timestamp",
                "prev_hash",
                "agent_id",
                "action_type",
                "input_summary",
                "output_summary",
                "confidence_score",
                "risk_level",
                "human_approved",
                "human_approver_id",
                "downstream_events",
                "session_id",
            ]
            canonical_fields = {key: audit_fields[key] for key in canonical_order}
            score = canonical_fields.get("confidence_score")
            if isinstance(score, float):
                score = round(score, 3)
                canonical_fields["confidence_score"] = score
            if isinstance(score, float) and score.is_integer():
                canonical_fields["confidence_score"] = int(score)
            content = json.dumps(canonical_fields, separators=(",", ":"))
            chain_hash = hashlib.sha256((prev_hash + content).encode()).hexdigest()
            cur.execute(
                """INSERT INTO decision_log
                   (log_id, agent_id, action_type, input_summary, output_summary,
                    confidence_score, risk_level, human_approved, human_approver_id,
                    downstream_events, session_id, timestamp,
                    chain_hash, prev_hash)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    log_id, agent_id, "decision",
                    audit_fields["input_summary"],
                    audit_fields["output_summary"],
                    audit_fields["confidence_score"], "low", False, None,
                    [], None, ts, chain_hash, prev_hash,
                )
            )
            cur.execute(
                "SELECT chain_hash FROM decision_log WHERE log_id=%s", (log_id,)
            )
            row = cur.fetchone()
        conn.close()
        assert row and len(row[0]) == 64, "audit entry not found or hash_chain missing"
        audit_ok = True
        print(f"[OK] log_id={log_id}")
        print(f"[OK] chain_hash={row[0][:16]}...")
    except Exception as exc:
        print(f"[FAIL] decision_log: {exc}")

    # ── KAFKA LEG ────────────────────────────────────────────────────────────
    _print_section("SMOKE: Kafka event_bus leg")
    kafka_ok = False
    kafka_event_id = str(uuid.uuid4())
    try:
        import hmac as _hmac
        from kafka import KafkaProducer
        brokers = os.environ.get("KAFKA_BROKERS", "localhost:9092")
        signing_key = os.environ.get("EVENT_BUS_SIGNING_KEY", "dev-key-replace-in-production")
        event = {
            "event_id": kafka_event_id,
            "event_type": "engineering.smoke_test",
            "producer_agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence_score": float(trusted_conf or 0.78),
            "payload": {"prediction_id": prediction_id, "log_id": log_id},
            "correlation_id": str(uuid.uuid4()),
            "risk_level": "low",
            "requires_ack": False,
            "ttl_seconds": 3600,
        }
        signature = _hmac.new(
            signing_key.encode(), json.dumps(event).encode(), __import__("hashlib").sha256
        ).hexdigest()
        producer = KafkaProducer(
            bootstrap_servers=brokers.split(","),
            value_serializer=lambda v: json.dumps(v).encode(),
            request_timeout_ms=5000,
        )
        producer.send("agentco.events", key=kafka_event_id.encode(), value={**event, "signature": signature})
        producer.flush(timeout=5)
        producer.close()
        kafka_ok = True
        print(f"[OK] Kafka event_id={kafka_event_id} published to agentco.events")
    except Exception as exc:
        print(f"[SKIP/FAIL] Kafka: {exc}")
        print("       (Kafka not running — acceptable in dev; required in staging/prod)")

    # ── SUMMARY ─────────────────────────────────────────────────────────────
    _print_section("SMOKE SUMMARY")
    legs = {
        "Config validation": True,   # would have exited above if failed
        "Calibration engine (in-memory)": cal_ok,
        "LLM call": llm_ok,
        "decision_log / audit (Postgres)": audit_ok,
        "Kafka event_bus": kafka_ok,
    }
    for leg, ok in legs.items():
        print(f"  {'[OK]   ' if ok else '[FAIL] '} {leg}")

    required_ok = cal_ok and audit_ok
    if not required_ok:
        print("\n[SMOKE] FAILED — calibration + DB legs must pass.")
        sys.exit(1)
    elif not llm_ok:
        print("\n[SMOKE] PARTIAL — calibration + DB OK but LLM call failed (check provider config).")
        sys.exit(1)
    else:
        note = " (Kafka unavailable — infra gap)" if not kafka_ok else " (all legs)"
        print(f"\n[SMOKE] PASSED{note}")
        sys.exit(0)


if __name__ == "__main__":
    main()
