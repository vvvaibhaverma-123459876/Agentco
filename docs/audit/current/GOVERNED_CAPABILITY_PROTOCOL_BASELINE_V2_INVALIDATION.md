# Governed Capability Protocol Baseline V2 Invalidation

Finding `GCR-004` is recorded as an S1 evidence-integrity defect.

The Batch 08C campaign `governed-capability-protocol-baseline-v2` remains preserved as historical evidence, but its `PROTOCOL_BASELINE_ACCEPTED` decision is withdrawn and corrected to `INVALID_CAMPAIGN`.

Reasons:

- The candidate SHA was recorded as the attestation SHA.
- The campaign was not bound to the actual attestation commit.
- A canonical logical hash was labelled as a file-content hash.
- Freeze and artifact verification were not part of the acceptance predicate.
- Schema checks verified file existence rather than committed JSON Schema validity.
- Persistence did not prove retrieval through a recreated store.
- Raw header surfaces were excluded from secret-leak testing.
- Budget reservation evidence was labelled as settlement.
- Provider preflight could overstate availability when reachability was unverified.

Replacement campaigns:

- Protocol: `governed-capability-protocol-baseline-v3`
- Real capability: `governed-capability-genesis-v5`

This invalidation does not alter previous artifacts. It withdraws only the decision classification.
