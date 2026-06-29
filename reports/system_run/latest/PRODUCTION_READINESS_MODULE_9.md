# Production Readiness Module 9: Real LLM Ensemble Adapter

Date: 2026-06-26

## Verdict

Completed for the core ensemble voting slice.

This module removes deterministic canned model answers from `EnsembleService`. Ensemble personas now call the configured OpenAI-compatible chat completions endpoint and return structured answer/confidence/reasoning JSON. Missing LLM credentials fail closed instead of producing synthetic model votes.

## Changes

- `EnsembleService.queryModels()` now calls three LLM-backed personas:
  - `general_reasoning`
  - `specialized_reasoning`
  - `knowledge_grounded`
- Uses `LLM_API_KEY` or `OPENAI_API_KEY`.
- Uses `LLM_BASE_URL` with default `https://api.openai.com/v1`.
- Uses `LLM_MODEL_DEFAULT` with default `gpt-4o-mini`.
- Requires structured JSON with `answer`, `confidence`, and `reasoning`.
- Missing credentials, HTTP failures, empty content, and invalid JSON all fail closed.

## Verification

Commands run:

```bash
cd backend && npx tsc --noEmit
cd backend && npm test -- tests/ensemble-live-adapter.test.ts --runInBand --forceExit
```

Results:

- TypeScript compile: passed.
- Ensemble adapter tests: 2 passed.

## Remaining Scope

This module makes the ensemble real but dependent on LLM availability and cost. Offline fixture modes must continue using explicitly marked fixture paths outside this production service.
