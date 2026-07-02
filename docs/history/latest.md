# Vendor Risk Triage Benchmark - Leaderboard

**Run ID:** 245f7142-7beb-488e-8b01-6f67748a04ae
**Created:** 2026-06-22T18:06:29.177573
**Commit:** 0d24162b
**Dataset Hash:** 1593d5893b73da36...

Note: This committed result is a deterministic smoke run unless external provider results are present with completed status, provider model id, timestamp, dataset hash, and commit SHA.

## Results

| Rank | Model | Overall Score | Decision Accuracy | Risk Level Accuracy | Policy Compliance | Hallucination Rate | Evidence F1 | Escalation Accuracy |
|------|-------|---|---|---|---|---|---|---|
| 1 | fake:deterministic | 0.711 | 73.3% | 73.3% | 73.3% | 26.7% | 0.586 | 73.3% |

## Scoring Formula

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

## Interpretation

- **Overall Score**: Composite trustworthiness metric (0-1, higher better)
- **Decision Accuracy**: Approval/rejection/escalation correctness
- **Risk Level Accuracy**: Correct severity assessment
- **Policy Compliance**: No violations of stated policies
- **Hallucination Rate**: Unsupported or false claims (0-1, lower better)
- **Evidence F1**: Precision and recall of cited evidence
- **Escalation Accuracy**: Correct escalation decisions
