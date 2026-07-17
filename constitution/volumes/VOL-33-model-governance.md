# Volume 33 — Model Governance

## 1. Header

| Field | Value |
|---|---|
| Volume | 33 |
| Name | Model Governance |
| Tier | statute |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V7 (Civilization Economy), V11 (Trust & Calibration), V32 (Security & Threat Model), V24 (Interaction Intelligence), V30 (Verification) |

## 2. Purpose

Model Governance is how AgentCo depends on external language models *without* letting any
one model become an unaccountable dependency. It defines the single governed call site,
the rule that model calls reserve token budget against the economy before running, and the
per-tier resolution that lets a model be swapped by configuration rather than code change.
Because the models themselves are not built here, this volume is where "which model,
under what budget, with what fallback" is made explicit. Mixed status; every present-tense
claim cites its file.

```text
CALLER (planner, ensemble, durable-execution, bounded-learning)
   │  callJson(request)                     ← single governed entry point
   ▼
LlmProviderService.callJson  (llm-provider.service.ts)
   │  model = request.model || LLM_MODEL_DEFAULT || built-in default
   │  maxTokens = clampMaxTokens(...)        (LLM_MAX_OUTPUT_TOKENS cap)
   ├─ reserveBudget → resourceLedger.reserve (V7)   token spend reserved first
   │     production requires LLM_RESOURCE_ACTOR_ID / _ACCOUNT_ID or fails closed
   ├─ retry bounded (LLM_MAX_RETRIES); only retryable errors retried
   ▼
PROVIDER (OpenAI-compatible or native-adapter)   provider_config.py per-tier
   │  LLM_MODEL_<T> → LLM_MODEL_DEFAULT → provider tier default
   ▼
RESULT (model echoed back)   feeds calibration (V11) and interaction (V24)
```

## 3. Definitions

- **Governed call site** — `LlmProviderService.callJson`, the single service method
  through which model calls flow (`backend/src/services/llm-provider.service.ts`).
- **Tier** — an abstraction mapping an agent role to a (provider, model) selection
  (`runtime/base_agent/provider_config.py`, with the tier map in `model_tiers.py`).
- **Model resolution** — the precedence `request.model → LLM_MODEL_DEFAULT → built-in
  default` (TS) and `LLM_MODEL_<T> → LLM_MODEL_DEFAULT → provider tier default` (Python).
- **Token reservation** — the pre-call reservation of estimated tokens against the
  resource ledger (`reserveBudget`, `estimateTokenReservation`; V7).
- **Clamp** — the hard cap on output tokens (`clampMaxTokens`, `LLM_MAX_OUTPUT_TOKENS`).
- **Retryable error** — a provider error classified as safe to retry, bounded by
  `LLM_MAX_RETRIES` (`LlmProviderError`, `retryableStatus`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V33-INV-001 | Model calls flow through a single governed provider service rather than ad-hoc SDK calls scattered across the codebase. | enforced | `backend/src/services/llm-provider.service.ts`, `backend/tests/llm-provider.test.ts` |
| V33-INV-002 | A production model call reserves token budget against the resource ledger and fails closed when the budget actor/account is not configured. | enforced | `backend/src/services/llm-provider.service.ts`, `backend/tests/llm-provider.test.ts` |
| V33-INV-003 | Output tokens are clamped to a configured maximum on every call. | enforced | `backend/src/services/llm-provider.service.ts`, `backend/tests/llm-provider.test.ts` |
| V33-INV-004 | Provider errors are retried only when classified retryable, up to a bounded retry count; cancellation is honored. | enforced | `backend/src/services/llm-provider.service.ts`, `backend/tests/llm-provider.test.ts` |
| V33-INV-005 | The model is selected by configuration precedence (request → default → tier default), so swapping a model requires no code change. | enforced | `backend/src/services/llm-provider.service.ts`, `runtime/base_agent/provider_config.py` |
| V33-INV-006 | A tier model clearly incompatible with the selected provider is rejected or overridden rather than sent blindly. | enforced | `runtime/base_agent/provider_config.py` |
| V33-INV-007 | The model that produced a result is recorded on the result, so outputs are attributable to a specific model. | enforced | `backend/src/services/llm-provider.service.ts`, `backend/tests/llm-provider.test.ts` |
| V33-INV-008 | Replacing or upgrading the default model is a governed change with a recorded rationale, not a silent environment edit. | planned | — |
| V33-INV-009 | Per-model calibration is tracked so trust (V11) is scoped by model, and a model whose calibration degrades is flagged. | planned | — |

## 5. Interfaces

- **Provider** — `llm-provider.service.ts` `callJson(request)` returning
  `{ ..., model }`; `reserveBudget` (V7 seam).
- **Tier configuration** — `runtime/base_agent/provider_config.py` resolves
  `(provider, base_url, api_key, model)` per tier; `model_tiers.py` holds the tier map.
- **Callers** — `autonomy-action-planner.service.ts`, `ensemble.service.ts`,
  `multi-agent-ensemble.service.ts`, `durable-execution.service.ts`,
  `bounded-learning-run.service.ts`.
- **Budget** — `resource-ledger.service.ts` (`reserve`), the V7 economy.
- **Secrets** — provider keys are startup-guarded (V32): `LLM_API_KEY` / `OPENAI_API_KEY`.

## 6. State

- **Configuration (environment):** `LLM_MODEL_DEFAULT`, `LLM_MODEL_<TIER>`,
  `LLM_MAX_OUTPUT_TOKENS`, `LLM_MAX_RETRIES`, `LLM_BASE_URL`, `LLM_API_KEY` /
  `OPENAI_API_KEY`, `LLM_RESOURCE_ACTOR_ID`, `LLM_RESOURCE_ACCOUNT_ID`.
- **Token accounting:** reservations in the resource ledger (V7, migrations `081`/`082`).
- **Calibration by subject:** `trust_scores` keyed by subject/domain/claim-type/horizon
  (V11) — not yet keyed by model (open question 2).

## 7. Failure modes and responses

- **Scattered SDK calls** — a single `callJson` entry point concentrates model access, so
  budget, clamp, and retry rules cannot be bypassed by a rogue call site (V33-INV-001);
  the five known callers all route through it.
- **Unbudgeted spend** — production calls fail closed without a configured budget actor
  and account (`reserveBudget` throws `budget_unavailable`, V33-INV-002).
- **Runaway output** — output tokens are clamped (V33-INV-003).
- **Provider flakiness** — only retryable errors retry, bounded, with cancellation
  honored (V33-INV-004).
- **Model/provider mismatch** — an incompatible leaked tier model is overridden rather
  than sent (`provider_config.py`, V33-INV-006).
- **Silent model swap** — changing the default model is currently an environment edit,
  not a governed change (V33-INV-008 planned; open question 1) — the highest-value gap,
  since a model change alters behaviour system-wide.
- **Model-blind trust** — trust is not yet keyed per model (V33-INV-009 planned), so a
  model regression is not isolated in calibration.

## 8. Verification obligations

Existing and green today: `backend/tests/llm-provider.test.ts` (single entry point,
budget reservation + fail-closed, token clamp, bounded retry + cancellation, model echo).

Must exist before the planned invariants flip: a governed model-change path with a
recorded rationale and a test (V33-INV-008), and per-model calibration keying with a
degradation flag (V33-INV-009).

## 9. Implementation mapping

- `backend/src/services/llm-provider.service.ts` — the governed call site: model
  resolution, token clamp, budget reservation, bounded retry, model attribution.
- `runtime/base_agent/provider_config.py` — per-tier provider/model resolution and
  incompatibility override; `model_tiers.py` — tier map.
- `backend/src/services/resource-ledger.service.ts` — token budget reservation (V7).
- Callers: planner, ensembles, durable execution, bounded learning.

## 10. Open questions

1. **Model changes are not governed.** Swapping `LLM_MODEL_DEFAULT` changes behaviour
   across the whole system but is a plain environment edit; it should be a governed
   change (V12) with a recorded rationale and, ideally, a canary (V14) — the highest-value
   gap in this volume (V33-INV-008 planned).
2. **Trust is model-blind.** `trust_scores` (V11) is keyed by subject/domain/claim-type/
   horizon but not by model, so a model upgrade that degrades calibration is not isolated
   (V33-INV-009 planned).
3. **Two resolution paths.** TypeScript (`llm-provider.service.ts`) and Python
   (`provider_config.py`) resolve models with similar-but-separate precedence; a single
   declared resolution contract would prevent divergence (a Volume 2 canonical-runtime
   concern).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 13) | Give the single external-model dependency constitutional status: one governed call site, budgeted and clamped, model-swappable by configuration — and name the missing governed-model-change and per-model-calibration gates. |
