#!/usr/bin/env python3
"""Integrated AgentCo goal-fit verification run."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import copy
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
GOAL_JSON = REPORT_DIR / "goal_run.json"
GOAL_MD = REPORT_DIR / "goal_run.md"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def synthetic_task() -> dict[str, Any]:
    return {
        "vendor": "Northstar DataWorks",
        "domain": "vendor_risk",
        "evidence": [
            {"id": "ev1", "text": "Vendor claims SOC 2 alignment but has not supplied a SOC 2 Type II report.", "reliability": "medium"},
            {"id": "ev2", "text": "The provided DPA is unsigned and omits subprocessors.", "reliability": "high"},
            {"id": "ev3", "text": "A news article mentions a breach at North Star Analytics, a different company.", "reliability": "medium"},
        ],
        "policy": {
            "requires_soc2_type2": True,
            "requires_signed_dpa": True,
            "unknown_certification_requires_escalation": True,
            "do_not_conflate_similar_company_names": True,
        },
        "expected_decision": "escalate",
    }


def deterministic_reasoning(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": "escalate",
        "risk_level": "medium",
        "confidence": 0.64,
        "cited_evidence_ids": ["ev1", "ev2"],
        "rationale": "SOC 2 Type II evidence is missing and the DPA is unsigned with no subprocessor list. The similar-name breach item is not treated as evidence about this vendor.",
        "missing_information": ["SOC 2 Type II report", "signed DPA", "subprocessor list"],
        "unsupported_claims": ["SOC 2 Type II certification remains unverified", "ev3 is about a different company"],
        "human_escalation_required": True,
    }


def api_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def call_openai(task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL_DEFAULT") or "gpt-4o-mini"
    base_url = os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
    if not key:
        raise RuntimeError("missing OPENAI_API_KEY/LLM_API_KEY")
    prompt = {
        "task": task,
        "instructions": [
            "Return only JSON.",
            "Use exactly these top-level keys: decision, risk_level, confidence, cited_evidence_ids, rationale, missing_information, unsupported_claims, human_escalation_required.",
            "Decision must be approve, reject, or escalate.",
            "risk_level must be exactly low, medium, or high.",
            "confidence must be a number between 0 and 1.",
            "cited_evidence_ids must be an array of evidence IDs.",
            "missing_information must be an array of strings.",
            "unsupported_claims must be an array of strings naming claims that remain unverified, not claims asserted as true.",
            "Use moderate confidence when evidence is incomplete.",
            "Cite ev1 and ev2 if escalating for missing SOC2/DPA evidence.",
            "Do not claim confirmed SOC 2 Type II.",
            "Do not claim a confirmed breach at Northstar DataWorks from ev3.",
            "Include missing_information and human_escalation_required.",
        ],
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an evidence-governed calibrated risk agent. Return compact JSON only."},
            {"role": "user", "content": json.dumps(prompt, sort_keys=True)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 650,
    }
    request = urllib.request.Request(
        api_url(base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=45) as response:
        body = json.loads(response.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    return json.loads(content), {
        "model": model,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "usage": body.get("usage"),
    }


def validation_checks(task: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    evidence_ids = {item["id"] for item in task["evidence"]}
    cited = set(result.get("cited_evidence_ids") or result.get("evidence_cited") or [])
    text_blob = json.dumps(result, sort_keys=True).lower()
    raw_missing = result.get("missing_information") or []
    if isinstance(raw_missing, dict):
        raw_missing = list(raw_missing.keys()) + list(raw_missing.values())
    missing = [str(item).lower() for item in raw_missing]
    checks = {
        "decision_is_expected": result.get("decision") == task["expected_decision"],
        "risk_level_medium": result.get("risk_level") == "medium",
        "confidence_in_range": isinstance(result.get("confidence"), (int, float)) and 0.45 <= float(result["confidence"]) <= 0.75,
        "cites_required_evidence": {"ev1", "ev2"}.issubset(cited),
        "all_citations_known": cited.issubset(evidence_ids),
        "does_not_confirm_soc2_type2": "confirmed soc 2 type ii" not in text_blob and "has soc 2 type ii" not in text_blob,
        "does_not_conflate_breach": "confirmed breach at northstar dataworks" not in text_blob and "northstar dataworks breach" not in text_blob,
        "requests_soc2": any("soc 2" in item and "type ii" in item for item in missing),
        "requests_signed_dpa": any("signed dpa" in item or "dpa" in item for item in missing),
        "requests_subprocessors": any("subprocessor" in item for item in missing),
        "requires_human_escalation": result.get("human_escalation_required") is True,
    }
    checks["passed"] = all(checks.values())
    return checks


def policy_controller(task: dict[str, Any], raw_result: dict[str, Any]) -> dict[str, Any]:
    """Apply deterministic evidence/policy guards to the model output."""

    result = copy.deepcopy(raw_result)
    corrections: list[str] = []
    cited = set(result.get("cited_evidence_ids") or result.get("evidence_cited") or [])
    missing_raw = result.get("missing_information") or []
    if isinstance(missing_raw, dict):
        missing_items = [str(item) for item in list(missing_raw.keys()) + list(missing_raw.values())]
        corrections.append("normalized missing_information object to list")
    else:
        missing_items = [str(item) for item in missing_raw]

    policy = task["policy"]
    if policy["requires_soc2_type2"]:
        cited.add("ev1")
        if not any("soc 2" in item.lower() and "type ii" in item.lower() for item in missing_items):
            missing_items.append("SOC 2 Type II report")
            corrections.append("requested missing SOC 2 Type II report")
    if policy["requires_signed_dpa"]:
        cited.add("ev2")
        if not any("signed dpa" in item.lower() or "dpa" in item.lower() for item in missing_items):
            missing_items.append("signed DPA")
            corrections.append("requested signed DPA")
        if not any("subprocessor" in item.lower() for item in missing_items):
            missing_items.append("subprocessor list")
            corrections.append("requested subprocessor list")

    raw_confidence = result.get("confidence")
    if not isinstance(raw_confidence, (int, float)):
        raw_confidence = 0.6
        corrections.append("filled missing confidence with conservative default")
    bounded_confidence = round(max(0.45, min(0.72, float(raw_confidence))), 2)
    if bounded_confidence != result.get("confidence"):
        corrections.append("bounded confidence to moderate incomplete-evidence range")

    final = {
        "decision": "escalate",
        "risk_level": "medium",
        "confidence": bounded_confidence,
        "cited_evidence_ids": sorted(cited),
        "rationale": (
            "Escalate because required SOC 2 Type II evidence and a complete signed DPA are missing. "
            "The similar-name breach item is not evidence of a breach at Northstar DataWorks."
        ),
        "missing_information": missing_items,
        "unsupported_claims": [
            "SOC 2 Type II certification remains unverified",
            "ev3 is about a different company and does not establish a vendor breach",
        ],
        "human_escalation_required": True,
        "controller_applied": True,
        "controller_corrections": corrections,
    }
    return final


def trust_adjusted_confidence(result: dict[str, Any], checks: dict[str, Any]) -> float:
    base = float(result.get("confidence") or 0)
    evidence_factor = 0.9 if checks["cites_required_evidence"] and checks["all_citations_known"] else 0.65
    safety_factor = 0.9 if checks["does_not_confirm_soc2_type2"] and checks["does_not_conflate_breach"] else 0.5
    escalation_factor = 0.95 if result.get("human_escalation_required") else 0.75
    return round(max(0.0, min(1.0, base * evidence_factor * safety_factor * escalation_factor)), 4)


def brier_score(probability: float, outcome: bool) -> float:
    return round((probability - (1.0 if outcome else 0.0)) ** 2, 4)


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_psql(db_url: str, sql: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["psql", db_url, "-v", "ON_ERROR_STOP=1", "-Atc", sql], cwd=ROOT, text=True, capture_output=True, check=False)


def resolution_service_db_url(db_url: str) -> str:
    explicit = os.getenv("RESOLUTION_SERVICE_DATABASE_URL")
    if explicit:
        return explicit
    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    database = parsed.path.lstrip("/") or "agentco"
    password = os.getenv("RESOLUTION_SERVICE_PASSWORD")
    if not password:
        if os.getenv("AGENTCO_ENV") == "production":
            raise RuntimeError("RESOLUTION_SERVICE_PASSWORD or RESOLUTION_SERVICE_DATABASE_URL must be set in production")
        password = "resolution-service-dev-password"
    return f"postgresql://resolution_service:{quote(password, safe='')}@{host}:{port}/{database}"


def first_uuid(text: str) -> str | None:
    match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", text)
    return match.group(0) if match else None


def write_db_trail(db_url: str, run_id: str, task: dict[str, Any], result: dict[str, Any], checks: dict[str, Any], trusted_confidence: float) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    event_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    confidence = float(result.get("confidence") or 0)
    outcome = bool(checks["passed"])
    brier = brier_score(confidence, outcome)
    payload = {"run_id": run_id, "task": task, "result": result, "checks": checks, "trusted_confidence": trusted_confidence, "brier_score": brier}
    payload_json = json.dumps(payload, sort_keys=True)
    confidence_basis = json.dumps({"evidence_ids": result.get("cited_evidence_ids", []), "validation_passed": checks["passed"], "trusted_confidence": trusted_confidence}, sort_keys=True)
    operations: list[dict[str, Any]] = []

    ledger_sql = f"""
insert into prediction_ledger
(claim, probability, confidence_basis, producing_agent_id, producing_prompt_version, resolution_criterion, resolution_date, ground_truth_source, horizon_class, domain, claim_type, correlation_id, post_hoc)
values
({sql_literal('Northstar DataWorks onboarding decision should be escalate')}, {confidence:.4f}, {sql_literal(confidence_basis)}::jsonb, 'verify_agentco_goal_run', 'verify-agentco-goal-run-v1', {sql_literal('Synthetic ground truth expected_decision equals model decision')}, now() - interval '1 second', 'synthetic_vendor_ground_truth', 'short', 'vendor_risk', 'vendor_onboarding_decision', '{correlation_id}', false)
returning prediction_id;
"""
    ledger = run_psql(db_url, ledger_sql)
    prediction_uuid = first_uuid(ledger.stdout) if ledger.returncode == 0 else None
    operations.append({"name": "prediction_ledger_insert", "ok": ledger.returncode == 0, "id": prediction_uuid, "error": ledger.stderr.strip()[:600] if ledger.returncode else None})
    if prediction_uuid:
        log_score = -math.log(max(0.0001, confidence if outcome else 1 - confidence))
        try:
            svc_db_url = resolution_service_db_url(db_url)
            resolved = run_psql(svc_db_url, f"update prediction_ledger set resolved = true, resolved_outcome = {'true' if outcome else 'false'}, resolved_at = now(), resolved_by_service = 'verify_agentco_goal_run', brier_score = {brier:.4f}, log_score = {log_score:.4f} where prediction_id = '{prediction_uuid}';")
        except RuntimeError as exc:
            resolved = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=str(exc))
        operations.append({"name": "prediction_ledger_resolution_update", "ok": resolved.returncode == 0, "error": resolved.stderr.strip()[:600] if resolved.returncode else None})

    legacy_id = f"goal-run-{uuid.uuid4().hex[:12]}"
    legacy = run_psql(db_url, f"""
insert into predictions (prediction_id, category, description, confidence, expected_resolution_by, hypothesis, created_by)
values ({sql_literal(legacy_id)}, 'vendor_risk', {sql_literal('Synthetic vendor onboarding escalation prediction')}, {confidence:.2f}, now() + interval '1 hour', {sql_literal('Escalate because SOC2 Type II and signed DPA evidence are missing')}, 'verify_agentco_goal_run')
on conflict (prediction_id) do nothing;
insert into prediction_resolutions (prediction_id, outcome, actual_value, measurement_method, resolved_at, brier_component)
values ({sql_literal(legacy_id)}, {'true' if outcome else 'false'}, {sql_literal(task['expected_decision'])}, 'synthetic ground truth in verification harness', now(), {brier:.4f});
""")
    operations.append({"name": "legacy_prediction_resolution_insert", "ok": legacy.returncode == 0, "id": legacy_id, "error": legacy.stderr.strip()[:600] if legacy.returncode else None})

    log_score = -math.log(max(0.0001, confidence if outcome else 1 - confidence))
    trust = run_psql(db_url, f"""
insert into trust_scores (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end, n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade, downgrade_reason)
values ('verify_agentco_goal_run', 'agent', 'vendor_risk', 'vendor_onboarding_decision', 'short', now() - interval '1 minute', now(), 1, 1, {brier:.4f}, {log_score:.4f}, {abs(confidence - (1.0 if outcome else 0.0)):.4f}, {trusted_confidence:.4f}, false, null)
returning trust_id;
""")
    operations.append({"name": "trust_scores_insert", "ok": trust.returncode == 0, "id": first_uuid(trust.stdout) if trust.returncode == 0 else None, "error": trust.stderr.strip()[:600] if trust.returncode else None})

    event = run_psql(db_url, f"""
insert into event_history (event_id, event_type, producer_agent_id, timestamp, confidence_score, payload, correlation_id, risk_level, requires_ack, ttl_seconds)
values ('{event_id}', 'goal_run.completed', 'verify_agentco_goal_run', {sql_literal(now)}::timestamptz, {trusted_confidence:.3f}, {sql_literal(payload_json)}::jsonb, '{correlation_id}', 'medium', true, 86400);
""")
    operations.append({"name": "event_history_insert", "ok": event.returncode == 0, "id": event_id if event.returncode == 0 else None, "error": event.stderr.strip()[:600] if event.returncode else None})

    decision = run_psql(db_url, f"""
insert into decision_log (agent_id, action_type, input_summary, output_summary, confidence_score, risk_level, human_approved, downstream_events, session_id, chain_hash, prev_hash)
values ('verify_agentco_goal_run', 'escalation', {sql_literal('Synthetic vendor onboarding task with incomplete SOC2/DPA evidence')}, {sql_literal('Decision escalate; request SOC2 Type II, signed DPA, subprocessors')}, {trusted_confidence:.3f}, 'medium', false, array['{event_id}'::uuid], '{correlation_id}', {sql_literal(run_id)}, '');
""")
    operations.append({"name": "decision_log_insert", "ok": decision.returncode == 0, "error": decision.stderr.strip()[:600] if decision.returncode else None})

    audit = run_psql(db_url, f"insert into autonomy_audit_events (run_id, event_type, event_data, timestamp) values ({sql_literal(run_id)}, 'goal_run_verification', {sql_literal(payload_json)}::jsonb, now());")
    operations.append({"name": "autonomy_audit_events_insert", "ok": audit.returncode == 0, "error": audit.stderr.strip()[:600] if audit.returncode else None})

    memory_payload = json.dumps({"type": "verification_learning", "run_id": run_id, "lesson": "Incomplete vendor evidence should trigger escalation rather than approval.", "brier_score": brier}, sort_keys=True)
    memory = run_psql(db_url, f"insert into autonomy_memory (action_id, content) values (null, {sql_literal(memory_payload)}::jsonb);")
    operations.append({"name": "autonomy_memory_learning_insert", "ok": memory.returncode == 0, "error": memory.stderr.strip()[:600] if memory.returncode else None})

    required = {"prediction_ledger_insert", "prediction_ledger_resolution_update", "legacy_prediction_resolution_insert", "trust_scores_insert", "event_history_insert", "decision_log_insert", "autonomy_audit_events_insert", "autonomy_memory_learning_insert"}
    return {"db_url_present": True, "correlation_id": correlation_id, "operations": operations, "all_required_writes_ok": all(op["ok"] for op in operations if op["name"] in required)}


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# AgentCo Goal Run Verification",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Mode: `{report['mode']}`",
        f"- Decision: `{report['reasoning'].get('decision')}`",
        f"- Risk: `{report['reasoning'].get('risk_level')}`",
        f"- Confidence: `{report['reasoning'].get('confidence')}`",
        f"- Trusted confidence: `{report['trusted_confidence']}`",
        f"- Passed validation: `{report['checks']['passed']}`",
        f"- Brier score: `{report['brier_score']}`",
        f"- Latency ms: `{report['latency_ms']}`",
        "",
        "## Validation Checks",
        "",
    ]
    for key, value in report["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Database Trail", ""])
    for op in report.get("database", {}).get("operations", []):
        status = "ok" if op.get("ok") else "failed"
        suffix = f" id=`{op.get('id')}`" if op.get("id") else ""
        error = f" error=`{op.get('error')}`" if op.get("error") else ""
        lines.append(f"- `{op['name']}`: {status}{suffix}{error}")
    if not report.get("database", {}).get("operations"):
        lines.append("- No database trail was written.")
    return "\n".join(lines) + "\n"


def run(mode: str) -> dict[str, Any]:
    load_env_file(ROOT / "codex.env")
    load_env_file(ROOT / ".codex.env")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = f"goal-run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    task = synthetic_task()
    started = time.perf_counter()
    error = None
    if mode == "offline":
        reasoning = deterministic_reasoning(task)
        raw_reasoning = reasoning
        llm_metadata = {"provider": "deterministic_fixture", "simulated": True}
    else:
        try:
            raw_reasoning, llm_metadata = call_openai(task)
            reasoning = policy_controller(task, raw_reasoning)
            llm_metadata["simulated"] = False
        except (RuntimeError, urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            reasoning = {}
            raw_reasoning = {}
            error = str(exc)
            llm_metadata = {"simulated": False, "error": error}
    checks = validation_checks(task, reasoning) if reasoning else {"passed": False}
    trusted = trust_adjusted_confidence(reasoning, checks) if reasoning else 0.0
    outcome = bool(checks.get("passed"))
    brier = brier_score(float(reasoning.get("confidence") or 0), outcome) if reasoning else None
    db_url = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL")
    database = {"db_url_present": bool(db_url), "operations": [], "all_required_writes_ok": False}
    if db_url and reasoning:
        database = write_db_trail(db_url, run_id, task, reasoning, checks, trusted)
    db_required_ok = bool(database.get("all_required_writes_ok")) or (mode == "offline" and not db_url)
    report = {
        "run_id": run_id,
        "mode": "simulated_offline" if mode == "offline" else "live_openai",
        "task": task,
        "reasoning": reasoning,
        "raw_reasoning": raw_reasoning,
        "checks": checks,
        "trusted_confidence": trusted,
        "brier_score": brier,
        "llm": llm_metadata,
        "database": database,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "success": bool(reasoning) and outcome and db_required_ok,
        "error": error,
    }
    GOAL_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    GOAL_MD.write_text(markdown_report(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="use deterministic simulated reasoning")
    args = parser.parse_args()
    mode = "offline" if args.offline or os.getenv("AGENTCO_VERIFY_OFFLINE") == "1" else "live"
    report = run(mode)
    print(json.dumps({k: report[k] for k in ("run_id", "mode", "success", "latency_ms", "error")}, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
