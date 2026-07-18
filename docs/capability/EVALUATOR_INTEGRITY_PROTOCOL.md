# Evaluator Integrity Protocol

The evaluator measures real-provider outputs without becoming capability evidence.

Rules:

- Provider-visible requests must not contain expected answers, hidden tests, rubrics, scoring thresholds, or evaluator-only fixtures.
- Evaluator inputs and outputs are stored separately from provider outputs.
- Evaluator identity and version are recorded for every scored case.
- Evaluator failure is `evaluator_unavailable`, not provider failure unless policy explicitly maps it.
- Missing evidence is not silently scored as zero; it is classified according to the threshold specification.
- Blind scoring hides provider identity when provider identity is not needed for safety or model mismatch checks.
- Known-good and known-bad calibration responses must be scored during readiness checks to prove evaluator discrimination.

Scoring dimensions:

- task correctness;
- schema validity;
- evidence completeness;
- critical failure conditions;
- abstention and unsupported handling;
- latency and cost compliance;
- domain threshold satisfaction.

Evaluator outputs are never counted as provider outputs. A deterministic fixture or evaluator harness may prove evaluator plumbing only; it cannot establish real-provider capability.
