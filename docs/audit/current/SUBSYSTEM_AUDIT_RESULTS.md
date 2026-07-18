# Subsystem Audit Results

- Source commit: `5c7adaefc863569197e93501def783fb1c14f067`
- Source tree: `edf86777ef64c3a0d35cffd81bba5b3dd1428f55`
- Required subsystems: `18`
- Passed subsystems: `16`
- Failed subsystems: `2`

| Subsystem | Status | Evidence Paths | Linked Findings |
| --- | --- | ---: | --- |
| `l0_runtime_substrate` | `passed` | 3 | none |
| `l1_identity_authority` | `passed` | 3 | none |
| `l2_resource_budgeting` | `passed` | 3 | none |
| `l3_event_memory` | `passed` | 3 | none |
| `l4_evidence_retrieval` | `passed` | 3 | none |
| `l5_claim_prediction` | `passed` | 3 | none |
| `l6_calibration_trust` | `passed` | 3 | none |
| `l7_agent_citizenship` | `passed` | 3 | none |
| `l8_autonomy_tasks` | `passed` | 3 | none |
| `l9_institutions` | `passed` | 3 | none |
| `l10_governance_safety` | `passed` | 3 | none |
| `l11_judiciary` | `passed` | 3 | none |
| `l12_learning_memory` | `passed` | 3 | none |
| `l13_capability_expansion` | `passed` | 3 | none |
| `l14_civilization_os` | `passed` | 3 | none |
| `capability_runtime_protocol` | `failed` | 3 | GCR-008, GCR-010, GCR-011 |
| `frontend` | `passed` | 3 | none |
| `infra_deployment` | `failed` | 3 | HST-001 |

This is deterministic committed-evidence audit output. It does not replace the
real-provider capability baseline, hosted staging proof, or independently
diagnosable provider artifacts required by the loop Definition of Done.
