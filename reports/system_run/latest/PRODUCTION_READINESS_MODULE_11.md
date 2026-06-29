# Production Readiness Module 11: Real Civilization Service Routing

Date: 2026-06-26

## Verdict

Completed for the civilization routing slice.

This module removes simulated primary solving and randomized validation from `CivilizationService`. Civilization reasoning now calls the actual symbolic, ensemble, and RAG services, and validation is derived from those service outputs.

## Changes

- Primary solver execution now dispatches to real service adapters:
  - `symbolicService.solve()`
  - `ensembleService.ensembleVote()`
  - `ragService.augmentAnswer()`
- Broadcast validation now calls non-primary services and compares their answers/confidence to the primary result.
- Removed randomized agreement and confidence deltas.
- Validation failures are explicit structured concerns.
- Knowledge entries now use UUIDs instead of timestamp/random IDs.

## Verification

Commands run:

```bash
cd backend && npx tsc --noEmit
cd backend && npm test -- tests/civilization-real-routing.test.ts --runInBand --forceExit
```

Results:

- TypeScript compile: passed.
- Civilization routing tests: 1 passed.

## Remaining Scope

This module wires civilization routing to real service adapters. It does not make every adapter high-confidence for every domain; weak or missing upstream services now surface as validation concerns.
