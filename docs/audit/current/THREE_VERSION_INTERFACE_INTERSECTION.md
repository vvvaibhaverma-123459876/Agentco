# Three-Version Interface Intersection

Subjects:

- A: `fb27dc0529d3c5d11480503bfbcf6f2d156f5b04`
- B: `651794a41513db1e40930f08c253ef261af7c1e7`
- C: `81cd17431f826d9d3cda06b9127758751e44b798`

## Common Interfaces

One provider-free benchmark interface and one provider-free storage primitive
are semantically common across A, B and C:

- `durable-calibration-task`: runtime primitive. The subject calculates Brier score from adapter-supplied confidence and outcome.
- `durable-record-observation-task`: storage-write primitive. The subject records and returns a supplied observation payload.

The durable observation operation is not common support for the
`evidence_evaluation` benchmark domain. It does not evaluate conflicting
evidence, determine truth, accept or reject evidence, or produce confidence.

Neither operation is a broad reasoning, planning, governance, memory, recovery,
software engineering, data-analysis or civilization capability task.

## Rejected Candidates

- LLM-backed review/decision paths require live provider credentials.
- Backend HTTP routes are not equivalent across A, B and C without additional bootstrap/auth/database contracts.
- Civilization runtime paths are not present in Version A and cannot enter the primary common-core comparison.

## Conclusion

V2 can expand beyond the calibration utility only to a second storage primitive.
The broad capability threshold remains unmet.
