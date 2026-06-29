# AgentCo System Status

**Date:** 2026-06-29  
**Status:** local-native runnable; production certification incomplete.

This file replaces older phase-status claims. For exact item-level truth, read `BUILD_LEDGER.yaml`.

## Current Summary

| Metric | Value |
|---|---|
| Build ledger | `18/67 verified (26.87%)` |
| Backend default tier | `42` suites passed, `287` tests passed |
| Current verified E2E | Grounded learning civilization slice |
| Production readiness | Not certified |

## Verified Runtime Path

The current strongest path is:

```text
native Postgres
-> canonical evidence registry
-> grounded supported claim
-> prediction_ledger registration
-> resolution_service-only resolution
-> Brier/log score
-> persistent trust score
-> prediction_lesson memory
-> event_log + decision_log audit
```

## Remaining Blockers

- Full architecture ledger not complete.
- Production Vault/secrets posture not verified.
- Full Kafka/Redis/Vault/observability production smoke not rerun.
- Source-independence scoring still in progress.
- Cross-domain transfer remains smoke/skeleton.
- Some historical docs still describe older aspirations or phase results; current truth is the ledger and latest verification reports.

## Current Verification Commands

```bash
python3.13 scripts/build_ledger.py status

set -a
source .codex.env
set +a
export DATABASE_URL="$AGENTCO_TEST_DATABASE_URL"

cd backend
npm run db:migrate
npx tsc --noEmit
npm test -- --runInBand --forceExit
```
