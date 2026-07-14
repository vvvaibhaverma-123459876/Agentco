# Three-Version Interface Intersection

Subjects:

- A: `fb27dc0529d3c5d11480503bfbcf6f2d156f5b04`
- B: `651794a41513db1e40930f08c253ef261af7c1e7`
- C: `81cd17431f826d9d3cda06b9127758751e44b798`

## Common Interfaces

Two provider-free interfaces are semantically common across A, B and C:

- `durable-calibration-task`: runtime primitive. The subject calculates Brier score from adapter-supplied confidence and outcome.
- `durable-record-observation-task`: storage/retrieval primitive. The subject records and returns an observation payload.

Neither is a broad reasoning, planning, governance, memory, recovery, software
engineering, data-analysis or civilization capability task.

## Rejected Candidates

- LLM-backed review/decision paths require live provider credentials.
- Backend HTTP routes are not equivalent across A, B and C without additional bootstrap/auth/database contracts.
- Civilization runtime paths are not present in Version A and cannot enter the primary common-core comparison.

## Conclusion

V2 can expand beyond the calibration utility only to a second runtime primitive.
The broad capability threshold remains unmet.
