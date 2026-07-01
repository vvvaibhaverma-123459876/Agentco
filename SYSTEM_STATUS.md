# AgentCo System Status

**Date:** 2026-06-29  
**Status:** local production-posture runnable; hosted production certification incomplete.

This file replaces older phase-status claims. For exact item-level truth, read `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

## Current Summary

| Metric | Value |
|---|---|
| Build ledger | `67/67 verified (100%)`; termination predicate true |
| Backend default tier | `42` suites passed, `287` tests passed |
| Current verified E2E | Grounded learning civilization slice plus civilization vertical slice |
| Release gates | No-stub, no-simulation, firewall, sandbox, credential key-independence, and reachability green |
| Production readiness | Local production posture passes; hosted production operations not certified |
| Mission progress | Evidence-governed calibration civilization verified; long-horizon generality, repeated real-world improvement, broad open-domain transfer, and hosted operations remain partial or unproven |

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

- Hosted production SLOs, disaster recovery, backups, monitoring response, incident response, and long-running operations evidence are not proven.
- Progressively more general intelligence over long time horizons is not proven.
- Durable autonomous improvement from repeated real-world operation is not proven.
- Broad open-domain transfer remains partial bounded-verifier evidence, not proof of general intelligence.
- Production source discovery and external-service behavior still depend on live infrastructure and configured providers.
- Some historical docs still describe older aspirations or phase results; current truth is the ledger and latest verification reports.

## Current Verification Commands

```bash
python3.13 scripts/build_ledger.py status
make mission-progress

set -a
source .codex.env
set +a
export DATABASE_URL="$AGENTCO_TEST_DATABASE_URL"

cd backend
npm run db:migrate
npx tsc --noEmit
npm test -- --runInBand --forceExit
```
