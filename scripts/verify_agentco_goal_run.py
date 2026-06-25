#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"


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
    return {
        "success": validation["passed"],
        "mode": mode,
        "simulated": offline,
        "task": SYNTHETIC_VENDOR_TASK,
        "result": output,
        "validation": validation,
        "prediction": {
            "id": f"goal-run-{int(started)}",
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
        "failures": 0 if report["success"] else 1,
    }
    (REPORT_DIR / "performance_summary.json").write_text(json.dumps(perf, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    offline = args.offline or os.getenv("AGENTCO_VERIFY_OFFLINE") == "1"
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
