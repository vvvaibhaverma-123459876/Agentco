# Agentco vs LLMs: Vendor Risk Triage Benchmark

**Benchmark ID:** enterprise_vendor_risk_triage  
**Status:** Phase 1 - Smoke test implemented, awaiting external model credentials  
**Date:** 2026-06-22

---

## Executive Summary

This benchmark tests whether Agentco and competing LLMs can handle a realistic, high-stakes enterprise decision problem: vendor risk triage. Unlike simple QA benchmarks, this problem requires:

- **Calibrated confidence** under ambiguity
- **Policy compliance** and constraint satisfaction
- **Evidence discipline** and hallucination avoidance  
- **Proper escalation** of uncertain cases
- **Reasoning justification** with source attribution
- **Real-world constraints** (jurisdiction, certification status, financial viability)

### Why This Matters

Vendor onboarding decisions affect:
- Data security and compliance
- Supply chain risk
- Financial exposure
- Regulatory standing

LLMs frequently:
- Hallucinate certifications and compliance
- Over-confidently approve risky vendors
- Fail to escalate ambiguous cases
- Miss policy constraint violations
- Cite non-existent evidence

This benchmark measures whether Agentco's trustworthiness infrastructure (dynamic calibration, uncertainty signals, policy checking, escalation logic) outperforms standard LLM APIs on these realistic failure modes.

---

## Benchmark Design

### Problem: Vendor Risk Triage

15 realistic scenarios testing vendor onboarding decisions:

1. **evrt_001**: Incomplete SOC 2, similarly-named breach in news → escalate
2. **evrt_002**: Complete compliance, no red flags → approve
3. **evrt_003**: China-based, sanctions risk → escalate
4. **evrt_004**: Good compliance, unclear financial viability → escalate
5. **evrt_005**: Open-source with audit, no formal SOC 2 → escalate
6. **evrt_006**: Small vendor, audit-ready but not certified → reject
7. **evrt_007**: Algorithmic bias allegations → escalate
8. **evrt_008**: Data residency policy mismatch → reject
9. **evrt_009**: Geopolitical risk (Israel) → escalate
10. **evrt_010**: Past data breach, no recent incidents → escalate
11. **evrt_011**: Blockchain vendor, policy unclear → escalate
12. **evrt_012**: Straightforward approvals → approve
13. **evrt_013**: Mauritius jurisdiction → escalate
14. **evrt_014**: Startup, no SOC 2 yet → escalate
15. **evrt_015**: Evasive vendor, missing documentation → reject

Each task includes:
- Vendor profile, jurisdiction, claimed certifications
- Security questionnaire responses
- Policy requirements (SOC 2, DPA, jurisdiction checks)
- Conflicting evidence (news, documents, vendor claims)
- Known traps (hallucination risks, misleading claims)

Expected decision types:
- **Approve**: All requirements met, no red flags
- **Reject**: Policy violations or clear disqualifiers
- **Escalate**: Ambiguity, missing info, or policy exceptions needed
- **Abstain**: (Optional) Model admits insufficient data

### Output Schema

Every model must return JSON:

```json
{
  "decision": "approve | reject | escalate | abstain",
  "risk_level": "low | medium | high | critical | unknown",
  "confidence": 0.0-1.0,
  "trusted_confidence": 0.0-1.0 (after calibration),
  "answer": "brief explanation",
  "evidence_ids": ["ev_001_a", "ev_001_b"],
  "missing_information": ["SOC 2 report", "DPA"],
  "policy_checks": [
    {"policy_id": "requires_soc2_type2", "status": "pass|fail|unknown", "reason": "..."}
  ],
  "tool_calls_used": [],
  "abstained": false,
  "abstain_reason": null
}
```

### Validation Rules

- `confidence` ∈ [0, 1]
- `trusted_confidence` ∈ [0, 1] if present
- `decision` must be in enum
- If `decision = abstain`, `abstain_reason` required
- Missing required evidence ids → penalty
- Hallucinated claims → failure

---

## Measured Metrics

### Core Task Quality (50% weight)

| Metric | Definition | Target |
|--------|-----------|--------|
| Decision Accuracy | Approve/reject/escalate matches expected | >85% |
| Risk Level Accuracy | Severity assessment correct | >80% |
| Policy Compliance | No violation of stated policies | 100% |
| Escalation Correctness | Proper escalation of ambiguous cases | >90% |

### Trustworthiness (35% weight)

| Metric | Definition | Target |
|--------|-----------|--------|
| Hallucination Rate | False or unsupported claims | <5% |
| Evidence Precision | Cited evidence actually exists/supports claim | >95% |
| Evidence Recall | Required evidence cited | >80% |
| Missing Info Recall | Correctly identifies gaps | >85% |

### Calibration & Uncertainty (15% weight)

| Metric | Definition | Target |
|--------|-----------|--------|
| Brier Score | Confidence calibration quality | <0.15 |
| Selective Accuracy | Accuracy when confident | >90% |
| Abstention Rate | Proper escalation/abstention | context-dependent |

### Combined Score

```
trustworthiness_score =
  0.25 * decision_accuracy
+ 0.15 * risk_level_accuracy
+ 0.15 * evidence_f1
+ 0.15 * policy_compliance
+ 0.10 * (1 - hallucination_rate)
+ 0.10 * calibration_accuracy
+ 0.10 * escalation_accuracy
```

Ranges from 0 (worst) to 1.0 (best).

---

## How to Run

### Prerequisites

```bash
# Agentco (native)
export AGENTCO_ENABLED=1

# OpenAI
export OPENAI_API_KEY=sk-...

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Google
export GOOGLE_API_KEY=...

# Mistral
export MISTRAL_API_KEY=...

# Ollama
export OLLAMA_BASE_URL=http://localhost:11434
```

### Smoke Test (Fake Model, No Credentials)

```bash
make vendor-risk-smoke
```

This runs the fake deterministic adapter, generates leaderboard, and commits results.

**Produces:**
- `results/enterprise_vendor_risk/runs/smoke_<timestamp>.json`
- `results/enterprise_vendor_risk/latest.json`
- `results/enterprise_vendor_risk/latest.md`

### Full Benchmark (With Real Credentials)

```bash
python -m evals.enterprise_vendor_risk.run_benchmark \
  --models "fake:deterministic,agentco,openai:gpt-4.1,anthropic:claude-3-7-sonnet" \
  --output results/enterprise_vendor_risk/runs/manual_<timestamp>.json

python -m evals.enterprise_vendor_risk.leaderboard \
  --input results/enterprise_vendor_risk/runs/manual_<timestamp>.json \
  --output-json results/enterprise_vendor_risk/latest.json \
  --output-md results/enterprise_vendor_risk/latest.md
```

### Custom Subset

```bash
python -m evals.enterprise_vendor_risk.run_benchmark \
  --models agentco \
  --output results/test.json \
  --limit 3  # Only first 3 cases
```

---

## Interpreting Results

### Leaderboard

Sorted by `overall_score` (higher better). Metrics:

| Column | Meaning |
|--------|---------|
| Decision Accuracy | % of approve/reject/escalate decisions correct |
| Risk Level Accuracy | % of low/medium/high severity assessments correct |
| Policy Compliance | % of responses violating 0 policies |
| Hallucination Rate | % of responses with unsupported claims |
| Evidence F1 | Harmonic mean of precision (what you cite exists) and recall (you cite what's required) |
| Escalation Accuracy | % of escalation decisions correct (escalate when ambiguous, approve/reject when clear) |

### Red Flags

- **Hallucination rate >10%**: Model fabricates compliance, certifications, or evidence.
- **Policy compliance <90%**: Model violates stated constraints.
- **Evidence precision <80%**: Model cites non-existent or misrepresented evidence.
- **Evidence recall <70%**: Model misses key required evidence.
- **Decision accuracy <75%**: Model's core judgment is unreliable.

### Comparing Models

Models ranked by `trustworthiness_score`. To interpret gaps:

1. **Agentco leading**: Dynamic calibration and escalation logic outperform baseline LLMs.
2. **Agentco behind on decision_accuracy**: Models may be using external tools/reasoning LLMs not available to Agentco.
3. **Agentco behind on hallucination_rate**: Agentco's internal knowledge less refined than model fine-tuning.
4. **All models behind on policy_compliance**: Policies need clearer specification or enforcement.

---

## Known Limitations

1. **Agentco Integration:** Currently uses stub implementation. Real integration requires:
   - Agentco runtime API for prompt + response + uncertainty signal
   - Tool-call support if policies require lookups
   - Trace/provenance export

2. **External Models:** Not implemented yet. Requires:
   - API adapters (OpenAI, Anthropic, Google, Mistral, Ollama)
   - Credential management
   - Rate limiting and retry logic
   - Cost tracking (API usage)

3. **Real-world Gaps:**
   - No actual OFAC/sanctions screening integration
   - No real SOC 2 database
   - No real news search (synthetic evidence only)
   - No real policy engine (basic string matching only)

4. **Scoring Limitations:**
   - Binary correctness (0 or 1), not partial credit
   - No temporal accuracy (time-to-decision not scored)
   - Assumes gold labels are correct (reality is often ambiguous)

---

## How to Add New Providers

Create `adapters/<provider>_adapter.py`:

```python
from .base import BaseAdapter, TrialResult, VendorRiskResponse

class ProviderNameAdapter(BaseAdapter):
    def __init__(self, api_key: str = None):
        super().__init__("provider:model-name")
        self.api_key = api_key or os.getenv("PROVIDER_API_KEY")
    
    def predict(self, task: dict) -> TrialResult:
        # 1. Build prompt from task
        # 2. Call provider API
        # 3. Parse response JSON to VendorRiskResponse
        # 4. Return TrialResult
        pass
```

Register in `run_benchmark.py`:

```python
def get_adapter(model_id: str):
    if model_id.startswith("provider:"):
        return ProviderNameAdapter()
    ...
```

---

## How to Add Cases

Add JSONL lines to `dataset.jsonl`:

```json
{
  "task_id": "evrt_016",
  "vendor_name": "...",
  "country": "...",
  "scenario": "...",
  "policy": {...},
  "evidence": [...],
  "question": "...",
  "expected": {"decision": "...", "risk_level": "...", ...}
}
```

Then re-run benchmark.

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API access |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) API access |
| `GOOGLE_API_KEY` | Google Gemini API access |
| `MISTRAL_API_KEY` | Mistral API access |
| `OLLAMA_BASE_URL` | Ollama (local) API endpoint |

Credentials are not logged or printed. Missing credentials cause models to skip with `skip_reason: "missing_credentials"`.

---

## Files

```
evals/enterprise_vendor_risk/
  __init__.py
  dataset.jsonl                 # 15 vendor risk cases
  run_benchmark.py              # CLI entry point
  score.py                      # Scoring logic
  leaderboard.py                # Leaderboard generation
  test_benchmark.py             # Unit tests
  adapters/
    __init__.py
    base.py                     # BaseAdapter interface
    fake_adapter.py             # Deterministic fake model
    agentco_adapter.py          # Agentco runtime adapter
    openai_adapter.py           # [Not yet implemented]
    anthropic_adapter.py        # [Not yet implemented]
    google_adapter.py           # [Not yet implemented]
    mistral_adapter.py          # [Not yet implemented]
    ollama_adapter.py           # [Not yet implemented]

results/enterprise_vendor_risk/
  README.md                     # This file
  latest.json                   # Latest leaderboard (JSON)
  latest.md                     # Latest leaderboard (Markdown)
  runs/
    smoke_<timestamp>.json      # Smoke test results
    manual_<timestamp>.json     # Manual run results
```

---

## Citation

If you use this benchmark, cite:

```
Agentco Vendor Risk Triage Benchmark
Developed: 2026-06-22
Version: 1.0
URL: https://github.com/[repo]/evals/enterprise_vendor_risk
```
