# Batch 08G Final Acceptance

## Scope

PR #28 is the governed capability runtime PR. It is based on `main` after PR #27
was merged at `1fa5e4f31737a1253efbfce6687f68ed9c9578b9`.

No live-provider campaign was executed in Batch 08G.

## Corrected Manifest Record

- freeze candidate SHA: `6e1bf1483cd6f5cb20e0ffb61d6c538dd4b9b12f`
- freeze candidate tree: `e94d5c0469024d8ff8d54c7d9ae3dda56dbde3c1`
- freeze manifest commit SHA: `9f2c11908a47cb48eb00de033a11d098dbdeff46`
- freeze manifest Git blob SHA: `18a1c1b7dd2e5f062efb480bc0575ff85b61bc4c`
- freeze manifest content SHA-256:
  `93d3866845aae1c000f785e9a6c7476345228c526afc67ef9ad3d8511b130744`
- freeze binding commit: `6410661cb980829d678f27844ac32cdc5303f8e8`
- freeze binding logical hash:
  `480f9ba362a1e2893298103dad8e21037279766909b64d85d2d73e2ed7882a79`

The manifest blob was verified with `git rev-parse
9f2c11908a47cb48eb00de033a11d098dbdeff46:docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_MANIFEST.json`.
The manifest content SHA-256 was verified from exact `git show` bytes.

No authoritative Batch 08G report uses the earlier malformed manifest-blob
field.

## Clean-Clone Reproof

Disposable clone path: `/private/tmp/agentco-08g-clean-clone`.

Verified:

- PR #27 merge commit is an ancestor of the PR #28 tip.
- freeze candidate, manifest and binding commits are ancestors of the PR #28 tip.
- registered frozen files match the candidate.
- frozen semantic paths have no post-candidate mutation outside the manifest,
  binding and evidence records.
- stale Batch 08D/08E artifacts do not satisfy the current acceptance predicate.

## Protocol V3

- campaign: `governed-capability-protocol-baseline-v3`
- decision: `PROTOCOL_BASELINE_ACCEPTED`
- cases: `24/24`
- assertions: `94 executed / 94 passed / 0 failed / 0 skipped`
- request schema validation: passed
- invalid request rejection: passed
- terminal response-schema validation: passed
- negative-schema tests: passed
- persistence reinitialization: passed
- corruption rejection: passed
- timeout settlement: passed
- retryable and non-retryable behavior: passed
- audit-reference resolution: passed
- recursive secret scan: passed
- deterministic fallback prevention: passed
- freeze verifier: passed
- artifact verifier: passed
- local semantic hash:
  `84d5419bcaedcc269df96727557e3feedb3037388ae5433146833acfc1a6183d`

The semantic projection includes acceptance-relevant fields and excludes only
timestamps, workflow run IDs, temporary paths, host-specific metadata and full
artifact byte ordering outside acceptance-relevant result fields.

## GCR-005 And GCR-006

Status: resolved.

Verified deployed request path:

- requires HTTPS outside explicit local development
- rejects user-info and malformed authorities
- enforces exact or explicit wildcard allowlisting
- resolves DNS before connection
- rejects forbidden resolved addresses
- covers IPv4 and IPv6 loopback, private, link-local, reserved, multicast and
  unspecified ranges
- detects DNS-answer changes between validation and request attempt
- fails closed on ambiguous or forbidden resolution
- blocks redirects by default
- does not forward credentials to redirect destinations because redirects are
  not followed

Focused provider-boundary tests: `13 passed`.

## Genesis V5

- campaign: `governed-capability-genesis-v5`
- decision: `HOLD_FOR_MORE_EVIDENCE`
- execution attempted: `false`
- planned executions: `24`
- evidence unavailable: `24`
- completed: `0`
- failed: `0`
- timed out: `0`
- supported domains: none
- aggregate correctness: unavailable

No provider call occurred. No fallback output was generated. Evaluator-harness
software and data checks remain evaluator verification only and are not counted
as model capability.

## Readiness Decision

- Protocol/control readiness: `ACCEPTED`
- Runtime implementation: `VERIFIED`
- Real-provider capability: `NOT ESTABLISHED`
- Hosted staging: `BLOCKED / UNVERIFIED`
- Production readiness: `NOT ESTABLISHED`
- Capability improvement: `NOT CLAIMED`

PR #28 may be marked ready for human review only after final-head remote
workflows and manual Protocol V3/Genesis V5 artifacts reproduce this record.

PR #28 must not be merged unless the reviewed SHA matches the evidence-bound
tree.
