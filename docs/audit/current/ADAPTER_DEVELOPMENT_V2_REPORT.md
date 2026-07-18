# Adapter Development V2 Report

Development-only discovery used the 24 development cases and existing immutable
subject interfaces.

Supported common primitives found:

- `durable-calibration-task`
- `durable-record-observation-task`

Rejected candidates:

- LLM-backed review and decision paths require unavailable live provider credentials.
- Backend HTTP route contracts are not equivalent across immutable A/B/C without additional bootstrap.
- Civilization runtime paths are absent from Version A.

The V2 adapter bundle is frozen before validation/hidden execution. Validation
and hidden outcomes were not used to modify adapter support decisions.
