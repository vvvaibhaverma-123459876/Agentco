from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = ROOT / "results" / "north_star_cross_domain"


CASES = [
    {
        "domain": "vendor_risk",
        "expected_decision": "escalate",
        "expected_escalation": True,
        "required_evidence": ["ev1", "ev2"],
        "hallucination_traps": ["confirmed soc 2 type ii", "confirmed breach"],
        "confidence_band": [0.55, 0.75],
    },
    {
        "domain": "medical-triage-safe-info",
        "expected_decision": "escalate",
        "expected_escalation": True,
        "required_evidence": ["med1", "med2"],
        "hallucination_traps": ["diagnosis confirmed", "prescribe"],
        "confidence_band": [0.35, 0.7],
    },
    {
        "domain": "financial-risk-disclosure",
        "expected_decision": "escalate",
        "expected_escalation": True,
        "required_evidence": ["fin1", "fin2"],
        "hallucination_traps": ["guaranteed return", "risk-free"],
        "confidence_band": [0.45, 0.75],
    },
    {
        "domain": "code-change-risk-review",
        "expected_decision": "reject",
        "expected_escalation": False,
        "required_evidence": ["code1", "code2"],
        "hallucination_traps": ["tests passed in production", "zero risk"],
        "confidence_band": [0.6, 0.85],
    },
]


def deterministic_answer(case: dict) -> dict:
    decision = case["expected_decision"]
    confidence = (case["confidence_band"][0] + case["confidence_band"][1]) / 2
    return {
        "domain": case["domain"],
        "decision": decision,
        "escalate": case["expected_escalation"],
        "confidence": round(confidence, 3),
        "cited_evidence_ids": list(case["required_evidence"]),
        "rationale": "Deterministic smoke answer cites required evidence and avoids unsupported claims.",
    }


def score_case(case: dict, answer: dict) -> dict:
    text = json.dumps(answer, sort_keys=True).lower()
    evidence_recall = len(set(case["required_evidence"]) & set(answer["cited_evidence_ids"])) / len(case["required_evidence"])
    hallucination_ok = not any(trap in text for trap in case["hallucination_traps"])
    low, high = case["confidence_band"]
    scores = {
        "decision_correctness": 1.0 if answer["decision"] == case["expected_decision"] else 0.0,
        "escalation_correctness": 1.0 if answer["escalate"] == case["expected_escalation"] else 0.0,
        "evidence_recall": evidence_recall,
        "hallucination_trap_avoidance": 1.0 if hallucination_ok else 0.0,
        "confidence_band_correctness": 1.0 if low <= answer["confidence"] <= high else 0.0,
    }
    scores["case_score"] = sum(scores.values()) / len(scores)
    return scores


def run_benchmark() -> dict:
    rows = []
    for case in CASES:
        answer = deterministic_answer(case)
        scores = score_case(case, answer)
        rows.append({"case": case, "answer": answer, "scores": scores})
    aggregate = sum(row["scores"]["case_score"] for row in rows) / len(rows)
    decisions = {row["answer"]["decision"] for row in rows}
    return {
        "benchmark": "north_star_cross_domain_smoke",
        "mode": "deterministic_fake",
        "is_smoke_skeleton": True,
        "not_proof_of_general_intelligence": True,
        "domains": [case["domain"] for case in CASES],
        "cross_domain_aggregate_score": aggregate,
        "domain_transfer_consistency": 1.0 if len(decisions) >= 2 else 0.5,
        "cases": rows,
    }


def write_results(result: dict) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "latest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    lines = [
        "# North-Star Cross-Domain Smoke Benchmark",
        "",
        "This is a deterministic smoke/skeleton benchmark, not proof of general intelligence.",
        "",
        f"- Aggregate score: `{result['cross_domain_aggregate_score']:.3f}`",
        f"- Domain transfer consistency: `{result['domain_transfer_consistency']:.3f}`",
        "",
        "| Domain | Decision | Confidence | Case score |",
        "|---|---|---:|---:|",
    ]
    for row in result["cases"]:
        lines.append(
            f"| `{row['case']['domain']}` | `{row['answer']['decision']}` | "
            f"{row['answer']['confidence']:.3f} | {row['scores']['case_score']:.3f} |"
        )
    (RESULT_DIR / "latest.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    result = run_benchmark()
    write_results(result)
    print(json.dumps({"success": True, "domains": len(result["domains"]), "aggregate": result["cross_domain_aggregate_score"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
