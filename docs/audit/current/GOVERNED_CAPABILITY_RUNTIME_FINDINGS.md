# Governed Capability Runtime Findings

Updated for Batch 09B after PR #29 merged into `main`.

## Resolved Evidence-Integrity Findings

| Finding | Severity | Status | Summary |
| --- | --- | --- | --- |
| GCR-001 | S1 | resolved_invalidated | Genesis V1 acceptance withdrawn; corrected decision `INVALID_CAMPAIGN`. |
| GCR-002 | S1 | resolved_reclassified | Genesis V2 kept as protocol execution evidence only; no capability baseline. |
| GCR-003 | S1 | resolved_invalidated | Protocol Baseline V1 acceptance withdrawn. |
| GCR-004 | S1 | resolved_by_protocol_baseline_v3 | Protocol Baseline V2 acceptance withdrawn and replaced by Protocol V3 evidence. |

## Resolved Provider-Boundary Findings

| Finding | Severity | Status | Summary |
| --- | --- | --- | --- |
| GCR-005 | S3 | resolved_batch_08f | Provider URL validation now enforces approved schemes, explicit host allowlisting, DNS resolution, and forbidden-address rejection before provider execution and before each retry attempt. |
| GCR-006 | S3 | resolved_batch_08f | Provider redirects are blocked by default through an explicit no-redirect handler. |

Genesis V5 remains `HOLD_FOR_MORE_EVIDENCE` until real provider configuration
and credentials are supplied and verified. The resolved provider-boundary
findings do not create real-provider capability evidence.

## Batch 09A Readiness Finding

| Finding | Severity | Status | Summary |
| --- | --- | --- | --- |
| GCR-007 | S3 | resolved_batch_09a_readiness_contract | Added the real-provider readiness contract covering configuration, authorization, case manifest, thresholds, semantic hashes, preflight, dry-run, evidence capture and operator runbook. |

Batch 09A readiness does not execute a provider call and does not establish a
real capability baseline.

## Batch 09B Execution Finding

| Finding | Severity | Status | Summary |
| --- | --- | --- | --- |
| GCR-008 | S3 | open_hold_for_more_evidence | Batch 09B did not attempt real-provider execution because no executable campaign authorization artifact exists and the active process environment lacks provider model, endpoint, credential reference and host allowlist configuration. |

Genesis V6 remains `HOLD_FOR_MORE_EVIDENCE` with `execution_attempted = false`.
No provider call occurred, no credentials were recorded, and no capability
baseline or supported domains are claimed.
