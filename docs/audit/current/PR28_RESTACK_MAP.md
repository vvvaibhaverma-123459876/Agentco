# PR28 Restack Map

## Inputs

- PR #28 pre-restack SHA: `7259e6271124f3475c5b5bed81036c36752bd72f`
- old base: `audit/remediation-07-cross-version-civilization-evaluation`
- merged Batch 07 main SHA: `1fa5e4f31737a1253efbfce6687f68ed9c9578b9`
- restack method: normal merge of `origin/main`, not force-push or history rewrite

## Restack Commits

- merge commit: `2db3e0b`
- provider destination remediation: `1eb3789`
- freeze script reference-resolution fix: `702a1a8`
- protocol mock-provider local opt-in fix: `dfd36da`
- active freeze manifest commit: `898bed576715b9d64274c03e85e0d5bc543ba8ef`
- active freeze binding commit: `af06c343f2f614eb6b0355d5b7a02a2f93837d02`
- Protocol V3 local evidence commit: `b64d8932de89dcceff312313761d145870bd7ee5`
- Genesis V5 local HOLD evidence commit: `b96354d3fa1b16d5d88b4c39ed21977b830d0be0`

## Conflict Resolution

The restack encountered generated audit-ledger conflicts inherited from the
Batch 07 main merge. Resolution preserved Batch 08 governed capability runtime
controls while retaining the merged Batch 07 evidence-integrity controls.

Source files for the capability runtime merged without textual conflicts.

## Evidence Regeneration

Prior Batch 08D/08E freeze evidence is stale for the restacked tree. Batch 08F
regenerated:

- freeze candidate
- freeze manifest
- freeze binding
- Protocol V3 local artifact
- Genesis V5 local HOLD artifact

Remote workflow artifacts must be regenerated after push and compared against
the semantic Protocol V3 hash.

## PR Posture

PR #28 must be retargeted to `main` after PR #27 merge. It remains draft and
unmerged. It must not be marked ready until final-head workflows and semantic
artifact checks pass.
