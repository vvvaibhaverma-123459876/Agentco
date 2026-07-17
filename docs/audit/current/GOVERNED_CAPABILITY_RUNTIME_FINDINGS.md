# Governed Capability Runtime Findings

Updated for Batch 08E against PR #28 SHA
`89af203e24b6a9e4f5c1636cf5d5bd0c5513ba81`.

## Resolved Evidence-Integrity Findings

| Finding | Severity | Status | Summary |
| --- | --- | --- | --- |
| GCR-001 | S1 | resolved_invalidated | Genesis V1 acceptance withdrawn; corrected decision `INVALID_CAMPAIGN`. |
| GCR-002 | S1 | resolved_reclassified | Genesis V2 kept as protocol execution evidence only; no capability baseline. |
| GCR-003 | S1 | resolved_invalidated | Protocol Baseline V1 acceptance withdrawn. |
| GCR-004 | S1 | resolved_by_protocol_baseline_v3 | Protocol Baseline V2 acceptance withdrawn and replaced by Protocol V3 evidence. |

## Open Non-Blocking Findings

| Finding | Severity | Status | Summary |
| --- | --- | --- | --- |
| GCR-005 | S3 | open_backlog | Provider allowlist does not yet resolve DNS and reject private-range rebinding for non-local live providers. |
| GCR-006 | S3 | open_backlog | Provider transport does not explicitly block or revalidate redirects to another host. |

These S3 findings block live-provider trust-boundary hardening, not Protocol V3
readiness. Genesis V5 remains `HOLD_FOR_MORE_EVIDENCE` until real provider
configuration and credentials are supplied and verified.
