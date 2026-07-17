# Batch 08D Corrected Evidence Record

Audited PR #28 SHA:
`89af203e24b6a9e4f5c1636cf5d5bd0c5513ba81`.

## Freeze Binding

| Field | Value |
| --- | --- |
| Freeze candidate commit | `f88bb23965637dee60e7d1ab6d89b83cc33a97ee` |
| Freeze candidate tree | `7486641b0fe36fae86659415f495eba570959007` |
| Freeze manifest commit | `59e78cb7262dba453a1639ab564969e3e5b3591b` |
| Freeze manifest blob | `df612fcc1f85fd280679e7c65ee8e1cfb37e762d` |
| Freeze manifest SHA-256 | `cebb4802febbf7263caeb20395e1906e206b0948825c33577b083664ef91cbde` |
| Freeze binding commit | `ae52de68300f2154397dd63645d0aa5121ec9b88` |
| Complete binding logical hash | `3fc8e6f3eaa2a6724e732215483cbdcf0127f812c1470e536af9e980987245b7` |
| Final branch tip | `89af203e24b6a9e4f5c1636cf5d5bd0c5513ba81` |

The binding logical hash was independently reconstructed with
`agentco_capability.evidence.canonical_json` after excluding only the
`freeze_binding_logical_hash` field. A naive compact JSON hash produces a
different value and is not the repository's canonical freeze hash.

## Ancestry

`git merge-base --is-ancestor` passed for:

- candidate -> final tip
- manifest -> final tip
- binding -> final tip

## Registered Frozen Files

The V5 freeze manifest records 56 frozen files. Candidate/final comparison
passed through `scripts/verify_capability_genesis_freeze.py --check`; no
registered frozen file changed after the candidate, and no unregistered semantic
file was added under frozen directories.

Permitted post-candidate changes:

- `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_MANIFEST.json`
- `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_BINDING.json`
- forensic inventory/control ledgers
- score-validation reports

## Artifact Binding

Protocol V3 workflow artifact:

- run: `29572538767`
- artifact: `8403691594`
- GitHub archive digest:
  `sha256:3fd3a88b198623ef570be6cd174b26776c15d03cc8d21acb415e36ec2486621d`
- internal payload manifest hash:
  `e6ccb9d408c60f6d93caea3c43594ddec5b43ee4fa07d054b382df8a867ce856`

Genesis V5 workflow artifact:

- run: `29572538694`
- artifact: `8403716532`
- GitHub archive digest:
  `sha256:09c13f5466930b9c276b83c71e8402268a2d15f5f580d734607f5dd694e3103b`
- internal payload manifest hash:
  `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`
