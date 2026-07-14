# Remediation 07D: Evidence Binding and Subject-Native V2

## Scope

Batch 07D closes evidence-binding gaps in the subject-native cross-version campaign and expands the common-core comparison beyond the prior calibration-only primitive.

Immutable subjects remain unchanged:

- Version A: `fb27dc0529d3c5d11480503bfbcf6f2d156f5b04`
- Version B: `651794a41513db1e40930f08c253ef261af7c1e7`
- Version C: `81cd17431f826d9d3cda06b9127758751e44b798`

## V1 Reclassification

`subject-native-cross-version-v1` is preserved as:

- `VALID PROCESS-EXECUTION EVIDENCE`
- `VALID CALIBRATION-UTILITY COMPATIBILITY EVIDENCE`
- `INSUFFICIENT BROAD CAPABILITY EVIDENCE`

The V1 operation supplies `confidence` and `outcome` to subject code and verifies the Brier-score calculation primitive. It is not prediction capability, reasoning capability, calibration judgment, or evidence of model calibration improvement.

## V2 Adapter Freeze

The V2 adapter bundle is frozen before validation and hidden execution.

- Adapter freeze SHA: `111a97a41deefc92c05782897c11bafef3064922`
- Adapter freeze tree hash: `60049a3fd0a3656b04a9f1f9951ae62ac6718404`
- Freeze manifest: `docs/audit/current/SUBJECT_ADAPTER_V2_FREEZE_MANIFEST.json`

The campaign verifier requires the freeze SHA to be present, to resolve, and to be an ancestor of the campaign execution SHA.

## Evidence Binding

V2 campaign manifests record:

- campaign execution SHA
- workflow head SHA
- adapter freeze SHA and tree hash
- adapter bundle hash
- compatibility matrix hash
- benchmark registry hash
- evaluator version and code hash
- subject SHAs and tree hashes
- environment hash
- locked dependency hashes
- planned, completed, failed, timeout, and unsupported totals
- common-core coverage
- threshold result
- decision reference
- internal payload manifest hash

`scripts/verify_campaign_evidence_binding.py` fails when totals do not reconcile, raw results are missing, subject or evaluator hashes drift, adapter freeze binding is absent, or the workflow head differs from the campaign execution SHA.

## Digest Terminology

Batch 07D distinguishes:

- GitHub artifact archive digest: digest reported by GitHub Actions artifact metadata when available.
- Internal payload manifest hash: canonical SHA-256 over extracted campaign result files.
- Individual file hashes: hashes of specific files inside an evidence payload.
- Aggregate evidence-chain hash: hash linking aggregate history records.

An internal payload hash must not be reported as a GitHub artifact archive digest.

## Interface Intersection

The three-version interface audit found five candidate interfaces:

- `durable-calibration-task`: common `runtime_primitive`
- `durable-record-observation-task`: common `storage_write` primitive associated with evidence-shaped input, not `evidence_evaluation` benchmark support
- LLM review/decision path: rejected, live provider required
- backend route task path: rejected, no semantically equivalent bootstrap/auth contract across A/B/C
- civilization runtime path: rejected, absent from Version A

Common capability-task domains: `0`

Common primitive/control/storage domains: `2`

## Local V2 Campaign Result

Campaign: `subject-native-cross-version-v2`

- planned executions: `360`
- completed executions: `60`
- failed executions: `0`
- timeout executions: `0`
- unsupported executions: `300`
- completed runtime primitive executions: `30`
- completed storage-write executions: `30`
- completed capability-task executions: `0`

The local V2 campaign completed the available common primitive and storage paths, but it did not satisfy broad capability thresholds.

## Threshold Result

The predefined thresholds remain unmet:

- required common benchmark capability domains: `8 of 12`; observed `0`
- required validation/hidden common benchmark capability cases: `18 of 24`; observed `0`
- required common capability-task domains: `4`; observed `0`
- required common-core completion: unmet for broad capability evidence

Decision: `HOLD_FOR_MORE_EVIDENCE`

External approval: `PENDING_EXTERNAL_REVIEW`

## Controls Added

- capability versus primitive classification
- answer-ownership verifier
- campaign evidence-binding verifier
- V2 interface intersection ledger
- V2 adapter development report
- V2 freeze manifest
- V2 campaign result and decision reports
- artifact digest terminology separation

## Limitations

- No broad cross-version capability improvement is demonstrated.
- No common reasoning, planning, software-engineering, data-analysis, governance, budget, memory, or recovery capability-task interface was found across A, B and C.
- Hosted staging remains `BLOCKED`.
- Scheduled observation count remains limited to genuine schedule events.
- PR #27 must remain draft and unmerged unless future evidence satisfies the broad thresholds.
