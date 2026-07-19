# Legacy Blocked Items

The loop now follows Continuous Completion Loop v2. Human approval waits are
superseded by autonomous decisions plus provisioned-resource checks. Current
resource gaps are tracked in `.loop/PROVISIONING.md`.

Historical entries below remain as context only; do not treat them as approval
gates.

## Hosted staging verification — HST-001

- Superseding resource record: `.loop/PROVISIONING.md`.
- Prepared: hosted staging finding and execution contract exist under `docs/audit/current/`.
- Verification when provisioned or descoped: run hosted staging prerequisite verifier and `make audit-staging-deployment`, or record a standard-item descoping decision and update all posture claims.

## Real capability baseline — GCR-010

- Superseding resource record: `.loop/PROVISIONING.md`.
- Prepared: future V7 runner requires source-bound authorization/config and records diagnosable provider evidence.
- Verification when provisioned: query available provider models, choose/record one in authorization, run canary, execute the 24 frozen cases only if canary passes, then run artifact/semantic-hash/secret-scan verifiers.

## Diagnosable real-provider evidence — GCR-011

- Superseding resource record: `.loop/PROVISIONING.md`.
- Prepared: `scripts/verify_capability_genesis_artifact.py --check` now rejects missing V7 payload manifests, hash-only provider response evidence and identical response-hash patterns across provider-attempted cases.
- Verification when provisioned: run a new authorized campaign that preserves redacted provider response content, provider request ID hash, finish reason, parser input hash/redacted parser input and audit references for every provider-attempted case; then rerun `python3.13 scripts/verify_capability_genesis_artifact.py --check`.

## Claude review via Duet

- Superseding resource record: `.loop/PROVISIONING.md`.
- Prepared: `duet` is installed and `duet talk` syntax is known.
- Verification when available: run bounded Claude second-opinion tasks through `duet`.
