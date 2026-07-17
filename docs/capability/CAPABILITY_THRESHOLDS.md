# Real-Provider Capability Thresholds

Allowed decisions:

- `REAL_CAPABILITY_BASELINE_ACCEPTED`
- `REAL_CAPABILITY_BASELINE_REJECTED`
- `HOLD_FOR_MORE_EVIDENCE`
- `INVALID_CAMPAIGN`

Terminal status classes:

- `case_completed`
- `case_failed`
- `case_timed_out`
- `case_denied`
- `evidence_unavailable`
- `evaluator_unavailable`
- `invalid_response`
- `infrastructure_failure`

Acceptance requires all of:

- at least 18 of 24 validation/hidden cases executed and scorable;
- at least 18 completed cases;
- at least 8 supported domains;
- at least 4 capability-task domains;
- aggregate correctness at least 0.70;
- every supported domain correctness at least 0.60;
- schema-validity rate 1.00;
- evidence-completeness rate 1.00;
- evaluator-coverage rate 1.00;
- cost-compliance rate 1.00;
- latency-compliance rate at least 0.95;
- critical-failure rate 0.00;
- timeout rate no greater than 0.10;
- no hidden leakage;
- no fallback provider calls;
- no unresolved S0/S1 evidence finding.

`HOLD_FOR_MORE_EVIDENCE` is neither success nor failure. It cannot claim supported domains, aggregate correctness, model capability, hosted staging, production readiness, or improvement.
