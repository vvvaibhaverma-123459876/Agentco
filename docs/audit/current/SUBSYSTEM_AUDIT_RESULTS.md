# Subsystem Audit Results

- Source commit: `4da7f14047f5e31c13b7b93b667ef13731ceff8e`
- Source tree: `6a847fd7823f7c88c79eb3d2a0980818bd295cd2`
- Required subsystems: `18`
- Passed subsystems: `16`
- Failed subsystems: `2`

| Subsystem | Status | Evidence Paths | Active Findings | Historical Findings |
| --- | --- | ---: | --- | --- |
| `l0_runtime_substrate` | `passed` | 3 | none | none |
| `l1_identity_authority` | `passed` | 3 | none | none |
| `l2_resource_budgeting` | `passed` | 3 | none | none |
| `l3_event_memory` | `passed` | 3 | none | none |
| `l4_evidence_retrieval` | `passed` | 3 | none | none |
| `l5_claim_prediction` | `passed` | 3 | none | none |
| `l6_calibration_trust` | `passed` | 3 | none | none |
| `l7_agent_citizenship` | `passed` | 3 | none | none |
| `l8_autonomy_tasks` | `passed` | 3 | none | none |
| `l9_institutions` | `passed` | 3 | none | none |
| `l10_governance_safety` | `passed` | 3 | none | none |
| `l11_judiciary` | `passed` | 3 | none | none |
| `l12_learning_memory` | `passed` | 3 | none | none |
| `l13_capability_expansion` | `passed` | 3 | none | none |
| `l14_civilization_os` | `passed` | 3 | none | none |
| `capability_runtime_protocol` | `failed` | 3 | GCR-010, GCR-011 | GCR-008 |
| `frontend` | `passed` | 3 | none | none |
| `infra_deployment` | `failed` | 3 | HST-001 | none |

This is deterministic committed-evidence audit output. It does not replace the
real-provider capability baseline, hosted staging proof, or independently
diagnosable provider artifacts required by the loop Definition of Done.
