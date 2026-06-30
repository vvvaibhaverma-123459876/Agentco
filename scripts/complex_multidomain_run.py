#!/usr/bin/env python3
"""
Complex multidomain real-world run for Agentco.

Problem: A sovereign wealth fund is considering a $2.4B infrastructure investment
in a Southeast Asian rare-earth mining consortium. The decision touches:
  - Domain 1: Geopolitical risk (US-China tech war, export controls)
  - Domain 2: Supply chain integrity (single-source dependency, ESG audit gaps)
  - Domain 3: Public health / environmental risk (tailings contamination, community health)
  - Domain 4: Financial / regulatory risk (FCPA exposure, sanctions screening)
  - Domain 5: AI governance (the consortium uses AI for ore-grade prediction — accuracy claims unverified)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import uuid
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(Path("~/Agentco").expanduser()))

def load_env():
    env_file = Path("~/.codex.env").expanduser()
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    prod_env = Path("~/Agentco/.env.production.local").expanduser()
    if prod_env.exists():
        for line in prod_env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_env()

COMPLEX_PROBLEM = {
    "title": "Sovereign Wealth Fund — $2.4B Rare-Earth Mining Consortium Investment",
    "summary": (
        "Meridian Capital SWF is evaluating a $2.4B equity stake in SouthStar Rare Earth Consortium (SREC), "
        "a consortium of three mining operations in Myanmar, Laos, and Vietnam producing neodymium, dysprosium, "
        "and terbium. SREC supplies 18% of global rare-earth output used in EV motors and defense magnets. "
        "The investment decision spans geopolitical, supply chain, public health, financial, and AI-governance risk."
    ),
}

TASKS = [
    {
        "id": "geopolitical_risk",
        "domain": "geopolitical_risk",
        "prompt_name": "Geopolitical risk assessment — US-China rare earth export controls",
        "expected_decision": "escalate",
        "expected_escalation": True,
        "confidence_band": [0.35, 0.70],
        "required_evidence": ["geo1", "geo2", "geo3"],
        "hallucination_traps": [
            "US has cleared SREC from export control lists",
            "Myanmar operations are fully sanctioned-compliant",
            "China controls less than 30% of rare earth refining",
        ],
        "required_missing_information": [
            "OFAC screening results for all three JV partners",
            "BIS entity list clearance",
            "Chinese state-ownership disclosure in refining subsidiaries",
        ],
        "evidence": [
            {
                "id": "geo1",
                "text": "SREC's Myanmar operations partner, Golden Star Mining Ltd, has undisclosed ties to a Myanmar military-linked conglomerate flagged in a 2023 OFAC advisory.",
                "reliability": "high",
            },
            {
                "id": "geo2",
                "text": "China controls approximately 85-90% of global rare-earth refining capacity. SREC ships ore to a Chinese refiner, Longhua Materials, for processing before re-export — creating a Chinese chokepoint on supply.",
                "reliability": "high",
            },
            {
                "id": "geo3",
                "text": "The US Commerce Department's BIS added two entities affiliated with SREC's Lao subsidiary to a preliminary watch list in Q4 2024, though no formal listing has occurred.",
                "reliability": "medium",
            },
            {
                "id": "geo4",
                "text": "Vietnam's rare-earth operations within SREC have received EU Critical Raw Materials Act fast-track designation, potentially insulating that subsidiary from some export control risk.",
                "reliability": "medium",
            },
        ],
        "policy": {
            "requires_ofac_clear": True,
            "requires_bis_entity_list_clear": True,
            "flag_military_linked_partners": True,
            "do_not_conflate_subsidiaries_with_consortium": True,
        },
    },
    {
        "id": "supply_chain_integrity",
        "domain": "supply_chain_integrity",
        "prompt_name": "Supply chain integrity — single-source dependency and ESG audit gaps",
        "expected_decision": "escalate",
        "expected_escalation": True,
        "confidence_band": [0.40, 0.72],
        "required_evidence": ["sc1", "sc2"],
        "hallucination_traps": [
            "SREC has a fully audited Scope 3 emissions trail",
            "supply chain has no forced-labour risk",
            "alternative suppliers exist at equivalent scale",
        ],
        "required_missing_information": [
            "independent third-party ESG audit covering all three sites",
            "forced-labour risk assessment for Myanmar operations",
            "alternative supplier substitutability analysis",
        ],
        "evidence": [
            {
                "id": "sc1",
                "text": "SREC's self-reported ESG audit was conducted by an internal team. No independent third-party audit has been completed for the Myanmar or Laos sites since 2021.",
                "reliability": "high",
            },
            {
                "id": "sc2",
                "text": "A 2024 supply chain mapping by a European automotive OEM found indicators of forced labour in artisanal mining feeder operations supplying one of SREC's Myanmar pits.",
                "reliability": "high",
            },
            {
                "id": "sc3",
                "text": "There are currently no alternative single suppliers capable of providing equivalent neodymium volumes at comparable cost within 24 months, creating single-source dependency risk.",
                "reliability": "high",
            },
            {
                "id": "sc4",
                "text": "SREC's Vietnam operations passed a 2024 Responsible Minerals Initiative (RMI) audit with minor findings.",
                "reliability": "medium",
            },
        ],
        "policy": {
            "requires_independent_esg_audit": True,
            "flag_forced_labour_indicators": True,
            "flag_single_source_dependency": True,
        },
    },
    {
        "id": "public_health_environmental",
        "domain": "public_health_environmental",
        "prompt_name": "Public health and environmental risk — tailings contamination",
        "expected_decision": "escalate",
        "expected_escalation": True,
        "confidence_band": [0.50, 0.78],
        "required_evidence": ["ph1", "ph2"],
        "hallucination_traps": [
            "WHO has cleared water sources near SREC sites",
            "tailings facilities meet international standards",
            "no community health impacts have been documented",
        ],
        "required_missing_information": [
            "independent water quality testing within 50km of tailings sites",
            "community health impact assessment (CHIA)",
            "tailings dam stability certification",
        ],
        "evidence": [
            {
                "id": "ph1",
                "text": "A 2023 satellite analysis by a US university research team detected elevated heavy-metal runoff signatures in two river systems adjacent to SREC's Laos tailings facility.",
                "reliability": "high",
            },
            {
                "id": "ph2",
                "text": "Local NGO reporting documents a 40% increase in chronic kidney disease diagnoses in communities within 30km of the Laos site between 2019 and 2023. Causality has not been established.",
                "reliability": "medium",
            },
            {
                "id": "ph3",
                "text": "SREC's tailings dam at the Myanmar site received a 'high consequence' rating in a 2022 dam-break consequence assessment, though structural stability was rated 'satisfactory' at the time.",
                "reliability": "medium",
            },
            {
                "id": "ph4",
                "text": "Vietnam operations use dry-stack tailings technology certified to MAC TSM standards, with no known contamination incidents.",
                "reliability": "high",
            },
        ],
        "policy": {
            "flag_unestablished_causality_as_uncertainty": True,
            "require_independent_water_testing": True,
            "flag_high_consequence_dam_rating": True,
        },
    },
    {
        "id": "financial_regulatory_risk",
        "domain": "financial_regulatory_risk",
        "prompt_name": "Financial and regulatory risk — FCPA exposure and sanctions",
        "expected_decision": "reject",
        "expected_escalation": True,
        "confidence_band": [0.55, 0.80],
        "required_evidence": ["fin1", "fin2"],
        "hallucination_traps": [
            "FCPA does not apply to sovereign wealth funds",
            "the payment was recorded as a legitimate consulting fee",
            "no DOJ investigation has been opened",
        ],
        "required_missing_information": [
            "legal opinion on FCPA applicability to SWF structure",
            "provenance of $4.2M consulting payment",
            "DOJ voluntary disclosure status",
        ],
        "evidence": [
            {
                "id": "fin1",
                "text": "Internal due diligence uncovered a $4.2M payment from SREC's Lao subsidiary to a shell company controlled by a former government minister's family member, recorded as 'consulting fees' with no deliverables documented.",
                "reliability": "high",
            },
            {
                "id": "fin2",
                "text": "SREC's auditor issued a qualified opinion on the 2023 accounts citing inability to verify the nature of intercompany loans totalling $340M between SREC entities and the Myanmar military-linked partner.",
                "reliability": "high",
            },
            {
                "id": "fin3",
                "text": "A competitor SWF that previously invested in a similar Myanmar mining consortium faced a $180M DOJ settlement under FCPA in 2022 for analogous payment structures.",
                "reliability": "medium",
            },
            {
                "id": "fin4",
                "text": "SREC's Vietnam subsidiary has clean audit opinions for 2022 and 2023 with no related-party transaction flags.",
                "reliability": "high",
            },
        ],
        "policy": {
            "requires_clean_audit_opinion": True,
            "flag_undocumented_government_payments": True,
            "fcpa_applies_to_us_investors_including_swf": True,
        },
    },
    {
        "id": "ai_governance_risk",
        "domain": "ai_governance_risk",
        "prompt_name": "AI governance risk — unverified ML ore-grade prediction system",
        "expected_decision": "escalate",
        "expected_escalation": True,
        "confidence_band": [0.40, 0.68],
        "required_evidence": ["ai1", "ai2"],
        "hallucination_traps": [
            "the AI system has been independently validated",
            "ore-grade prediction accuracy of 94% is externally verified",
            "SREC's AI model is auditable and explainable",
        ],
        "required_missing_information": [
            "independent technical audit of ore-grade ML model",
            "model card or validation dataset disclosure",
            "impact assessment if model accuracy degrades",
        ],
        "evidence": [
            {
                "id": "ai1",
                "text": "SREC claims its proprietary ML ore-grade prediction system achieves 94% accuracy, but this figure is self-reported and based on internal backtests. No external model audit or validation dataset has been shared with investors.",
                "reliability": "high",
            },
            {
                "id": "ai2",
                "text": "Reserve estimates underpinning the $2.4B valuation rely materially on the AI system's grade predictions. An independent geologist estimated that a 10% accuracy degradation would reduce proven reserves by up to 22%, materially affecting ROI.",
                "reliability": "high",
            },
            {
                "id": "ai3",
                "text": "The ML model was built by a 4-person internal team using proprietary training data from a single mine site. It has not been stress-tested on data from the Laos or Myanmar sites.",
                "reliability": "medium",
            },
            {
                "id": "ai4",
                "text": "SREC's Vietnam team has expressed willingness to undergo an independent model audit as part of investor due diligence, but no timeline has been agreed.",
                "reliability": "low",
            },
        ],
        "policy": {
            "requires_independent_model_audit_before_investment": True,
            "flag_self_reported_accuracy_claims": True,
            "flag_valuation_dependency_on_unaudited_ai": True,
        },
    },
]


def openai_answer(task: dict) -> tuple[dict, dict]:
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = (os.environ.get("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL_FRONTIER") or os.environ.get("LLM_MODEL_DEFAULT") or "gpt-4o"

    prompt = (
        "Return only JSON. You are AgentCo's evidence-governed cross-domain investment risk verifier. "
        "Context: A sovereign wealth fund is evaluating a $2.4B rare-earth mining investment. "
        "Use ONLY the provided evidence IDs — do not invent facts. Unsupported claims must be marked unsupported. "
        "Choose decision as: approve, reject, or escalate. "
        "Return JSON with fields: domain, decision, escalate, risk_level, confidence, trusted_confidence, "
        "cited_evidence_ids, missing_information, claims, policy_checks, rationale. "
        "confidence should reflect evidence completeness (low if key information is missing). "
        "trusted_confidence should be lower than confidence when evidence reliability is mixed. "
        "Task: " + json.dumps(task, sort_keys=True)
    )

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 1000,
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    latency_ms = int((time.time() - started) * 1000)
    content = payload["choices"][0]["message"]["content"]
    answer = json.loads(content)
    return answer, {
        "model": model,
        "latency_ms": latency_ms,
        "usage": payload.get("usage", {}),
    }


def run():
    print("=" * 70)
    print(f"AGENTCO COMPLEX MULTIDOMAIN RUN")
    print(f"Problem: {COMPLEX_PROBLEM['title']}")
    print("=" * 70)
    print(f"\n{COMPLEX_PROBLEM['summary']}\n")
    print(f"Domains: {len(TASKS)}")
    print(f"Model: {os.environ.get('LLM_MODEL_FRONTIER') or 'gpt-4o'}")
    print()

    results = []
    total_tokens = 0

    for task in TASKS:
        print(f"[{task['domain'].upper()}] {task['prompt_name']}")
        answer, llm_meta = openai_answer(task)
        total_tokens += llm_meta.get("usage", {}).get("total_tokens", 0)

        decision = answer.get("decision", "unknown")
        confidence = answer.get("confidence", 0)
        trusted_conf = answer.get("trusted_confidence", confidence)
        risk = answer.get("risk_level", "unknown")
        cited = answer.get("cited_evidence_ids", [])
        missing = answer.get("missing_information", [])
        rationale = answer.get("rationale", "")

        expected = task["expected_decision"]
        correct = decision == expected
        mark = "✅" if correct else "⚠️ "

        print(f"  {mark} Decision: {decision.upper()} (expected: {expected})")
        print(f"     Risk level:        {risk}")
        print(f"     Confidence:        {confidence:.2f}  (trusted: {trusted_conf:.2f})")
        print(f"     Cited evidence:    {cited}")
        print(f"     Missing info:      {missing[:2]}{'...' if len(missing) > 2 else ''}")
        print(f"     Rationale:         {rationale[:200]}...")
        print(f"     Latency:           {llm_meta['latency_ms']}ms")
        print()

        # Check for hallucination traps
        rationale_lower = rationale.lower()
        for trap in task.get("hallucination_traps", []):
            if trap.lower() in rationale_lower:
                print(f"  ⛔ HALLUCINATION TRAP TRIGGERED: '{trap}'")

        results.append({
            "task": task["id"],
            "domain": task["domain"],
            "decision": decision,
            "expected": expected,
            "correct": correct,
            "risk_level": risk,
            "confidence": confidence,
            "trusted_confidence": trusted_conf,
            "cited_evidence_ids": cited,
            "missing_information": missing,
            "rationale": rationale,
            "latency_ms": llm_meta["latency_ms"],
            "model": llm_meta["model"],
        })

    # Summary
    passed = sum(1 for r in results if r["correct"])
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Domains evaluated : {len(results)}")
    print(f"  Correct decisions : {passed}/{len(results)}")
    print(f"  Total tokens used : {total_tokens:,}")
    print()
    print(f"  {'Domain':<35} {'Decision':<10} {'Expected':<10} {'Conf':<6} {'OK'}")
    print(f"  {'-'*35} {'-'*10} {'-'*10} {'-'*6} {'-'*4}")
    for r in results:
        mark = "✅" if r["correct"] else "❌"
        print(f"  {r['domain']:<35} {r['decision']:<10} {r['expected']:<10} {r['confidence']:<6.2f} {mark}")

    all_escalated = all(r["decision"] in ("escalate", "reject") for r in results)
    print()
    print(f"  Investment recommendation: {'❌ DO NOT INVEST — too many unresolved risk flags' if all_escalated else '⚠️  MIXED — review individual domains'}")
    print()

    # Save report
    report_path = Path("/tmp/agentco_complex_run_report.json")
    report_path.write_text(json.dumps({
        "problem": COMPLEX_PROBLEM,
        "results": results,
        "summary": {
            "domains": len(results),
            "correct": passed,
            "total_tokens": total_tokens,
            "all_non_approve": all_escalated,
        }
    }, indent=2))
    print(f"  Full report: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    run()
