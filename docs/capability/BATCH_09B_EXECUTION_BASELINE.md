# Batch 09B Execution Baseline

| Field | Value |
| --- | --- |
| branch | `audit/remediation-09-real-provider-genesis-baseline` |
| starting main SHA | `98eb1b9c04604e84770c7bdd286f9bbbfdbec663` |
| current branch SHA at precondition check | `98eb1b9c04604e84770c7bdd286f9bbbfdbec663` |
| source tree | `c56aa6daa67d78b222c7fd00f09faaa1d109698c` |
| PR #29 merge commit | `98eb1b9c04604e84770c7bdd286f9bbbfdbec663` |
| Protocol V3 campaign identity | `governed-capability-protocol-baseline-v3` |
| prior Genesis campaign identity | `governed-capability-genesis-v5` |
| intended Batch 09B campaign identity | `governed-capability-genesis-v6-real-baseline` |
| provider | `openai_compatible` configured by contract, not active in environment |
| exact model identifier | unavailable |
| API base URL hostname | unavailable |
| provider host allowlist | unavailable |
| case manifest semantic hash | `8f843e7cbca082d9e430fd8550ce5f84981d3df3ebee108c6779e44611a408c6` |
| frozen case manifest file SHA-256 | `39546df51028c55473e366ac2545dc555765ee3e398ec7d7e76b8df8bd5cb1d1` |
| evaluator protocol file SHA-256 | `2a60dc7e55d03d9e8a69800286fb00ac6ceda574e63004b981e2cb2ae75d93a4` |
| threshold file SHA-256 | `66c99fdd87b114584077d6815684bbd51221d82c45c907e5ca2b4772da43d4b6` |
| threshold semantic hash | `dd80a05fff8614ac2bbf1881de9d9a38c72bcf0e76bcc0cae3ba86a6e517c0df` |
| semantic hash specification SHA-256 | `7712812b188a39722c00b1758666a1a2452d5f651676b61ea88047f405c1e9c9` |
| authorization schema SHA-256 | `a2d924a91debe4756c33ba60ddc65108d7e17821c8c42c5e5a9806b3f7820e24` |
| authorization artifact hash | unavailable: no executable authorization artifact found |
| maximum calls | unavailable: no authorization artifact |
| maximum tokens | unavailable: no authorization artifact |
| maximum cost | unavailable: no authorization artifact |
| timeout | unavailable: no authorization artifact |
| retry limit | unavailable: no authorization artifact |
| concurrency | unavailable: no authorization artifact |
| evidence destination | unavailable: no authorization artifact |
| operator | unavailable: no authorization artifact |
| authorization expiry | unavailable: no authorization artifact |
| credential values recorded | `false` |

## Precondition Verdict

`decision: HOLD_FOR_MORE_EVIDENCE`

`execution_attempted: false`

Batch 09B provider execution was not attempted. The repository contains the real-provider readiness schema and operator contract, but it does not contain a machine-verifiable campaign authorization artifact bound to this exact source commit, source tree, provider, model, endpoint, case manifest and budget. The active process environment also does not expose `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL` or `AGENTCO_PROVIDER_HOST_ALLOWLIST`.

No provider credentials were read, printed, persisted or used.
