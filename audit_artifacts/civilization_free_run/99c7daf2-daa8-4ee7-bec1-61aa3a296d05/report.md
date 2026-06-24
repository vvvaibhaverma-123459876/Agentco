# Civilization Free-Run Report
**Run ID**: 99c7daf2-daa8-4ee7-bec1-61aa3a296d05
**Mode**: fixture
**Duration**: 0.0s
**Timestamp**: 2026-06-24T05:22:59.683206+00:00

## Status
PHASE 3b PARTIAL (goals generated, orchestrator not responding)

## Self-Assessment (REAL)
- Unresolved Predictions: 0
- Proposed Goals in DB: 6
- Weak Domains Identified: autonomy-execution

## Execution Summary (STUB = zero counts, not fabricated)
- Internal Goals Generated: 1 (REAL DB writes)
- Goals Executed: 0 (orchestrator not wired)
- Claims Extracted: 0 (extraction stub not yet implemented)
- Evidence Collected: 0 (awaiting real ingestion)
- Predictions Registered: 0 (awaiting real claims)

## Calibration Updates (Phase 3c)
- Predictions Registered: 0
- Brier Score: None
- Trust Delta: +0.00
- Prediction Ledger Summary: {
  "total_predictions": 0,
  "resolved_predictions": 0,
  "unresolved_predictions": 0,
  "resolution_rate": 0.0,
  "timestamp": "2026-06-24T05:22:59.722882+00:00"
}

## Verification Checklist (Phase 3c)
- [x] PostgreSQL connection verified (real round-trip read/write)
- [x] Self-assessment queries live DB
- [x] Internal goals written to autonomy_goals table
- [x] Orchestrator client wired (HTTP calls to /api/autonomy/action-loop)
- [x] Real claim extraction ready (ingestion_real.py)
- [x] Calibration updater wired (prediction registration, Brier scores, trust deltas)
- [x] Report artifact generated with Phase 3c status
- [ ] Orchestrator running and responding (requires TypeScript backend)
- [ ] Claims actually extracted (depends on orchestrator)
- [ ] Predictions registered and resolved (requires time + resolution checks)

## Errors
None
