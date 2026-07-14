# Capability Versus Primitive Classification

`subject-native-cross-version-v1` is reclassified as:

```text
VALID PROCESS-EXECUTION EVIDENCE
VALID CALIBRATION-UTILITY COMPATIBILITY EVIDENCE
INSUFFICIENT BROAD CAPABILITY EVIDENCE
```

The V1 adapter supplied both `confidence` and `outcome`; the immutable subject
calculated the Brier score. That proves a runtime calculation primitive, not
prediction capability, reasoning capability, calibration judgment, or model
calibration improvement.

For V2, completed operations are scored by class:

- `runtime_primitive`: Brier-score calculation.
- `storage_write`: durable observation recording.
- `capability_task`: none currently common across A, B and C.

The durable observation operation accepts evidence-shaped input, stores/returns
the supplied observation, and preserves request/payload hashes. It does not
evaluate conflicting evidence, select accepted/rejected evidence, determine
truth, or generate confidence. It is therefore excluded from common support for
the `evidence_evaluation` benchmark domain.

Only `capability_task` results may support broad capability-improvement claims.
