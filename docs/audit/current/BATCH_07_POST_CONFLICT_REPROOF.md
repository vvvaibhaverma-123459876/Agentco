# Batch 07 Post-Conflict Reproof

## Subject

- Branch: `audit/remediation-07-cross-version-civilization-evaluation`
- Merge commit under reproof: `1786f0ccda8b4684e754cec15cda8d4f1f307ed8`
- Previous PR #27 head: `be4a44750ad78a8bee024b503c79e5d1856fc684`
- Merged `origin/main`: `1a98381db9184f766a2d33352ba99927dc8d3229`

## Reproof Requirements

The post-conflict tree must re-establish:

- evaluation subject bindings are unchanged for immutable A/B/C subjects;
- synthetic evaluator-side outputs remain invalidated;
- closure campaign does not report broad capability evidence;
- primitive operations remain separated from capability tasks;
- generated ledgers match the merged tree;
- release, clean-room, runtime integration, staging, and constitution gates pass.

## Initial Reproof Commands

Completed during conflict resolution:

```bash
python3.13 scripts/generate_runtime_reachability.py
python3.13 scripts/generate_forensic_inventory.py
python3.13 scripts/generate_forensic_audit_controls.py
cd backend && npm run agentco:score-validation
```

Pending canonical gates:

```bash
make release-gate
make audit-clean-room
make audit-runtime-integration
make audit-staging-deployment
make subject-native-cross-version-campaign \
  BASELINE=fb27dc0529d3c5d11480503bfbcf6f2d156f5b04 \
  RAW_CANDIDATE=651794a41513db1e40930f08c253ef261af7c1e7 \
  RECONCILED_CANDIDATE=81cd17431f826d9d3cda06b9127758751e44b798 \
  CAMPAIGN=subject-native-cross-version-v2-closure
```

## Current Verdict

Pending. PR #27 must not be merged until post-conflict gates complete and generated evidence is bound to the resolved tree.
