# Blocked Items

## Hosted staging verification — HST-001

- Human action required: provide or explicitly rescope a hosted cloud account/toolchain, IaC state backend, DNS zone, workload identity, registry, monitoring, backup/restore target, and bounded provider credentials.
- Prepared: hosted staging finding and execution contract exist under `docs/audit/current/`.
- Verification once unblocked: run the hosted staging prerequisite verifier and `make audit-staging-deployment` against the authorized hosted environment.

## Real capability baseline — GCR-010

- Human action required: authorize a currently available provider/model and budget for a new real-provider campaign. Do not reuse the disputed historical `gpt-5.6-luna` authorization without an explicit decision.
- Prepared this iteration: future V7 runner now requires an authorization JSON and records diagnosable provider evidence.
- Verification once unblocked: run canary, execute the 24 frozen cases only if canary passes, then run artifact/semantic-hash/secret-scan verifiers.

## Claude review via Duet

- Human/tooling action required: Claude session quota must reset or authentication/session limit must be cleared.
- Prepared: `duet` is installed and `duet talk` syntax is known.
- Verification once unblocked: run a bounded Claude second-opinion review through `duet talk --repo /Users/Zet/Agentco --new claude ...`.
