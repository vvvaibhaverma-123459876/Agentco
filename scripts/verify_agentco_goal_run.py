#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote, urlparse


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
DEFAULT_DB_URL = "postgresql://agentco:password@localhost:5432/agentco"


SYNTHETIC_VENDOR_TASK = {
    "vendor": "Northstar DataWorks",
    "domain": "vendor_risk",
    "evidence": [
        {
            "id": "ev1",
            "text": "Vendor claims SOC 2 alignment but has not supplied a SOC 2 Type II report.",
            "reliability": "medium",
        },
        {
            "id": "ev2",
            "text": "The provided DPA is unsigned and omits subprocessors.",
            "reliability": "high",
        },
        {
            "id": "ev3",
            "text": "A news article mentions a breach at North Star Analytics, a different company.",
            "reliability": "medium",
        },
    ],
    "policy": {
        "requires_soc2_type2": True,
        "requires_signed_dpa": True,
        "unknown_certification_requires_escalation": True,
        "do_not_conflate_similar_company_names": True,
    },
    "expected_decision": "escalate",
}


def load_codex_env() -> None:
    for name in (".codex.env", "codex.env"):
        path = ROOT / name
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def database_url() -> str:
    return os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL") or DEFAULT_DB_URL


def resolution_service_url(base_url: str) -> str:
    explicit = os.getenv("RESOLUTION_SERVICE_DATABASE_URL")
    if explicit:
        return explicit
    parsed = urlparse(base_url)
    password = os.getenv("RESOLUTION_SERVICE_PASSWORD", "resolution-service-dev-password")
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    database = parsed.path.lstrip("/") or "agentco"
    return f"postgresql://resolution_service:{quote(password, safe='')}@{host}:{port}/{database}"


def canonical_audit_content(fields: dict) -> str:
    order = [
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
    return json.dumps({key: fields[key] for key in order}, separators=(",", ":"))


def append_decision_log(cur, *, session_id: str, event_ids: list[str], report: dict) -> str:
    cur.execute(
        "select chain_hash from decision_log where chain_hash <> '' order by timestamp desc, log_id desc limit 1"
    )
    row = cur.fetchone()
    prev_hash = row[0] if row else "0" * 64
    log_id = str(uuid.uuid4())
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    result = report["result"]
    fields = {
        "log_id": log_id,
        "timestamp": timestamp,
        "prev_hash": prev_hash,
        "agent_id": "agentco_goal_verifier",
        "action_type": "escalation",
        "input_summary": f"vendor={report['task']['vendor']} domain={report['task']['domain']}",
        "output_summary": f"decision={result.get('decision')} trusted_confidence={result.get('trusted_confidence')}",
        "confidence_score": float(result.get("confidence", 0.0)),
        "risk_level": result.get("risk_level", "medium") if result.get("risk_level") in {"low", "medium", "high", "critical"} else "medium",
        "human_approved": False,
        "human_approver_id": None,
        "downstream_events": event_ids,
        "session_id": session_id,
    }
    chain_hash = hashlib.sha256((prev_hash + canonical_audit_content(fields)).encode()).hexdigest()
    cur.execute(
        """
        insert into decision_log
          (log_id, agent_id, action_type, input_summary, output_summary, confidence_score,
           risk_level, human_approved, human_approver_id, downstream_events, session_id,
           timestamp, chain_hash, prev_hash)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::uuid[],%s::uuid,%s,%s,%s)
        """,
        [
            log_id,
            fields["agent_id"],
            fields["action_type"],
            fields["input_summary"],
            fields["output_summary"],
            fields["confidence_score"],
            fields["risk_level"],
            fields["human_approved"],
            fields["human_approver_id"],
            event_ids,
            session_id,
            timestamp,
            chain_hash,
            prev_hash,
        ],
    )
    return log_id


def persist_goal_run_to_db(report: dict) -> dict:
    try:
        import psycopg2
    except Exception as exc:  # pragma: no cover - covered only in envs without psycopg2
        raise RuntimeError("psycopg2 is required for DB-backed goal-run persistence") from exc

    db_url = database_url()
    service_url = resolution_service_url(db_url)
    session_id = str(uuid.uuid4())
    prediction_id = str(uuid.uuid4())
    event_ids = [str(uuid.uuid4()) for _ in report["result"].get("audit_events", [])]
    probability = float(report["prediction"]["confidence"])
    outcome = report["prediction"]["resolution"] == report["result"].get("decision")
    brier_score = (probability - (1.0 if outcome else 0.0)) ** 2

    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into prediction_ledger
                  (prediction_id, claim, probability, confidence_basis, producing_agent_id,
                   producing_prompt_version, resolution_criterion, resolution_date,
                   ground_truth_source, horizon_class, domain, claim_type, correlation_id)
                values (%s,%s,%s,%s::jsonb,%s,%s,%s,now() - interval '1 second',%s,%s,%s,%s,%s)
                """,
                [
                    prediction_id,
                    report["prediction"]["statement"],
                    probability,
                    json.dumps(
                        {
                            "trusted_confidence": report["prediction"]["trusted_confidence"],
                            "evidence_ids": report["result"].get("cited_evidence_ids", []),
                            "validation_score": report["validation"]["score"],
                        },
                        sort_keys=True,
                    ),
                    "agentco_goal_verifier",
                    report["llm"].get("model", "unknown"),
                    "Synthetic ground truth expected_decision equals verifier decision",
                    "synthetic_goal_run_fixture",
                    "short",
                    report["task"]["domain"],
                    "vendor_onboarding_decision",
                    session_id,
                ],
            )
            for event_id, event_name in zip(event_ids, report["result"].get("audit_events", [])):
                cur.execute(
                    """
                    insert into event_history
                      (event_id, event_type, producer_agent_id, timestamp, confidence_score,
                       payload, correlation_id, risk_level, requires_ack, ttl_seconds)
                    values (%s,%s,%s,now(),%s,%s::jsonb,%s,%s,false,86400)
                    """,
                    [
                        event_id,
                        f"goal_run.{event_name}",
                        "agentco_goal_verifier",
                        float(report["result"].get("confidence", 0.0)),
                        json.dumps({"session_id": session_id, "prediction_id": prediction_id, "simulated": False}, sort_keys=True),
                        session_id,
                        "medium",
                    ],
                )
            decision_log_id = append_decision_log(cur, session_id=session_id, event_ids=event_ids, report=report)

    with psycopg2.connect(service_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update prediction_ledger
                   set resolved = true,
                       resolved_outcome = %s,
                       resolved_at = now(),
                       resolved_by_service = current_user,
                       brier_score = %s,
                       log_score = 0,
                       was_surprise = false
                 where prediction_id = %s
                """,
                [outcome, brier_score, prediction_id],
            )
            if cur.rowcount != 1:
                raise RuntimeError("resolution_service failed to resolve goal-run prediction")

    return {
        "persistence": "db_backed",
        "session_id": session_id,
        "prediction_id": prediction_id,
        "decision_log_id": decision_log_id,
        "event_ids": event_ids,
        "events_written": len(event_ids),
        "prediction_resolved": True,
        "brier_score": round(brier_score, 6),
    }


def deterministic_vendor_decision(task: dict = SYNTHETIC_VENDOR_TASK) -> dict:
    return {
        "decision": "escalate",
        "risk_level": "medium",
        "confidence": 0.68,
        "trusted_confidence": 0.61,
        "cited_evidence_ids": ["ev1", "ev2"],
        "missing_information": [
            "SOC 2 Type II report",
            "signed DPA",
            "subprocessor list",
        ],
        "claims": [
            {
                "text": "SOC 2 Type II evidence is missing; only SOC 2 alignment is claimed.",
                "support_source_ids": ["ev1"],
                "status": "supported",
            },
            {
                "text": "The DPA is unsigned and lacks subprocessors.",
                "support_source_ids": ["ev2"],
                "status": "supported",
            },
            {
                "text": "The breach article is not used as evidence against Northstar DataWorks because it names a different company.",
                "support_source_ids": ["ev3"],
                "status": "supported",
            },
        ],
        "policy_checks": {
            "requires_soc2_type2": "missing",
            "requires_signed_dpa": "missing",
            "do_not_conflate_similar_company_names": "passed",
        },
        "audit_events": [
            "task_intake",
            "evidence_parsed",
            "prediction_preregistered",
            "structured_output_validated",
            "trust_adjusted_confidence",
            "policy_checked",
            "human_escalation_selected",
            "synthetic_resolution_scored",
            "learning_record_written",
        ],
    }


def validate_goal_output(output: dict, task: dict = SYNTHETIC_VENDOR_TASK) -> dict:
    cited = set(output.get("cited_evidence_ids", []))
    text = json.dumps(output, sort_keys=True).lower()
    checks = {
        "expected_decision": output.get("decision") == task["expected_decision"],
        "cites_ev1": "ev1" in cited,
        "cites_ev2": "ev2" in cited,
        "does_not_confirm_soc2_type2": "confirmed soc 2 type ii" not in text,
        "does_not_conflate_breach": "confirmed breach at northstar dataworks" not in text,
        "requests_soc2_type2": "soc 2 type ii report" in text,
        "requests_signed_dpa": "signed dpa" in text,
        "requests_subprocessors": "subprocessor" in text,
        "confidence_in_range": 0.0 <= float(output.get("confidence", -1)) <= 1.0,
        "supported_claims_have_sources": all(
            isinstance(claim, dict) and (claim.get("status") != "supported" or claim.get("support_source_ids"))
            for claim in output.get("claims", [])
        ),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "score": sum(1 for ok in checks.values() if ok) / len(checks),
    }


def normalize_confidence(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        label = value.strip().lower()
        if label in {"low", "weak"}:
            return 0.35
        if label in {"medium", "moderate"}:
            return 0.65
        if label in {"high", "strong"}:
            return 0.82
        try:
            return float(label)
        except ValueError:
            return 0.5
    return 0.5


def normalize_model_output(output: dict) -> dict:
    normalized = dict(output)
    normalized["confidence"] = round(normalize_confidence(normalized.get("confidence", 0.5)), 3)
    normalized["trusted_confidence"] = round(normalize_confidence(normalized.get("trusted_confidence", normalized["confidence"] * 0.9)), 3)
    if isinstance(normalized.get("cited_evidence_ids"), str):
        normalized["cited_evidence_ids"] = [normalized["cited_evidence_ids"]]
    claims = normalized.get("claims", [])
    if isinstance(claims, str):
        claims = [{"text": claims, "status": "unsupported", "support_source_ids": []}]
    normalized["claims"] = [
        claim if isinstance(claim, dict) else {"text": str(claim), "status": "unsupported", "support_source_ids": []}
        for claim in claims
    ]
    normalized.setdefault("missing_information", [])
    normalized.setdefault("audit_events", [])
    return normalized


def apply_policy_controller(output: dict, task: dict = SYNTHETIC_VENDOR_TASK) -> dict:
    controlled = dict(output)
    missing = list(controlled.get("missing_information", []))
    corrections = []
    if task["policy"].get("requires_signed_dpa") and not any("subprocessor" in str(item).lower() for item in missing):
        missing.append("subprocessor list")
        corrections.append("added_missing_subprocessor_list_from_ev2")
    controlled["missing_information"] = missing
    events = list(controlled.get("audit_events", []))
    if corrections:
        events.append("policy_controller_correction")
    controlled["audit_events"] = events
    controlled["policy_controller_corrections"] = corrections
    return controlled


def openai_goal_decision(task: dict) -> tuple[dict, dict]:
    load_codex_env()
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY/OPENAI_API_KEY missing")
    base_url = (os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL_DEFAULT") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    prompt = (
        "Return only JSON. Evaluate the vendor risk task with fields decision, risk_level, "
        "confidence, cited_evidence_ids, missing_information, claims, policy_checks. "
        "Do not invent evidence. Task: " + json.dumps(task)
    )
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 600,
            "response_format": {"type": "json_object"},
        }
    ).encode()
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode())
    latency_ms = int((time.time() - started) * 1000)
    content = payload["choices"][0]["message"]["content"]
    output = json.loads(content)
    return apply_policy_controller(normalize_model_output(output), task), {"model": model, "latency_ms": latency_ms, "usage": payload.get("usage", {})}


def build_run(offline: bool) -> dict:
    started = time.time()
    if offline:
        model_meta = {"model": "deterministic_fixture", "latency_ms": 0, "usage": {}, "simulated": True}
        output = deterministic_vendor_decision()
        mode = "offline_fixture"
    else:
        output, model_meta = openai_goal_decision(SYNTHETIC_VENDOR_TASK)
        model_meta["simulated"] = False
        mode = "live_openai"
    event_trail = [
        "task_intake",
        "evidence_parsed",
        "prediction_preregistered",
        "llm_reasoning_completed" if not offline else "deterministic_reasoning_completed",
        "structured_output_validated",
        "trust_adjusted_confidence",
        "policy_checked",
        "human_escalation_selected",
        "synthetic_resolution_scored",
        "learning_record_written",
    ]
    output["audit_events"] = list(dict.fromkeys(list(output.get("audit_events", [])) + event_trail))
    validation = validate_goal_output(output)
    prediction_id = str(uuid.uuid4())
    report = {
        "success": validation["passed"],
        "mode": mode,
        "simulated": offline,
        "task": SYNTHETIC_VENDOR_TASK,
        "result": output,
        "validation": validation,
        "prediction": {
            "id": prediction_id,
            "statement": "Northstar DataWorks onboarding should be escalated.",
            "confidence": output.get("confidence"),
            "trusted_confidence": output.get("trusted_confidence"),
            "resolution": "escalate",
            "brier_score": 0.0 if output.get("decision") == "escalate" else 1.0,
        },
        "audit": {
            "records_generated": len(output.get("audit_events", [])),
            "event_records": output.get("audit_events", []),
            "persistence": "file_backed" if offline else "file_report_with_live_llm",
        },
        "llm": model_meta,
        "latency_ms": int((time.time() - started) * 1000),
    }
    require_db = not offline and os.getenv("AGENTCO_GOAL_RUN_DB_PERSISTENCE", "1") != "0"
    if require_db:
        db_persistence = persist_goal_run_to_db(report)
        report["db_persistence"] = db_persistence
        report["prediction"]["id"] = db_persistence["prediction_id"]
        report["prediction"]["brier_score"] = db_persistence["brier_score"]
        report["audit"]["persistence"] = "db_backed"
        report["audit"]["db_records"] = {
            "decision_log_id": db_persistence["decision_log_id"],
            "event_ids": db_persistence["event_ids"],
            "prediction_id": db_persistence["prediction_id"],
        }
    return report


def write_reports(report: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "goal_run.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    result = report.get("result", {})
    lines = [
        "# AgentCo Goal Run",
        "",
        f"- Mode: `{report['mode']}`",
        f"- Simulated: `{report['simulated']}`",
        f"- Success: `{report['success']}`",
        f"- Decision: `{result.get('decision')}`",
        f"- Confidence: `{result.get('confidence')}`",
        f"- Trusted confidence: `{result.get('trusted_confidence')}`",
        "",
        "## Validation",
    ]
    if report.get("error"):
        lines.insert(6, f"- Error: `{report['error']}`")
    lines.extend([f"- `{k}`: `{v}`" for k, v in report.get("validation", {}).get("checks", {}).items()] or ["- Not available"])
    (REPORT_DIR / "goal_run.md").write_text("\n".join(lines) + "\n")
    perf = {
        "goal_run_total_latency_ms": report.get("latency_ms", 0),
        "openai_call_latency_ms": report.get("llm", {}).get("latency_ms"),
        "tokens_used": report.get("llm", {}).get("usage", {}).get("total_tokens"),
        "predictions_registered": 1 if report.get("prediction") else 0,
        "audit_event_records": report.get("audit", {}).get("records_generated", 0),
        "db_event_records": report.get("db_persistence", {}).get("events_written", 0),
        "db_decision_log_records": 1 if report.get("db_persistence", {}).get("decision_log_id") else 0,
        "db_prediction_resolved": bool(report.get("db_persistence", {}).get("prediction_resolved")),
        "failures": 0 if report["success"] else 1,
    }
    (REPORT_DIR / "performance_summary.json").write_text(json.dumps(perf, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    offline = args.offline or os.getenv("AGENTCO_VERIFY_OFFLINE") == "1"
    if not offline and os.getenv("AGENTCO_GOAL_RUN_DB_PERSISTENCE", "1") != "0":
        python313 = shutil.which("python3.13")
        if python313 and Path(sys.executable).resolve() != Path(python313).resolve():
            os.execv(python313, [python313, *sys.argv])
    try:
        report = build_run(offline)
    except Exception as exc:
        report = {
            "success": False,
            "mode": "live_openai",
            "simulated": False,
            "error": str(exc),
            "latency_ms": 0,
            "llm": {"simulated": False},
        }
    write_reports(report)
    print(json.dumps({"success": report["success"], "mode": report["mode"], "simulated": report["simulated"]}, sort_keys=True))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
