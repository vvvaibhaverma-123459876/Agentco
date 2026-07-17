# Batch 08F Integration Report

## Batch 07 Base

- PR #27 starting SHA: `be4a44750ad78a8bee024b503c79e5d1856fc684`
- resolved Batch 07 SHA: `a3b98960ada6716531734cbc784d96960cee31de`
- PR #27 merge commit: `1fa5e4f31737a1253efbfce6687f68ed9c9578b9`
- conflict resolution report: `docs/audit/current/PR27_CONFLICT_RESOLUTION.md`
- post-conflict reproof report: `docs/audit/current/BATCH_07_POST_CONFLICT_REPROOF.md`

PR #27 was merged only after semantic conflict resolution and required gates
passed. PR #28 remains unmerged.

## PR28 Restack

- PR #28 pre-restack SHA: `7259e6271124f3475c5b5bed81036c36752bd72f`
- old base: `audit/remediation-07-cross-version-civilization-evaluation`
- new intended base after PR #27 merge: `main`
- restack merge commit: `2db3e0b`
- current local evidence SHA after Genesis HOLD: `b96354d3fa1b16d5d88b4c39ed21977b830d0be0`

PR #28 remains draft until all final-head remote workflows and artifact checks
complete.

## Provider Boundary

- `GCR-005`: resolved by resolved-destination validation and private-range
  rejection.
- `GCR-006`: resolved by disabling redirects by default.

No live provider campaign was executed.

## Regenerated Freeze Evidence

- freeze candidate: `dfd36daf97133fec52dcd664c5dd8dca2d3bef00`
- freeze candidate tree: `6a7d108d836557fe49c77511ca771710341e35c4`
- freeze manifest commit: `898bed576715b9d64274c03e85e0d5bc543ba8ef`
- freeze manifest blob: `22a60d1b0608e128ff6b00f951ef7160258fe7dc`
- freeze manifest SHA-256: `8cfde6e48bb6ed1b9a4648fa03265aec7a69f33660f343ba621a765b7e383a01`
- freeze binding commit: `af06c343f2f614eb6b0355d5b7a02a2f93837d02`
- freeze binding logical hash:
  `4ca5aaffc64c5e447a550d5379c38107ef4d1971537668c2f093e8623cafa3c7`
- frozen-file count: `56`

Freeze verification passed locally.

## Protocol V3

- campaign: `governed-capability-protocol-baseline-v3`
- local campaign execution SHA: `af06c343f2f614eb6b0355d5b7a02a2f93837d02`
- cases: `24/24`
- assertions: `94 executed / 94 passed / 0 failed / 0 skipped`
- decision: `PROTOCOL_BASELINE_ACCEPTED`
- internal payload hash:
  `fd370f790b62c92fa079b44a9c66c48d9b0567cbf093a97d944459bc56f4670a`
- semantic protocol hash:
  `3579d7dc989762f405c9afd86e0369ddef88551b17ec2f310d9be629f94de6ce`

The semantic hash is the stable acceptance-relevant hash. Full artifact payload
hashes may differ between local and GitHub executions only for documented
execution metadata.

## Genesis V5

- campaign: `governed-capability-genesis-v5`
- local campaign execution SHA: `b64d8932de89dcceff312313761d145870bd7ee5`
- provider preflight: `unavailable`
- execution attempted: `false`
- planned cases: `24`
- evidence unavailable: `24`
- supported domains: none
- aggregate correctness: unavailable
- decision: `HOLD_FOR_MORE_EVIDENCE`
- internal payload hash:
  `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`

Genesis V5 remains an honest provider-evidence HOLD. No deterministic,
mock-provider, evaluator-harness or protocol result is counted as real
capability evidence.

## Remaining Work Before Review

After push, PR #28 must be retargeted to `main` and final-head workflows must
run:

- CI
- Constitution Check
- Clean-Room Audit
- Runtime Integration Audit
- Staging Deployment Audit
- Capability Runtime Audit
- manual Protocol V3
- manual Genesis V5 governed HOLD

The workflow Protocol V3 artifact must report the same semantic protocol hash
for the regenerated freeze binding. If it does not, Protocol V3 acceptance must
be held.
