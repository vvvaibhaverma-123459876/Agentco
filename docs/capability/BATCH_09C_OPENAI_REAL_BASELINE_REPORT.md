# Batch 09C OpenAI Real Baseline Report

## Decision

| Field | Value |
| --- | --- |
| campaign | `governed-capability-genesis-v7-openai-real-baseline` |
| decision | `HOLD_FOR_MORE_EVIDENCE` |
| reason | `AUTHORIZED_MODEL_UNAVAILABLE` |
| canary_execution_attempted | `true` |
| baseline_execution_attempted | `false` |
| provider | `OpenAI` |
| requested model | `gpt-5.6-luna` |
| endpoint hostname | `api.openai.com` |
| provider fallback | `not used` |
| model fallback | `not used` |

## Canary

The one-request canary was authorized and attempted against `https://api.openai.com/v1` with exact model `gpt-5.6-luna`. It failed with sanitized category `model_or_request_unavailable` and HTTP status `400`. No provider response text, error body, credential value or authorization header was persisted.

Because fallback is prohibited, the 24-case Genesis baseline was not started.

## Counts

| Metric | Value |
| --- | --- |
| planned cases | `24` |
| executed cases | `0` |
| completed cases | `0` |
| failed cases | `0` |
| timed-out cases | `0` |
| denied cases | `0` |
| evidence-unavailable cases | `24` |
| evaluator-unavailable cases | `0` |
| invalid-response cases | `0` |
| infrastructure-failure cases | `0` |
| supported domains | `[]` |
| aggregate correctness | unavailable |

## Non-Claims

No real capability baseline is established. No supported domains, aggregate correctness, capability improvement, hosted staging readiness or production readiness are claimed.

## Evidence

Redacted durable evidence is stored under `docs/capability/batch_09c_evidence`. A local ignored copy also exists under `artifacts/capability-runtime/governed-capability-genesis-v7-openai-real-baseline`. The canary evidence SHA-256 is `bd2a9f7f5c0fbb226846e9ba90c8101708c6159b12a8951b044e46ebdf67b8e5`.
