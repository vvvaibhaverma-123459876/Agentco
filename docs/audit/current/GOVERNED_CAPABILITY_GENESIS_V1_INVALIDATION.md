# Governed Capability Genesis V1 Invalidation

Campaign `governed-capability-genesis-v1` is preserved but invalidated.

- Campaign methodology: `INVALID`
- Previous decision: `GENESIS_BASELINE_ACCEPTED`
- Corrected decision: `INVALID_CAMPAIGN`
- Capability baseline accepted: `false`
- Promotion implication: `none`
- Finding: `GCR-001` (`S1`, evidence integrity)

## Root Cause

The v1 campaign generated validation and hidden cases inside the runner and
treated completed domain-shaped responses as capability success. It did not use
evaluator-only hidden expectations or task-specific correctness scorers.

## Required Reclassification

The previous artifact remains audit history only. It must not be used as a
future comparison baseline, promotion basis, model-calibration result, or broad
capability claim.

## Invalidating Reasons

- Validation and hidden cases were generated directly by the campaign runner.
- Validation and hidden requests were duplicated or semantically identical.
- No evaluator-only hidden expectations existed.
- Completion status was treated as capability success.
- No domain correctness scorer was applied.
- The deterministic provider returned domain-shaped templates.
- Software-engineering output was not validated through fixture tests.
- Data-analysis output was not evaluated against expected calculations.
- Reasoning output was not evaluated for correctness.
- Planning output was not evaluated against task-specific requirements.
- Provider-generated confidence was hash-derived rather than empirically calibrated.
- The previous acceptance threshold counted domain labels rather than proven capabilities.
