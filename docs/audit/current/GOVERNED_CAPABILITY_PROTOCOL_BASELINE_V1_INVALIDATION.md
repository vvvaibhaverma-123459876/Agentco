# Governed Capability Protocol Baseline V1 Invalidation

Finding `GCR-003` is recorded as an S1 evidence-integrity defect.

The Batch 08B protocol campaign `governed-capability-protocol-baseline-v1` is preserved as historical evidence, but its `PROTOCOL_BASELINE_ACCEPTED` decision is withdrawn and corrected to `INVALID_CAMPAIGN`.

Root causes:

- The freeze candidate was followed by changes to a declared frozen file.
- The freeze verifier did not inspect every declared frozen path.
- Several named failure controls were hardcoded to pass.
- Malformed-response, transport-failure and oversized-response behavior was not executed in the protocol artifact.
- Timeout, retry, redaction and audit-reference cases did not prove their named controls.
- Real capability acceptance omitted mandatory governance and evidence conditions.
- Software scoring trusted provider-declared test outcomes.

The real-provider campaign decision remains `HOLD_FOR_MORE_EVIDENCE`; it is not upgraded or invalidated by this protocol finding.

Replacement campaigns:

- Protocol: `governed-capability-protocol-baseline-v2`
- Real capability: `governed-capability-genesis-v4`
