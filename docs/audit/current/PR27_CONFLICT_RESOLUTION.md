# PR #27 Conflict Resolution

## Scope

- PR: #27, `audit/remediation-07-cross-version-civilization-evaluation`
- Previous PR head: `be4a44750ad78a8bee024b503c79e5d1856fc684`
- Current `origin/main` merged: `1a98381db9184f766a2d33352ba99927dc8d3229`
- Merge base: `b3bd3dc17b20350d28385213d02a3010dd1fca1e`
- Merge commit: `1786f0ccda8b4684e754cec15cda8d4f1f307ed8`

## Conflict Inventory

The textual conflicts were limited to generated audit ledgers and generated score-validation outputs:

- `docs/audit/FORENSIC_AUDIT_CONTROLS.json`
- `docs/audit/FORENSIC_AUDIT_CONTROLS.md`
- `docs/audit/FORENSIC_FILE_INVENTORY.json`
- `docs/audit/FORENSIC_FILE_INVENTORY.md`
- `docs/audit/current/ACTUAL_RUNTIME_ARCHITECTURE.json`
- `docs/audit/current/ACTUAL_RUNTIME_ARCHITECTURE.md`
- `docs/audit/current/AUTHORITATIVE_IMPLEMENTATIONS.md`
- `docs/audit/current/CLAIM_EVIDENCE_MATRIX.json`
- `docs/audit/current/CLAIM_EVIDENCE_MATRIX.md`
- `docs/audit/current/FILE_AUDIT_LEDGER_BATCH03.json`
- `docs/audit/current/INTEGRATION_CONTRACT_MATRIX.json`
- `docs/audit/current/INTEGRATION_CONTRACT_MATRIX.md`
- `docs/audit/current/RUNTIME_COMPONENT_LEDGER.json`
- `docs/audit/current/RUNTIME_COMPONENT_LEDGER.md`
- `docs/audit/current/RUNTIME_INTEGRATION_FINDINGS.json`
- `docs/audit/current/RUNTIME_INTEGRATION_FINDINGS.md`
- `docs/audit/current/RUNTIME_REACHABILITY.json`
- `docs/audit/current/RUNTIME_REACHABILITY.md`
- `reports/system_run/latest/score_validation.json`
- `reports/system_run/latest/score_validation.md`

## Resolution Rationale

Runtime source, constitution files, civilization reports, and Make targets merged without textual conflicts. Those changes preserve the current `main` civilization runtime improvements while retaining Batch 07's cross-version audit history.

For generated ledgers, the Batch 07 side was used as the semantic conflict base because it contains the invalidated and corrected cross-version evidence classifications. The ledgers were then regenerated with the repository generators:

- `python3.13 scripts/generate_runtime_reachability.py`
- `python3.13 scripts/generate_forensic_inventory.py`
- `python3.13 scripts/generate_forensic_audit_controls.py`
- `cd backend && npm run agentco:score-validation`

This avoids mechanically choosing either stale generated side as final evidence.

## Behaviour Preserved

- Batch 07 invalidated synthetic comparisons remain invalid.
- `subject-native-cross-version-v2-closure` remains a primitive-compatibility closure, not capability evidence.
- `record_observation` remains `storage_write`, not evidence-evaluation capability.
- No primitive operation is counted as a capability task.
- Current `main` civilization runtime, constitution volumes, and completion reports remain present.

## Required Reproof

The merge commit changes the source tree and therefore invalidates any claim that the old PR #27 head is the current integration subject. Batch 07 post-conflict reproof must bind to `1786f0ccda8b4684e754cec15cda8d4f1f307ed8` or a later Batch 07 evidence commit.
