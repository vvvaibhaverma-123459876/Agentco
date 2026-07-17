# Remediation 07E: Final Evidence-Semantic Closure

## Scope

Batch 07E corrects the remaining semantic overstatement in the subject-native
cross-version V2 evidence. Immutable subjects A, B and C remain unchanged.

## Semantic Corrections

The `record_observation` durable task is no longer classified as support for
the `evidence_evaluation` benchmark domain.

It is now recorded as:

- `operation_classification`: `storage_write`
- `operation_name`: `durable_observation_recording`

This operation stores and returns a supplied observation payload. It does not
evaluate conflicting evidence, determine truth, accept or reject evidence,
produce a conclusion, or generate confidence.

## Operation-Specific Scoring

The generic completed-case correctness aggregate was removed for V2 closure.

Scoring is operation-specific:

- calibration calculation reports Brier-score formula parity and numerical
  availability.
- durable observation recording reports write acknowledgement, request-hash
  preservation, payload integrity, and recorded output hash.
- storage-write records have `correctness`, `brier_score`, and
  `capability_score` set to `null`.

Primitive scores are not averaged into a capability score.

## Resource Measurement

Per-execution resource measurement now samples the actual child subject process
with `psutil`.

Canonical RSS is stored in bytes, with kilobytes derived explicitly. CPU user,
system and total times are recorded separately. The measurement method,
platform, sampling interval and availability are included in each process
record.

## Payload Evidence

Every closure campaign artifact includes `INTERNAL_PAYLOAD_MANIFEST.json`.

The internal payload hash is computed from repository-relative extracted paths,
file sizes and SHA-256 hashes. The manifest excludes `CONTROL_MANIFEST.json`
and itself from recursive hashing.

Terminology is separated:

- GitHub artifact archive digest: provided by GitHub artifact metadata.
- Internal payload manifest hash: reproducible from extracted artifact
  contents.
- Individual file hashes: recorded per included payload file.

## Closure Campaign

Campaign: `subject-native-cross-version-v2-closure`

Local execution result:

- planned executions: `360`
- completed executions: `60`
- failed executions: `0`
- timeout executions: `0`
- unsupported executions: `300`
- calibration primitive executions: `30`
- storage-write primitive executions: `30`
- capability-task executions: `0`
- common benchmark capability domains: `0`
- common capability-task domains: `0`
- primitive compatibility operations: `2`

Internal payload manifest hash:

```text
c5327c2f2f7e5156d6951cf4a7f8b3c80030f9c2d05ea7199abf5001f21d96b1
```

## Governed Decision

Decision remains:

```text
HOLD_FOR_MORE_EVIDENCE
```

Audit PR readiness and candidate promotion readiness are separated:

```text
audit_pr_readiness = READY_FOR_HUMAN_REVIEW
candidate_promotion_readiness = BLOCKED_INSUFFICIENT_CAPABILITY_EVIDENCE
```

No promotion, deployment, automatic approval or merge is authorized by this
evidence.

## Remaining Limitations

- broad cross-version capability evidence remains unavailable.
- hosted staging remains `BLOCKED`.
- scheduled observation count remains based only on genuine scheduled events.
- Batch 08 is required to add a real governed capability runtime for future
  versions.
