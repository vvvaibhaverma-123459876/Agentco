# Provisioning State

Continuous Completion Loop v2 treats missing external access as a provisioned
resource gap, not a request for approval. The loop must attempt legitimate
alternatives, record outcomes here, and keep working on other items unless a
core item becomes unachievable.

## Claude Via Duet

- Status: unavailable.
- Last check: `duet doctor` failed with Claude session limit resetting at `1:50pm (Asia/Calcutta)`.
- Current action: keep probing once per iteration; use Claude for bounded review/tasks when it becomes available.
- Claims affected: none.

## Real Provider Capability Baseline

- Status: not currently established.
- Current evidence: `GCR-010` and `GCR-011` remain open; prior Genesis V7 attempt used real OpenAI reachability but all 24 cases were schema-invalid and hash-only evidence cannot be independently diagnosed.
- Current action: do not reuse stale or disputed model assumptions. Future execution must query provider model availability from the account, choose a verified available model through a source-bound authorization/config artifact, run canary, then execute the frozen cases only if all gates pass.
- Claims affected: real capability baseline not established; supported domains not claimed; capability improvement not claimed.

## Hosted Staging

- Status: unverified.
- Current evidence: `HST-001` remains open.
- Current action: use local/IaC verifiers where possible. If external hosted resources remain unavailable after genuine attempts, the standard hosted-staging item may be descoped only with a recorded decision and posture docs updated to state hosted operation is unverified.
- Claims affected: hosted staging unverified; production readiness unverified.
