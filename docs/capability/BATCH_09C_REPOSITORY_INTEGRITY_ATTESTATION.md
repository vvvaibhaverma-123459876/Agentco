# Batch 09C Repository Integrity Attestation

| Field | Value |
| --- | --- |
| branch | `audit/remediation-09-openai-genesis-v7-baseline` |
| execution source commit | `9bfad8e79d494b84ab869f09032d1bdfa3e97c0d` |
| execution source tree | `c82e35a1379c77b8426271d66612ba6e7c886800` |
| campaign | `governed-capability-genesis-v7-openai-real-baseline-attempt-2` |
| credentials committed | `false` |
| provider fallback used | `false` |
| model fallback used | `false` |
| baseline cases started | `true` |
| baseline cases completed | `0` |
| invalid-response cases | `24` |
| hosted deployment attempted | `false` |
| production deployment attempted | `false` |
| secret scan | `passed` |

Attempt 2 executed the authorized OpenAI canary and all 24 frozen baseline cases from the recorded execution source commit. The baseline remains `HOLD_FOR_MORE_EVIDENCE` because no case produced schema-valid, scorable capability evidence. Repository evidence contains sanitized metadata and no provider credential values.
