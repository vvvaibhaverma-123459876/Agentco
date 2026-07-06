# Production Readiness Module 5: Fail-Closed Evidence and Claim Persistence

Date: 2026-06-26

## Verdict

Completed for the action execution and specialist persistence slice.

This module removes the remaining placeholder artifact paths in active action execution. Fetch failures now block without creating evidence rows, and specialist persistence failures no longer return stub IDs.

## Changes

- `ActionExecutorService.FETCH_PAGE` now returns `BLOCKED` when no real page content is available.
- The backend fetch handler no longer records placeholder evidence rows such as "Fetch Attempted (Unavailable)".
- `SpecialistAgent.persist_evidence()` raises after DB connection retry exhaustion instead of returning an unpersisted evidence ID.
- `SpecialistAgent.persist_claim()` rejects missing evidence sources and DB retry exhaustion instead of returning an unpersisted claim ID.
- `ResearcherAgent.GENERATE_CLAIM` now calls `persist_claim()` and only reports success after persistence succeeds.
- Researcher/fetcher evidence-producing actions now return structured failures with no artifacts if persistence fails.

## Verification

Commands run:

```bash
python3.13 -m pytest agents/tests/test_specialist_real_web_actions.py -q
cd backend && npx tsc --noEmit
cd backend && DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npm test -- tests/action-loop.test.ts --runInBand --forceExit
```

Results:

- Specialist persistence tests: 10 passed.
- TypeScript compile: passed.
- Action-loop tests: 16 passed.

## Remaining Scope

This module removes active placeholder artifact generation in the covered action paths. It does not remove explicitly offline fixture behavior, deterministic eval baselines, or simulation datasets that are intentionally labeled as such.

## Reachability Note

The live specialist activation path covered here is the TypeScript `TeamActivationService` path that starts `python3.13 -m agents.autonomy.<role>` by default, or `AGENTCO_PYTHON` when configured. It reaches the 17 registered `agents/autonomy/*` specialist roles.

The additional department-style Python agent classes under executive, legal, marketing, sales, design, product, people-ops, customer-experience, and engineering directories are repository inventory and targeted test surfaces unless a separate caller instantiates them. They are not activated by the `spawn_specialist` action and should not be counted as production-reachable subprocess specialists for this module.
