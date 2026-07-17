# Protocol V3 Reproof

## Subject

PR #28 tip:
`89af203e24b6a9e4f5c1636cf5d5bd0c5513ba81`.

Campaign:
`governed-capability-protocol-baseline-v3`.

## Clean-Clone Commands

```bash
git clone /Users/Zet/Agentco /private/tmp/agentco-08e-clean-89af203
cd /private/tmp/agentco-08e-clean-89af203
git checkout 89af203e24b6a9e4f5c1636cf5d5bd0c5513ba81
python3.13 -m pip install -r requirements/requirements.lock.txt
python3.13 scripts/verify_capability_genesis_freeze.py --check
make capability-protocol-baseline-v3
python3.13 scripts/verify_capability_genesis_artifact.py --check
```

Dependency installation used the repository lockfile. It installed into the
shared Python environment rather than a separate virtualenv; this is recorded as
an environment limitation, not as evidence failure.

## Results

| Check | Result |
| --- | --- |
| Freeze verifier | passed |
| Protocol cases executed | 24/24 |
| Assertions executed | 94 |
| Assertions passed | 94 |
| Assertions failed | 0 |
| Assertions skipped | 0 |
| Invalid request rejection | passed |
| Completed/denied/failed/timed-out response schemas | passed |
| Corrupted persistence rejection | passed |
| Timeout settlement | passed, terminal with zero unreleased reservation |
| Retryable/non-retryable paths | passed |
| Audit-reference resolution | passed |
| Selected-provider failure no fallback | passed |
| Recursive secret-canary scan | passed, zero occurrences |
| Artifact verifier | passed |

Clean-clone Protocol V3 internal payload hash:
`1cabb829dead0ec1f4bfff204944535db5afcde50740a77c8fa0792fea7e1a4b`.

Published workflow Protocol V3 internal payload hash:
`e6ccb9d408c60f6d93caea3c43594ddec5b43ee4fa07d054b382df8a867ce856`.

The hashes are not expected to match across independently generated artifacts
because the payload includes generated artifact content. The audited binding
fields, campaign SHA, control totals, acceptance predicate and decision matched.

Decision: `PROTOCOL_BASELINE_ACCEPTED`.
