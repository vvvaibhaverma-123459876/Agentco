> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# Production Readiness Module 3: Real Specialist Web Actions

Date: 2026-06-26

## Verdict

Completed for the specialist web-action slice.

This module removes fake search/fetch/extraction behavior from the autonomy specialist agents. Search and page fetch now use real HTTP providers and fail closed with structured errors when unavailable or unsafe. Extraction now reads persisted evidence text instead of returning synthetic key points.

## Changes

- `ResearcherAgent.WEB_SEARCH` now calls a real DuckDuckGo HTML search path and persists returned results as `autonomy_evidence`.
- `ResearcherAgent.FETCH_PAGE` and `FetcherAgent.FETCH_PAGE` now fetch real HTTP/HTTPS pages with SSRF validation before and after redirects.
- `ResearcherAgent.EXTRACT_EVIDENCE` now loads persisted evidence text and extracts bounded sentence-level evidence from real stored content.
- `autonomy_evidence.content_text` stores bounded source text for later extraction.
- Specialist subprocess port selection now asks the OS for an available loopback port instead of choosing randomly from a narrow range.

## Fail-Closed Behavior

- Unsafe URLs are blocked and produce no artifacts.
- Search provider failure produces no fake search artifacts.
- Fetch failure produces no fake page artifacts.
- Missing or empty evidence text blocks extraction and produces no fake extracted evidence.
- Specialist HTTP port collisions are avoided by OS-assigned ports.

## Verification

Commands run:

```bash
python3.13 -m pytest agents/tests/test_specialist_real_web_actions.py agents/tests/test_specialist_server_runtime.py -q
cd backend && npx tsc --noEmit
cd backend && DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npm test -- tests/team-activation.test.ts --runInBand --forceExit
```

Results:

- Python specialist tests: 9 passed.
- Backend TypeScript compile: passed.
- Team activation tests: 13 passed.

## Remaining Scope

This module makes specialist web actions real and fail-closed. It does not claim that every other AgentCo subsystem is production-ready. Production mode still requires non-development secrets and production-grade deployment configuration, which must not be generated or committed by this repository.
