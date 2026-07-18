# Batch 09C OpenAI Real Baseline Report

## Current Decision

| Field | Value |
| --- | --- |
| campaign | `governed-capability-genesis-v7-openai-real-baseline-attempt-2` |
| decision | `HOLD_FOR_MORE_EVIDENCE` |
| provider | `OpenAI` |
| requested model | `gpt-5.6-luna` |
| returned model identity | `gpt-5.6-luna` |
| endpoint hostname | `api.openai.com` |
| provider fallback | `not used` |
| model fallback | `not used` |
| capability improvement | `NOT_CLAIMED` |

## Attempt 2

Attempt 2 corrected the OpenAI request contract to use `max_completion_tokens`. The authorized canary completed against `gpt-5.6-luna`, captured a provider request ID, established returned model identity, captured usage, and reconciled the canary reservation.

The 24 frozen validation/hidden cases then executed sequentially with concurrency `1`. All 24 provider calls returned terminal evidence, but every baseline response failed the structured JSON-output parser under the frozen evaluator contract. No case was scored as completed capability evidence, no domain met support thresholds, and aggregate correctness remains unavailable.

## Attempt 2 Counts

| Metric | Value |
| --- | --- |
| planned cases | `24` |
| executed cases | `24` |
| completed cases | `0` |
| failed cases | `0` |
| timed-out cases | `0` |
| denied cases | `0` |
| evidence-unavailable cases | `0` |
| evaluator-unavailable cases | `0` |
| invalid-response cases | `24` |
| infrastructure-failure cases | `0` |
| supported domains | `[]` |
| aggregate correctness | `None` |
| total input tokens | `5234` |
| total cached-input tokens | `0` |
| total output/reasoning tokens | `6174` |
| total campaign cost, local ledger | `$0.21139` |
| remaining authorized budget | `$2.78861` |
| semantic hash | `bf0fe05dbb4744ff726acd151dfecd34a67eac5d458c05c67db7d6a3029b7974` |

## Prior Attempt 1

The original Batch 09C canary record is preserved under `docs/capability/batch_09c_evidence/` and `docs/audit/current/REAL_PROVIDER_GENESIS_V7_HOLD.json`. It reported `HOLD_FOR_MORE_EVIDENCE` because the initial request contract used an unsupported token parameter and the 24-case baseline was not started.

## Non-Claims

No real capability baseline is established. No supported domains, aggregate correctness, capability improvement, hosted staging readiness or production readiness are claimed. Attempt 2 is evidence of provider reachability and a failed structured-output campaign, not evidence of benchmark capability.

## Evidence

Attempt 2 redacted durable evidence is stored under `docs/capability/batch_09c_evidence/attempt_2_real_execution`. The local artifact copy is stored under `artifacts/capability-runtime/governed-capability-genesis-v7-openai-real-baseline-attempt-2`. Credentials and authorization headers were not persisted.
