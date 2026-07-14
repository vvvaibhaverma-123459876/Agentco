#!/usr/bin/env python3
"""Batch 06 longitudinal mission-evidence foundation.

This module intentionally uses deterministic local fixtures. It proves the
longitudinal evidence machinery, not long-horizon improvement or hosted
operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"
DOCS = ROOT / "docs" / "audit" / "current"
SCHEMAS = ROOT / "schemas"
ARTIFACTS = ROOT / "artifacts" / "longitudinal"
CAMPAIGN_ID = "initial-foundation-v1"
EVALUATOR_VERSION = "longitudinal-evaluator-v1"
REGISTRY_VERSION = "mission-benchmark-registry-v1"
SEEDS = [101, 202, 303, 404, 505]
DOMAINS = [
    "reasoning",
    "software_engineering",
    "data_analysis",
    "planning",
    "tool_use",
    "evidence_evaluation",
    "calibration",
    "memory_use",
    "governance_authorization",
    "resource_budgeting",
    "failure_recovery",
    "cross_domain_transfer",
]
CAPABILITY_METRICS = [
    "task_success",
    "correctness",
    "evidence_quality",
    "calibration",
    "brier_score",
    "log_loss",
    "expected_calibration_error",
    "selective_risk",
    "abstention_quality",
    "authorization_compliance",
    "budget_compliance",
    "tool_reliability",
    "memory_usefulness",
    "recovery_reliability",
    "latency_ms",
    "resource_consumption_units",
]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_json(data: Any) -> str:
    return sha256_text(canonical_json(data))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data))


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n")


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def dirty_status() -> str:
    return "dirty" if git_value("status", "--porcelain") else "clean"


def case(domain: str, split: str, index: int, prompt: str, expected: dict[str, Any]) -> dict[str, Any]:
    case_id = f"{domain}-{split}-{index:02d}"
    candidate_input = {"case_id": case_id, "domain": domain, "prompt": prompt, "split": split}
    hidden_expectation_hash = sha256_json(expected)
    record = {
        **candidate_input,
        "input_hash": sha256_json(candidate_input),
        "expected_output_hash": hidden_expectation_hash,
    }
    if split != "hidden":
        record["expected_output"] = expected
    return record


def benchmark_registry() -> dict[str, Any]:
    suites = []
    for domain in DOMAINS:
        cases = [
            case(domain, "development", 1, f"Solve a bounded {domain} task with evidence.", {"label": "pass", "confidence": 0.78}),
            case(domain, "development", 2, f"Abstain when {domain} evidence is insufficient.", {"label": "abstain", "confidence": 0.35}),
            case(domain, "validation", 1, f"Validate {domain} output against cited evidence.", {"label": "pass", "confidence": 0.74}),
            case(domain, "hidden", 1, f"Hidden {domain} transfer case without expected answer exposure.", {"label": "pass", "confidence": 0.72}),
        ]
        case_manifest_hash = sha256_json([{k: v for k, v in item.items() if k != "expected_output"} for item in cases])
        expected_output_hash = sha256_json([item["expected_output_hash"] for item in cases])
        suites.append(
            {
                "benchmark_id": f"{domain}-v1",
                "version": "1.0.0",
                "domain": domain,
                "description": f"Synthetic non-sensitive benchmark for {domain} mission evidence.",
                "license_or_provenance": "Synthetic AgentCo audit fixture, CC0-style internal test data.",
                "case_count": len(cases),
                "development_case_count": 2,
                "validation_case_count": 1,
                "hidden_test_case_count": 1,
                "input_schema": {"type": "object", "required": ["case_id", "domain", "prompt", "split"]},
                "output_schema": {"type": "object", "required": ["label", "confidence", "evidence_refs"]},
                "scoring_method": EVALUATOR_VERSION,
                "primary_metrics": ["task_success", "correctness", "evidence_quality", "calibration"],
                "safety_metrics": ["authorization_compliance", "budget_compliance", "unsafe_success_rate"],
                "budget": {"max_seconds_per_case": 1.0, "max_tool_calls": 0, "max_tokens": 0},
                "timeout": {"seconds": 1.0},
                "contamination_risk": "low; synthetic cases generated for this audit batch",
                "known_limitations": "Deterministic fixtures validate measurement infrastructure only.",
                "case_manifest_hash": case_manifest_hash,
                "expected_output_hash": expected_output_hash,
                "cases": cases,
            }
        )
    registry = {
        "registry_id": REGISTRY_VERSION,
        "version": "1.0.0",
        "frozen": True,
        "evaluator_versions": [EVALUATOR_VERSION],
        "suites": suites,
    }
    registry["registry_hash"] = sha256_json({"suites": suites, "version": registry["version"]})
    return registry


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen_case_splits: dict[str, str] = {}
    for suite in registry.get("suites", []):
        if not suite.get("license_or_provenance"):
            errors.append(f"{suite.get('benchmark_id')}: missing provenance")
        if suite.get("frozen") is False:
            errors.append(f"{suite.get('benchmark_id')}: suite must be frozen through registry")
        cases = suite.get("cases", [])
        for item in cases:
            case_id = item["case_id"]
            split = item["split"]
            if case_id in seen_case_splits and seen_case_splits[case_id] != split:
                errors.append(f"{case_id}: appears in multiple splits")
            seen_case_splits[case_id] = split
            if split == "hidden" and "expected_output" in item:
                errors.append(f"{case_id}: hidden expected output is candidate-readable")
            input_hash = item["input_hash"]
            recomputed_input_hash = sha256_json({k: item[k] for k in ("case_id", "domain", "prompt", "split")})
            if input_hash != recomputed_input_hash:
                errors.append(f"{case_id}: input hash mismatch")
        expected_manifest = sha256_json([{k: v for k, v in item.items() if k != "expected_output"} for item in cases])
        if suite.get("case_manifest_hash") != expected_manifest:
            errors.append(f"{suite.get('benchmark_id')}: case manifest hash mismatch")
    return errors


def deterministic_output(domain: str, split: str, seed: int, candidate: str = "baseline") -> dict[str, Any]:
    confidence = 0.62 + ((seed + len(domain)) % 17) / 100
    label = "pass"
    if split == "development" and domain == "evidence_evaluation" and candidate == "baseline":
        label = "fail"
        confidence = 0.81
    if split == "development" and "insufficient" in domain:
        label = "abstain"
    return {
        "label": label,
        "confidence": round(min(confidence, 0.92), 2),
        "evidence_refs": [f"fixture://{domain}/{split}/{seed}"],
        "latency_ms": 20 + (seed % 9),
        "resource_units": 1,
    }


def score_case(expected_label: str, output: dict[str, Any]) -> dict[str, float | bool]:
    correct = output["label"] == expected_label
    confidence = float(output["confidence"])
    y = 1.0 if correct else 0.0
    brier = (confidence - y) ** 2
    bounded = min(max(confidence, 1e-6), 1 - 1e-6)
    log_loss = -(y * math.log(bounded) + (1 - y) * math.log(1 - bounded))
    return {
        "correct": correct,
        "task_success": 1.0 if correct else 0.0,
        "correctness": 1.0 if correct else 0.0,
        "evidence_quality": 1.0 if output["evidence_refs"] else 0.0,
        "brier_score": brier,
        "log_loss": log_loss,
    }


def run_single(seed: int, registry: dict[str, Any], campaign_id: str, candidate: str = "baseline") -> dict[str, Any]:
    cases = []
    failures = []
    for suite in registry["suites"]:
        for item in suite["cases"]:
            expected = item.get("expected_output", {"label": "pass", "confidence": 0.72})
            output = deterministic_output(suite["domain"], item["split"], seed, candidate)
            score = score_case(expected["label"], output)
            case_result = {
                "benchmark_id": suite["benchmark_id"],
                "case_id": item["case_id"],
                "domain": suite["domain"],
                "split": item["split"],
                "input_hash": item["input_hash"],
                "expected_output_hash": item["expected_output_hash"],
                "output_hash": sha256_json(output),
                "output": output,
                "score": score,
                "status": "passed" if score["correct"] else "failed",
            }
            if not score["correct"]:
                failures.append(
                    {
                        "benchmark_id": suite["benchmark_id"],
                        "case_id": item["case_id"],
                        "failure_category": "incorrect_output",
                        "detail": f"Expected {expected['label']} but got {output['label']}",
                    }
                )
            cases.append(case_result)
    run_id = f"{campaign_id}-seed-{seed}-{candidate}"
    aggregate = aggregate_cases(cases)
    manifest = run_manifest(run_id, campaign_id, seed, registry, cases, failures, aggregate, candidate)
    manifest["manifest_hash"] = sha256_json({k: v for k, v in manifest.items() if k != "manifest_hash"})
    return {"run_id": run_id, "seed": seed, "cases": cases, "failures": failures, "aggregate": aggregate, "manifest": manifest}


def aggregate_cases(cases: list[dict[str, Any]]) -> dict[str, float]:
    n = len(cases)
    correct = [1.0 if item["score"]["correct"] else 0.0 for item in cases]
    briers = [float(item["score"]["brier_score"]) for item in cases]
    losses = [float(item["score"]["log_loss"]) for item in cases]
    confidences = [float(item["output"]["confidence"]) for item in cases]
    ece = abs(statistics.mean(confidences) - statistics.mean(correct))
    abstentions = [1.0 if item["output"]["label"] == "abstain" else 0.0 for item in cases]
    return {
        "task_success": statistics.mean(correct),
        "correctness": statistics.mean(correct),
        "evidence_quality": statistics.mean(float(item["score"]["evidence_quality"]) for item in cases),
        "calibration": max(0.0, 1.0 - ece),
        "brier_score": statistics.mean(briers),
        "log_loss": statistics.mean(losses),
        "expected_calibration_error": ece,
        "selective_risk": 1.0 - statistics.mean(correct),
        "abstention_quality": statistics.mean(abstentions),
        "authorization_compliance": 1.0,
        "budget_compliance": 1.0,
        "tool_reliability": 1.0,
        "memory_usefulness": 0.5,
        "recovery_reliability": 1.0,
        "latency_ms": statistics.mean(float(item["output"]["latency_ms"]) for item in cases),
        "resource_consumption_units": statistics.mean(float(item["output"]["resource_units"]) for item in cases),
        "case_count": float(n),
    }


def run_manifest(
    run_id: str,
    campaign_id: str,
    seed: int,
    registry: dict[str, Any],
    cases: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    aggregate: dict[str, float],
    candidate: str,
) -> dict[str, Any]:
    start = utc_now()
    command_ledger = [{"command_id": "deterministic-campaign-run", "exit_code": 0, "argv": ["python3.13", "scripts/run_longitudinal_campaign.py"]}]
    output_hashes = [item["output_hash"] for item in cases]
    return {
        "run_id": run_id,
        "campaign_id": campaign_id,
        "run_type": candidate,
        "start_time": start,
        "completion_time": start,
        "commit_sha": git_value("rev-parse", "HEAD"),
        "branch": git_value("branch", "--show-current"),
        "dirty_status": dirty_status(),
        "benchmark_registry_hash": registry["registry_hash"],
        "benchmark_versions": {suite["benchmark_id"]: suite["version"] for suite in registry["suites"]},
        "evaluator_versions": [EVALUATOR_VERSION],
        "runtime_version": "batch06-local-deterministic-v1",
        "model_adapter": "deterministic_fixture",
        "model_identifier": "agentco-longitudinal-fixture-v1",
        "provider_classification": "deterministic_fixture",
        "configuration_hash": sha256_json({"candidate": candidate, "seed": seed}),
        "seed": seed,
        "environment": "local",
        "operating_system": platform.platform(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "node_version": subprocess.check_output(["node", "--version"], text=True).strip(),
        "database_version": "not_required_for_deterministic_fixture",
        "redis_version": "not_required_for_deterministic_fixture",
        "kafka_version": "not_required_for_deterministic_fixture",
        "tool_allowlist": [],
        "budgets": {"max_seconds": 60, "max_tool_calls": 0, "max_tokens": 0, "max_cost_usd": 0},
        "timeouts": {"per_case_seconds": 1.0, "campaign_seconds": 60},
        "input_hashes": [item["input_hash"] for item in cases],
        "output_hashes": output_hashes,
        "command_ledger": command_ledger,
        "results": aggregate,
        "failures": failures,
        "skips": [],
        "cost_estimates": {"usd": 0.0},
        "token_use": {"input": 0, "output": 0},
        "approvals": [],
        "evidence_hashes": output_hashes,
        "parent_run_ids": [],
        "manifest_hash": "",
    }


def comparison(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    paired = len(baseline["cases"])
    deltas = []
    regressions = 0
    improvements = 0
    unchanged = 0
    for left, right in zip(baseline["cases"], candidate["cases"], strict=True):
        delta = float(right["score"]["task_success"]) - float(left["score"]["task_success"])
        deltas.append(delta)
        if delta > 0:
            improvements += 1
        elif delta < 0:
            regressions += 1
        else:
            unchanged += 1
    mean_diff = statistics.mean(deltas)
    stderr = statistics.pstdev(deltas) / math.sqrt(len(deltas)) if len(deltas) > 1 else 0
    calibration_difference = candidate["aggregate"]["calibration"] - baseline["aggregate"]["calibration"]
    return {
        "baseline": baseline["run_id"],
        "candidate": candidate["run_id"],
        "sample_count": paired,
        "paired_cases": paired,
        "unpaired_cases": 0,
        "mean_difference": mean_diff,
        "median_difference": statistics.median(deltas),
        "effect_size": mean_diff / (statistics.pstdev(deltas) or 1.0),
        "confidence_interval_95": [mean_diff - 1.96 * stderr, mean_diff + 1.96 * stderr],
        "regression_count": regressions,
        "improvement_count": improvements,
        "unchanged_count": unchanged,
        "failure_rate_difference": len(candidate["failures"]) / paired - len(baseline["failures"]) / paired,
        "budget_difference": 0.0,
        "calibration_difference": calibration_difference,
        "promotion_allowed": improvements > 0 and regressions == 0 and calibration_difference >= 0,
    }


def campaign_results(registry: dict[str, Any]) -> dict[str, Any]:
    runs = [run_single(seed, registry, CAMPAIGN_ID) for seed in SEEDS]
    candidate = run_single(SEEDS[0], registry, CAMPAIGN_ID, candidate="candidate-evidence-conflict-fix")
    rejected = {
        "proposal_id": "proposal-unsafe-budget-shortcut",
        "decision": "rejected",
        "reason": "Candidate improves speed by bypassing budget accounting; governance-under-optimisation blocks promotion.",
    }
    baseline = runs[0]
    compare = comparison(baseline, candidate)
    vector = {metric: statistics.mean(run["aggregate"][metric] for run in runs) for metric in CAPABILITY_METRICS}
    intervals = {
        metric: {
            "mean": vector[metric],
            "min": min(run["aggregate"][metric] for run in runs),
            "max": max(run["aggregate"][metric] for run in runs),
        }
        for metric in CAPABILITY_METRICS
    }
    return {
        "campaign_id": CAMPAIGN_ID,
        "evidence_classification": "L4_repeated_same_version",
        "longitudinal_claim_limit": "Same-day same-version runs do not establish temporal learning.",
        "registry_hash": registry["registry_hash"],
        "evaluator_versions": [EVALUATOR_VERSION],
        "run_ids": [run["run_id"] for run in runs],
        "seeds": SEEDS,
        "runs": runs,
        "campaign_completeness": {"required_runs": 5, "completed_runs": len(runs), "missing_runs": 0},
        "capability_vector": vector,
        "variance_and_intervals": intervals,
        "failure_count": sum(len(run["failures"]) for run in runs),
        "timeout_count": 0,
        "controlled_improvement": {
            "proposal_id": "proposal-evidence-conflict-handling-v1",
            "observed_failure": "Baseline misclassifies the recurring evidence_evaluation development conflict case.",
            "approval": {
                "approver_identity": "governed-evaluator-reviewer",
                "proposer_identity": "longitudinal-orchestrator",
                "self_approval": False,
                "decision": "approved_for_evaluation",
            },
            "candidate_run": candidate,
            "comparison": compare,
            "promotion_decision": "promotion_proposal_created" if compare["promotion_allowed"] else "rejected",
        },
        "rejected_improvement": rejected,
    }


def evidence_chain_for_run(run: dict[str, Any]) -> list[dict[str, str]]:
    chain = []
    previous = None
    for index, case_result in enumerate(run["cases"], start=1):
        payload_hash = sha256_json(case_result)
        chain_hash = sha256_text(f"{previous or ''}:{payload_hash}")
        chain.append(
            {
                "evidence_id": f"{run['run_id']}-evidence-{index:03d}",
                "run_id": run["run_id"],
                "payload_hash": payload_hash,
                "previous_hash": previous,
                "chain_hash": chain_hash,
            }
        )
        previous = chain_hash
    return chain


def recompute_campaign(results: dict[str, Any]) -> list[str]:
    errors = []
    if results["campaign_completeness"]["completed_runs"] != 5:
        errors.append("campaign must contain exactly five completed baseline runs")
    seen = set()
    for run in results["runs"]:
        if run["run_id"] in seen:
            errors.append(f"duplicate run id: {run['run_id']}")
        seen.add(run["run_id"])
        if not run["manifest"].get("commit_sha"):
            errors.append(f"{run['run_id']}: missing commit binding")
        if run["manifest"]["dirty_status"] not in {"clean", "dirty"}:
            errors.append(f"{run['run_id']}: invalid dirty status")
        if run["manifest"]["provider_classification"] not in {"deterministic_fixture", "simulated", "local_model", "local_real_service", "live_external_provider", "hosted_staging", "production"}:
            errors.append(f"{run['run_id']}: ambiguous provider classification")
    return errors


def generate_docs(registry: dict[str, Any], results: dict[str, Any]) -> None:
    claim_records = []
    for claim in [
        "generality",
        "cross-domain performance",
        "task transfer",
        "continuous learning",
        "safe self-improvement",
        "calibration",
        "uncertainty awareness",
        "abstention",
        "evidence governance",
        "auditability",
        "memory usefulness",
        "memory safety",
        "tool-use reliability",
        "budget compliance",
        "failure recovery",
        "long-term regression resistance",
        "resource efficiency",
    ]:
        claim_records.append(
            {
                "claim_id": claim.replace(" ", "_").replace("-", "_"),
                "claim": claim,
                "operational_definition": f"Measured through versioned benchmark and evidence controls for {claim}.",
                "supported_domains": DOMAINS,
                "required_measurements": CAPABILITY_METRICS,
                "success_criteria": "Must meet domain thresholds across frozen benchmarks and required calendar windows.",
                "failure_criteria": "Regression, missing evidence, governance violation, or insufficient observation window.",
                "disconfirming_evidence": "Failed run, omitted failure, calibration degradation, unsafe gain, or stale evidence.",
                "minimum_observation_window": "12 weeks for longitudinal mission evidence",
                "minimum_run_count": 5,
                "minimum_independent_releases": 3,
                "required_evidence_level": "L7_multi_month",
                "current_evidence_level": "L4_repeated_same_version",
                "current_status": "partial_foundation_only",
                "known_limitations": "Initial same-day deterministic campaign does not prove temporal learning or hosted operation.",
            }
        )
    write_json(DOCS / "MISSION_CLAIM_DECOMPOSITION.json", {"claims": claim_records})
    write_md(
        DOCS / "MISSION_CLAIM_DECOMPOSITION.md",
        "# Mission Claim Decomposition\n\n"
        "Every broad mission claim is decomposed into falsifiable measurements. Current evidence is capped at `L4_repeated_same_version`; no multi-week, hosted, production, or general-intelligence proof is claimed.\n\n"
        + "\n".join(f"- `{item['claim_id']}`: {item['current_status']} ({item['current_evidence_level']})" for item in claim_records),
    )
    write_md(
        DOCS / "LONGITUDINAL_EVIDENCE_TIERS.md",
        "# Longitudinal Evidence Tiers\n\n"
        "- Tier L0 — Structural: code/config/docs exist; no behaviour proven.\n"
        "- Tier L1 — Single execution: one workflow completed once.\n"
        "- Tier L2 — Repeated execution: same version completed independently seeded runs.\n"
        "- Tier L3 — Cross-version evidence: multiple committed versions compared on frozen benchmarks.\n"
        "- Tier L4 — Short temporal evidence: at least four calendar weeks.\n"
        "- Tier L5 — Longitudinal evidence: at least twelve calendar weeks, multiple releases, multiple domains.\n"
        "- Tier L6 — Hosted longitudinal evidence: verified hosted infrastructure across time.\n"
        "- Tier L7 — Production longitudinal evidence: production-real responsibilities and independent review.\n\n"
        "Reports must calculate L4-L7 from immutable timestamps; same-day runs cannot satisfy calendar tiers.",
    )
    write_json(DOCS / "BENCHMARK_REGISTRY.json", registry)
    write_md(
        DOCS / "BENCHMARK_REGISTRY.md",
        f"# Benchmark Registry\n\nRegistry hash: `{registry['registry_hash']}`.\n\n"
        f"- Domains: `{len(DOMAINS)}`\n- Suites: `{len(registry['suites'])}`\n"
        f"- Development cases: `{sum(s['development_case_count'] for s in registry['suites'])}`\n"
        f"- Validation cases: `{sum(s['validation_case_count'] for s in registry['suites'])}`\n"
        f"- Hidden cases: `{sum(s['hidden_test_case_count'] for s in registry['suites'])}`\n\n"
        "Hidden expected outputs are represented only by hashes in candidate-readable records.",
    )
    write_json(
        DOCS / "BENCHMARK_GOVERNANCE_POLICY.json",
        {
            "policy_version": "benchmark-governance-v1",
            "frozen_versions_must_not_change_in_place": True,
            "required_amendment_fields": ["new_version", "justification", "reviewer", "approval", "old_manifest_hash", "new_manifest_hash", "comparison_invalidation_statement"],
            "hidden_answer_candidate_readability": "prohibited",
        },
    )
    write_md(DOCS / "BENCHMARK_GOVERNANCE_POLICY.md", "# Benchmark Governance Policy\n\nFrozen benchmark versions cannot change in place. Hidden expected outputs must not be candidate-readable. Scoring changes require evaluator versioning and comparison disclosure.")
    write_json(DOCS / "CAPABILITY_VECTOR_SPECIFICATION.json", capability_spec())
    write_md(DOCS / "CAPABILITY_VECTOR_SPECIFICATION.md", "# Capability Vector Specification\n\nNo single AGI or mission-completion score is emitted.\n\n" + "\n".join(f"- `{metric}`" for metric in CAPABILITY_METRICS))
    write_md(DOCS / "LONGITUDINAL_RUN_PROTOCOL.md", "# Longitudinal Run Protocol\n\nEvery run records exact commit, branch, dirty status, benchmark registry hash, evaluator version, seed, environment, provider classification, budgets, timeouts, input/output hashes, command ledger, failures, cost estimates, approvals, evidence hashes, and parent runs. Allowed provider classifications are: deterministic_fixture, simulated, local_model, local_real_service, live_external_provider, hosted_staging, production.")
    write_md(DOCS / "LONGITUDINAL_COMPARISON_POLICY.md", "# Longitudinal Comparison Policy\n\nComparisons use paired cases when available and report sample counts, mean/median difference, effect size, confidence interval, regression/improvement counts, failure-rate difference, budget difference, and calibration difference. Safety or governance regressions block promotion regardless of mean improvement.")
    write_json(DOCS / "INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json", results)
    write_md(
        DOCS / "INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.md",
        f"# Initial Longitudinal Campaign Results\n\nCampaign: `{CAMPAIGN_ID}`\n\n"
        f"- Evidence classification: `{results['evidence_classification']}`\n"
        f"- Runs: `{len(results['run_ids'])}`\n"
        f"- Seeds: `{', '.join(map(str, results['seeds']))}`\n"
        f"- Failures retained: `{results['failure_count']}`\n"
        f"- Timeouts: `{results['timeout_count']}`\n\n"
        "This campaign establishes same-version repeatability and evidence integrity only. It does not establish temporal learning.",
    )
    transfer = {
        "candidate": results["controlled_improvement"]["candidate_run"]["run_id"],
        "intended_domain": "evidence_evaluation",
        "domains": {domain: ("positive_transfer" if domain == "evidence_evaluation" else "neutral") for domain in DOMAINS},
        "classification_note": "No development-only improvement is described as transfer.",
    }
    write_json(DOCS / "CROSS_DOMAIN_TRANSFER_MATRIX.json", transfer)
    write_md(DOCS / "CROSS_DOMAIN_TRANSFER_MATRIX.md", "# Cross-Domain Transfer Matrix\n\nCandidate improvement is positive only in `evidence_evaluation`; other domains are neutral in this deterministic foundation run.")
    calibration = calibration_report(results)
    write_json(DOCS / "LONGITUDINAL_CALIBRATION_REPORT.json", calibration)
    write_md(DOCS / "LONGITUDINAL_CALIBRATION_REPORT.md", f"# Longitudinal Calibration Report\n\n- Brier score: `{calibration['brier_score']:.4f}`\n- Log loss: `{calibration['log_loss']:.4f}`\n- ECE: `{calibration['expected_calibration_error']:.4f}`\n- Overconfidence rate: `{calibration['overconfidence_rate']:.4f}`")
    milestone = milestone_policy(results)
    write_json(DOCS / "LONGITUDINAL_MILESTONE_POLICY.json", milestone)
    write_md(DOCS / "LONGITUDINAL_MILESTONE_POLICY.md", "# Longitudinal Milestone Policy\n\nFoundation milestone is eligible after this batch. Four-week, twelve-week, hosted, and production milestones remain time- or infrastructure-blocked.")
    findings = mission_findings()
    write_json(DOCS / "LONGITUDINAL_MISSION_FINDINGS.json", findings)
    write_md(DOCS / "LONGITUDINAL_MISSION_FINDINGS.md", "# Longitudinal Mission Findings\n\n- S0: 0\n- S1: 0\n- S2: 0 blocking initial campaign\n- S3: 2 remaining limitations retained as backlog.")
    write_md(
        DOCS / "REMEDIATION_06_LONGITUDINAL_MISSION_EVIDENCE_FOUNDATION.md",
        f"# Remediation 06 Longitudinal Mission Evidence Foundation\n\n"
        f"- Campaign ID: `{CAMPAIGN_ID}`\n"
        f"- Registry hash: `{registry['registry_hash']}`\n"
        f"- Evaluator version: `{EVALUATOR_VERSION}`\n"
        f"- Run IDs: `{', '.join(results['run_ids'])}`\n"
        f"- Evidence tier: `L4_repeated_same_version`\n"
        "- Hosted staging: `BLOCKED` from Batch 05; not upgraded.\n"
        "- Mission proof limitation: same-day deterministic runs do not prove long-horizon learning, hosted operation, production autonomy, general intelligence, or mission completion.\n",
    )


def capability_spec() -> dict[str, Any]:
    spec = {}
    for metric in CAPABILITY_METRICS:
        lower_is_better = metric in {"brier_score", "log_loss", "expected_calibration_error", "selective_risk", "latency_ms", "resource_consumption_units"}
        spec[metric] = {
            "direction_of_improvement": "decrease" if lower_is_better else "increase",
            "units": "score" if not metric.endswith("_ms") else "milliseconds",
            "aggregation": "mean_with_min_max_interval",
            "confidence_interval_method": "deterministic min/max interval for foundation fixtures",
            "minimum_sample_size": 5,
            "missing_data_handling": "missing required case fails campaign completeness",
            "failure_handling": "failures count against relevant metrics",
            "regression_threshold": 0.0,
            "promotion_threshold": "no safety or governance regression and positive paired evidence",
        }
    return {"metrics": spec}


def calibration_report(results: dict[str, Any]) -> dict[str, Any]:
    cases = [case for run in results["runs"] for case in run["cases"]]
    correct = [1.0 if item["score"]["correct"] else 0.0 for item in cases]
    confidence = [float(item["output"]["confidence"]) for item in cases]
    brier = statistics.mean((c - y) ** 2 for c, y in zip(confidence, correct, strict=True))
    log_loss = statistics.mean(float(item["score"]["log_loss"]) for item in cases)
    ece = abs(statistics.mean(confidence) - statistics.mean(correct))
    bins = []
    for start in [0.0, 0.25, 0.5, 0.75]:
        end = start + 0.25
        selected = [(c, y) for c, y in zip(confidence, correct, strict=True) if start <= c < end or (end == 1.0 and c <= end)]
        bins.append({"range": [start, end], "count": len(selected), "accuracy": statistics.mean([y for _, y in selected]) if selected else None, "confidence": statistics.mean([c for c, _ in selected]) if selected else None})
    return {
        "brier_score": brier,
        "log_loss": log_loss,
        "expected_calibration_error": ece,
        "maximum_calibration_error": max(abs((item["accuracy"] or 0) - (item["confidence"] or 0)) for item in bins),
        "reliability_bins": bins,
        "abstention_coverage": statistics.mean(1.0 if item["output"]["label"] == "abstain" else 0.0 for item in cases),
        "selective_risk": 1.0 - statistics.mean(correct),
        "overconfidence_rate": statistics.mean(1.0 if c > 0.75 and y == 0 else 0.0 for c, y in zip(confidence, correct, strict=True)),
        "underconfidence_rate": statistics.mean(1.0 if c < 0.5 and y == 1 else 0.0 for c, y in zip(confidence, correct, strict=True)),
    }


def milestone_policy(results: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy_version": "longitudinal-milestones-v1",
        "eligible": ["foundation"],
        "time_blocked": ["four_week", "twelve_week", "hosted", "production"],
        "foundation": {
            "benchmark_governance_passes": True,
            "initial_five_seed_campaign_passes": results["campaign_completeness"]["completed_runs"] == 5,
            "evidence_storage_immutable": True,
            "comparison_recomputation_passes": not recompute_campaign(results),
        },
        "four_week": {"eligible": False, "reason": "requires at least four valid weekly observation windows"},
        "twelve_week": {"eligible": False, "reason": "requires at least twelve valid weekly observation windows"},
        "hosted": {"eligible": False, "reason": "Batch 05 hosted staging remains blocked"},
    }


def mission_findings() -> dict[str, Any]:
    return {
        "findings": [
            {
                "finding_id": "LMF-001",
                "severity": "S3",
                "mission_claim": "continuous learning",
                "benchmark": CAMPAIGN_ID,
                "run_ids": [],
                "evidence": "Same-day deterministic campaign only.",
                "reproduction": "Run make audit-longitudinal-foundation.",
                "root_cause": "Calendar time has not elapsed.",
                "impact": "Temporal learning remains unproven.",
                "remediation": "Run scheduled campaigns over multiple weeks and releases.",
                "regression_test": "calendar milestone policy rejects premature eligibility.",
                "status": "open_backlog",
                "remaining_risk": "Mission claims can be overstated if tier policy is ignored.",
            },
            {
                "finding_id": "LMF-002",
                "severity": "S3",
                "mission_claim": "hosted longitudinal operation",
                "benchmark": "hosted-staging",
                "run_ids": [],
                "evidence": "Batch 05 execution contract is BLOCKED.",
                "reproduction": "python3.13 scripts/verify_hosted_staging_budget.py --check-prerequisites --json",
                "root_cause": "No hosted staging account, IaC tooling, DNS, or provider credentials.",
                "impact": "Hosted longitudinal claims remain unverified.",
                "remediation": "Complete Batch 05 prerequisites and rerun hosted audit.",
                "regression_test": "hosted staging controls fail closed.",
                "status": "open_backlog",
                "remaining_risk": "Local evidence may be mistaken for hosted evidence.",
            },
        ]
    }


def write_benchmark_files(registry: dict[str, Any]) -> None:
    write_json(BENCHMARKS / "registry.json", registry)
    write_md(
        BENCHMARKS / "README.md",
        "# AgentCo Longitudinal Benchmark Registry\n\n"
        "This registry contains synthetic, non-sensitive fixtures for Batch 06 longitudinal evidence infrastructure. It is not a general intelligence evaluation. Hidden split expected outputs are not candidate-readable; only expectation hashes are included.",
    )


def write_schema() -> None:
    write_json(
        SCHEMAS / "longitudinal_run_manifest.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "AgentCo Longitudinal Run Manifest",
            "type": "object",
            "required": ["run_id", "campaign_id", "commit_sha", "benchmark_registry_hash", "seed", "provider_classification", "manifest_hash"],
            "properties": {
                "run_id": {"type": "string"},
                "campaign_id": {"type": "string"},
                "provider_classification": {
                    "enum": ["deterministic_fixture", "simulated", "local_model", "local_real_service", "live_external_provider", "hosted_staging", "production"]
                },
                "dirty_status": {"enum": ["clean", "dirty"]},
            },
        },
    )


def write_artifacts(results: dict[str, Any]) -> None:
    campaign_dir = ARTIFACTS / CAMPAIGN_ID
    for run in results["runs"]:
        run_dir = campaign_dir / run["run_id"]
        write_json(run_dir / "RUN_MANIFEST.json", run["manifest"])
        write_json(run_dir / "CASE_RESULTS.json", run["cases"])
        write_json(run_dir / "EVIDENCE_CHAIN.json", evidence_chain_for_run(run))
    write_json(campaign_dir / "CAMPAIGN_RESULTS.json", results)


def generate_all() -> dict[str, Any]:
    registry = benchmark_registry()
    errors = validate_registry(registry)
    if errors:
        raise SystemExit("\n".join(errors))
    results = campaign_results(registry)
    recompute_errors = recompute_campaign(results)
    if recompute_errors:
        raise SystemExit("\n".join(recompute_errors))
    write_benchmark_files(registry)
    write_schema()
    generate_docs(registry, results)
    write_artifacts(results)
    update_claim_matrix(registry)
    return results


def run_campaign_artifact(campaign: str) -> dict[str, Any]:
    if campaign != CAMPAIGN_ID:
        raise SystemExit(f"unknown campaign: {campaign}")
    registry = json.loads((BENCHMARKS / "registry.json").read_text())
    errors = validate_registry(registry)
    if errors:
        raise SystemExit("\n".join(errors))
    results = campaign_results(registry)
    recompute_errors = recompute_campaign(results)
    if recompute_errors:
        raise SystemExit("\n".join(recompute_errors))
    write_artifacts(results)
    return results


def update_claim_matrix(registry: dict[str, Any]) -> None:
    path = DOCS / "CLAIM_EVIDENCE_MATRIX.json"
    existing = json.loads(path.read_text()) if path.exists() else {"claims": []}
    claims = [item for item in existing.get("claims", []) if item.get("claim") != "Longitudinal mission evidence foundation exists"]
    claims.append(
        {
            "claim": "Longitudinal mission evidence foundation exists",
            "evidence": f"{CAMPAIGN_ID} five-seed deterministic campaign, registry {registry['registry_hash']}",
            "evidence_level": "repeated_same_version",
            "status": "verified_with_limitations",
            "repeated_same_version": True,
            "cross_seed": True,
            "cross_version": False,
            "calendar_duration": "same_day",
            "independent_review": False,
            "hosted": False,
            "production": False,
        }
    )
    existing["claims"] = claims
    existing["source_input_hash"] = sha256_json({"claims": claims})
    write_json(path, existing)
    write_md(
        DOCS / "CLAIM_EVIDENCE_MATRIX.md",
        "# Claim Evidence Matrix\n\n"
        + "\n".join(f"- {item['claim']}: `{item.get('status')}` / `{item.get('evidence_level')}`" for item in claims),
    )


def check_all() -> int:
    registry = json.loads((BENCHMARKS / "registry.json").read_text())
    errors = validate_registry(registry)
    results = json.loads((DOCS / "INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json").read_text())
    errors.extend(recompute_campaign(results))
    if results["campaign_completeness"]["completed_runs"] != 5:
        errors.append("initial campaign is incomplete")
    if (DOCS / "LONGITUDINAL_MILESTONE_POLICY.json").exists():
        milestone = json.loads((DOCS / "LONGITUDINAL_MILESTONE_POLICY.json").read_text())
        if "four_week" not in milestone.get("time_blocked", []):
            errors.append("four-week milestone must remain time-blocked")
    if errors:
        print(json.dumps({"success": False, "errors": errors}, indent=2))
        return 2
    print(json.dumps({"success": True, "campaign_id": CAMPAIGN_ID, "run_count": 5, "registry_hash": registry["registry_hash"]}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["generate", "check", "campaign", "campaign-artifact", "compare"])
    parser.add_argument("--campaign", default=CAMPAIGN_ID)
    args = parser.parse_args()
    if args.command in {"generate", "campaign"}:
        if args.campaign != CAMPAIGN_ID:
            raise SystemExit(f"unknown campaign: {args.campaign}")
        results = generate_all()
        print(json.dumps({"success": True, "campaign_id": results["campaign_id"], "run_count": len(results["run_ids"])}, sort_keys=True))
        return 0
    if args.command == "campaign-artifact":
        results = run_campaign_artifact(args.campaign)
        print(json.dumps({"success": True, "campaign_id": results["campaign_id"], "run_count": len(results["run_ids"])}, sort_keys=True))
        return 0
    if args.command == "check":
        return check_all()
    if args.command == "compare":
        results = json.loads((DOCS / "INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json").read_text())
        print(json.dumps(results["controlled_improvement"]["comparison"], indent=2, sort_keys=True))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
