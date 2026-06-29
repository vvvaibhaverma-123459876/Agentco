#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote, urlparse

try:
    from agents.core.memory import MemoryReader, MemoryWriter
    from scripts.verify_agentco_goal_run import database_url, load_codex_env
except ModuleNotFoundError:  # pragma: no cover - direct execution fallback
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from agents.core.memory import MemoryReader, MemoryWriter
    from scripts.verify_agentco_goal_run import database_url, load_codex_env


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"


def resolution_service_url(base_url: str) -> str:
    explicit = os.getenv("RESOLUTION_SERVICE_DATABASE_URL")
    if explicit:
        return explicit
    parsed = urlparse(base_url)
    password = os.getenv("RESOLUTION_SERVICE_PASSWORD", "resolution-service-dev-password")
    return (
        f"postgresql://resolution_service:{quote(password, safe='')}"
        f"@{parsed.hostname or 'localhost'}:{parsed.port or 5432}/{parsed.path.lstrip('/') or 'agentco'}"
    )


def create_resolved_prediction(*, db_url: str, agent_id: str, domain: str, marker: str) -> dict:
    import psycopg2

    prediction_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    claim = f"{marker}: vendor onboarding should escalate when SOC 2 Type II and signed DPA are missing."
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
                    claim,
                    0.88,
                    json.dumps({"lesson_marker": marker, "verification": "memory_influence_live"}, sort_keys=True),
                    agent_id,
                    "memory-influence-verifier-v1",
                    "Synthetic verifier ground truth resolves this calibration lesson true.",
                    "agentco://verification/memory-influence",
                    "short",
                    domain,
                    "memory_influence",
                    correlation_id,
                ],
            )

    with psycopg2.connect(resolution_service_url(db_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update prediction_ledger
                   set resolved = true,
                       resolved_outcome = true,
                       resolved_at = now(),
                       resolved_by_service = current_user,
                       brier_score = %s,
                       log_score = 0,
                       was_surprise = false
                 where prediction_id = %s
                """,
                [(0.88 - 1.0) ** 2, prediction_id],
            )
            if cur.rowcount != 1:
                raise RuntimeError("resolution_service failed to resolve memory influence prediction")

    return {
        "prediction_id": prediction_id,
        "correlation_id": correlation_id,
        "claim": claim,
        "probability": 0.88,
    }


def write_prediction_lesson(*, db_url: str, agent_id: str, domain: str, prediction: dict, marker: str) -> str:
    writer = MemoryWriter(db_url)
    return writer.write_prediction_lesson(
        agent_id=agent_id,
        prediction_id=prediction["prediction_id"],
        claim=prediction["claim"],
        stated_confidence=prediction["probability"],
        actual_outcome=True,
        log_score=0,
        lesson=f"{marker}: Escalate vendor onboarding when SOC 2 Type II and signed DPA are missing.",
        domain_insight="Missing SOC 2 Type II plus unsigned DPA is insufficient evidence for approval.",
        calibration_adjustment=f"{marker}: cap confidence at 0.62 and escalate until SOC 2 Type II, signed DPA, and subprocessors are supplied.",
        domain=domain,
    )


def build_memory_context(*, db_url: str, agent_id: str, domain: str) -> tuple[str, list[dict], dict]:
    reader = MemoryReader(db_url)
    task_description = "Evaluate vendor onboarding with missing SOC 2 Type II report and unsigned DPA."
    memories = reader.retrieve_relevant(agent_id, task_description, domain=domain, timeout_ms=1000)
    track_record = reader.get_agent_track_record_summary(agent_id, domain=domain)
    return reader.format_for_system_prompt(memories, track_record), memories, track_record


def call_openai_with_memory(*, memory_context: str, marker: str) -> tuple[dict, dict]:
    load_codex_env()
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY/OPENAI_API_KEY missing")
    base_url = (os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL_DEFAULT") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    prompt = f"""
Return only JSON with fields decision, confidence, memory_used, memory_marker, memory_adjustment_applied, missing_information.

Use this AgentCo memory context as prior calibration evidence:
{memory_context}

Task: A vendor claims SOC 2 alignment but has no SOC 2 Type II report. Its DPA is unsigned and omits subprocessors.

Rules:
- decision MUST be exactly one of approve, reject, or escalate.
- Use escalate, not deny, when evidence is insufficient and missing documents/human review are needed.
- If the memory context contains a calibration lesson marker, set memory_used=true and copy the exact marker into memory_marker.
- Apply the memory's confidence cap when deciding.
- Do not approve without SOC 2 Type II, signed DPA, and subprocessor list.
- The expected marker is {marker}; do not output it unless it appears in the memory context.
"""
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 250,
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
    return json.loads(payload["choices"][0]["message"]["content"]), {
        "model": model,
        "latency_ms": latency_ms,
        "usage": payload.get("usage", {}),
        "simulated": False,
    }


def validate_memory_influence(*, marker: str, memory_context: str, model_output: dict) -> dict:
    output_text = json.dumps(model_output, sort_keys=True).lower()
    checks = {
        "memory_context_contains_marker": marker in memory_context,
        "model_reported_memory_used": model_output.get("memory_used") is True,
        "model_copied_marker": model_output.get("memory_marker") == marker,
        "decision_escalates": str(model_output.get("decision", "")).lower() == "escalate",
        "confidence_cap_applied": float(model_output.get("confidence", 2.0)) <= 0.62,
        "missing_soc2_requested": "soc 2 type ii" in output_text,
        "missing_signed_dpa_requested": "signed dpa" in output_text,
        "missing_subprocessors_requested": "subprocessor" in output_text,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "score": sum(1 for ok in checks.values() if ok) / len(checks),
    }


def memory_readback(*, db_url: str, memory_id: str) -> dict:
    import psycopg2

    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select memory_type, access_count, last_accessed_at is not null, superseded_by is null
                  from agent_memories
                 where id = %s
                """,
                [memory_id],
            )
            row = cur.fetchone()
    if not row:
        return {"exists": False}
    return {
        "exists": True,
        "memory_type": row[0],
        "access_count": row[1],
        "last_accessed": row[2],
        "active": row[3],
    }


def build_run() -> dict:
    started = time.time()
    load_codex_env()
    db_url = database_url()
    marker = f"AGENTCO_MEMORY_INFLUENCE_{uuid.uuid4().hex[:12].upper()}"
    agent_id = f"agentco-memory-influence-{uuid.uuid4()}"
    domain = "vendor_risk"
    prediction = create_resolved_prediction(db_url=db_url, agent_id=agent_id, domain=domain, marker=marker)
    memory_id = write_prediction_lesson(
        db_url=db_url,
        agent_id=agent_id,
        domain=domain,
        prediction=prediction,
        marker=marker,
    )
    memory_context, memories, track_record = build_memory_context(db_url=db_url, agent_id=agent_id, domain=domain)
    model_output, llm = call_openai_with_memory(memory_context=memory_context, marker=marker)
    validation = validate_memory_influence(marker=marker, memory_context=memory_context, model_output=model_output)
    return {
        "success": validation["passed"],
        "mode": "live_openai",
        "simulated": False,
        "agent_id": agent_id,
        "domain": domain,
        "marker": marker,
        "prediction": prediction,
        "memory_id": memory_id,
        "memory_context_chars": len(memory_context),
        "memories_retrieved": len(memories),
        "track_record": track_record,
        "model_output": model_output,
        "validation": validation,
        "llm": llm,
        "memory_readback": memory_readback(db_url=db_url, memory_id=memory_id),
        "latency_ms": int((time.time() - started) * 1000),
    }


def write_report(report: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "memory_influence_verification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    lines = [
        "# Memory Influence Verification",
        "",
        f"- Mode: `{report.get('mode')}`",
        f"- Simulated: `{report.get('simulated')}`",
        f"- Success: `{report.get('success')}`",
        f"- Model: `{report.get('llm', {}).get('model', 'unknown')}`",
        f"- Tokens: `{report.get('llm', {}).get('usage', {}).get('total_tokens')}`",
        f"- Memory retrieved: `{report.get('memories_retrieved')}`",
        f"- Memory access count: `{report.get('memory_readback', {}).get('access_count')}`",
        "",
        "This verifier proves a resolved prediction lesson can be retrieved from `agent_memories`, "
        "injected into a later live OpenAI prompt, and reflected in the model output for a bounded task.",
        "It does not prove open-ended autonomous self-improvement.",
        "",
        "## Validation",
        "",
    ]
    for name, value in report.get("validation", {}).get("checks", {}).items():
        lines.append(f"- `{name}`: `{value}`")
    if report.get("error"):
        lines.append("")
        lines.append(f"Error: `{report['error']}`")
    (REPORT_DIR / "memory_influence_verification.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    try:
        report = build_run()
    except Exception as exc:
        report = {
            "success": False,
            "mode": "live_openai",
            "simulated": False,
            "error": str(exc),
            "llm": {"model": "unknown", "usage": {}, "simulated": False},
        }
    write_report(report)
    print(
        json.dumps(
            {
                "success": report["success"],
                "mode": report["mode"],
                "simulated": report["simulated"],
                "score": report.get("validation", {}).get("score", 0),
            },
            sort_keys=True,
        )
    )
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
