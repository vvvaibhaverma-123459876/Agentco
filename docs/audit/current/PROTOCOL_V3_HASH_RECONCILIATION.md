# Protocol V3 Hash Reconciliation

## Prior Mismatch

Batch 08E recorded two different internal payload hashes for Protocol V3:

- clean-clone internal payload hash: `1cabb829dead0ec1f4bfff204944535db5afcde50740a77c8fa0792fea7e1a4b`
- published workflow internal payload hash: `e6ccb9d408c60f6d93caea3c43594ddec5b43ee4fa07d054b382df8a867ce856`

Those hashes represented complete execution artifacts. Complete artifacts include
execution-specific metadata such as run identity, timestamps, host paths,
temporary stores and artifact-local manifests. They are not stable semantic
result identifiers.

## Hash Semantics

- Full artifact hash: covers the complete extracted artifact payload and may
  vary when execution metadata changes.
- Semantic protocol hash: covers only acceptance-relevant protocol fields.
- Frozen source/evidence binding: covered by the freeze candidate, manifest and
  binding commit hashes.

## Batch 08F Semantic Hash

Batch 08F added deterministic semantic hashing for Protocol V3. The semantic
hash includes:

- campaign identity
- protocol version
- case population
- assertion population
- schema verdicts
- retry verdicts
- timeout settlement verdict
- persistence and corruption-rejection verdicts
- audit-reference verdict
- no-fallback verdict
- acceptance-predicate fields
- final decision
- frozen candidate and tree binding

It excludes only volatile execution fields:

- timestamps
- workflow run IDs
- temporary paths
- host-specific metadata

## Restacked Local Result

- campaign: `governed-capability-protocol-baseline-v3`
- decision: `PROTOCOL_BASELINE_ACCEPTED`
- cases: `24/24`
- assertions: `94/94 passed`
- freeze candidate: `dfd36daf97133fec52dcd664c5dd8dca2d3bef00`
- freeze candidate tree: `6a7d108d836557fe49c77511ca771710341e35c4`
- freeze binding commit: `af06c343f2f614eb6b0355d5b7a02a2f93837d02`
- full internal payload hash: `fd370f790b62c92fa079b44a9c66c48d9b0567cbf093a97d944459bc56f4670a`
- semantic protocol hash: `3579d7dc989762f405c9afd86e0369ddef88551b17ec2f310d9be629f94de6ce`

## Classification

Known full-payload differences are classified as expected execution metadata,
timestamp or run-identity variance, path variance, and artifact-local metadata.
No substantive protocol-result difference was found in the restacked local
result.

Remote semantic equality must be checked against the final post-push workflow
artifact. Protocol acceptance remains valid only when the workflow artifact
reports the same semantic protocol hash for the same freeze binding.
