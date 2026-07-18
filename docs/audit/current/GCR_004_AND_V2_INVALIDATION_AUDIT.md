# GCR-004 And Protocol V2 Invalidation Audit

## Result

GCR-004 remains permanently recorded in:

- `docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V2_INVALIDATION.json`
- `docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V2_INVALIDATION.md`

The invalidated campaign is `governed-capability-protocol-baseline-v2`.
The withdrawn decision is `PROTOCOL_BASELINE_ACCEPTED`.
The corrected decision is `INVALID_CAMPAIGN`.

## Search

Searched current code, documentation, tests, workflows, benchmark directories,
PR #28 body and generated evidence references for stale V2 acceptance claims.

Findings:

- Historical V2 benchmark files and Make target still exist for reproducibility.
- Tests explicitly assert that V2 is invalidated.
- PR #28 body states GCR-004 and Protocol V2 invalidation.
- The current workflow acceptance predicate checks only Protocol V3.
- No current report or PR text treats Protocol V2 as accepted.
- No current acceptance predicate selects stale V2 artifacts.

Protocol V3 uses new campaign identity
`governed-capability-protocol-baseline-v3` and does not inherit V2 conclusions.
