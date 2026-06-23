# Civilization Calibration & Trust Governance Implementation Plan

**Date:** 2026-06-23  
**Status:** 🚀 Ready to Begin  
**Database:** ✅ Working (33/33 migrations)  
**Civilization Structure:** ✅ In Place (entities, memberships, learning events, governance reviews)

---

## Overview

Implement a bounded trust governance layer where:
- **Civilization CAN propose** trust-policy changes
- **Civilization CANNOT directly** modify calibration, resolver, ground-truth, audit logs, RBAC, eval thresholds
- **All trust changes** are versioned, evaluated, signed, reviewed, canaried, auditable
- **No self-certification** - conflicting entities cannot approve own policy
- **No simulation-to-reality leakage** - simulation-derived claims blocked from real-world promotion
- **Reputation system** is event-sourced, immutable, never manually overwritten

---

## Implementation Strategy

### Phase A: Foundation (Steps 2-5)
Establish the core governance structures and validation mechanisms.

**Step 2: Calibration Constitution Service** (6-8 hours)
- Create `calibration_constitution` table with versioning, hashing, signing
- Service: `calibration-constitution.service.ts`
- Methods: createVersion, activateVersion, retireVersion, validateChange, getActive, verifyIntegrity
- All versions hashed (SHA256) and signed
- Only one active version at a time
- Acceptance: Constitution blocks prohibited changes, enforces protected surfaces

**Step 3: Trust Policy Versions Service** (8-10 hours)
- Create `trust_policy_versions` table with 9 policy types (confidence_discount, evidence_standard, etc.)
- Service: `trust-policy.service.ts`
- Methods: createDraft, validatePolicy, submitForReview, runEval, approve, activate, retire, rollback
- Status workflow: draft → under_review → eval_required → eval_failed/approved → canary → active → rolled_back → retired
- Promotion scope: agent/team/institution/society/civilization
- Parent policy tracking for lineage
- Acceptance: Policies are real artifacts, active policy controls calibration behavior

**Step 4: Calibration Change Requests Service** (8-10 hours)
- Create `calibration_change_requests` table
- Service: `calibration-change-governance.service.ts`
- Methods: createRequest, classifyRisk, checkConstitution, runProtectedSurfaceCheck, convertToPolicy, submitForReview, approve, reject, runImpactEval, createCanary, activate, rollback
- Allowed change types (12): adjust_confidence_discount, raise/lower_evidence_standard, adjust_reputation_weight, update_thresholds, update_dispute_rules, add_eval_case, retire_bad_policy, emergency_freeze
- Prohibited change types (7): modify_ground_truth, modify_resolver_logic, modify_calibration_score_code, edit_calibration_history, delete_audit_events, bypass_eval_gate, bypass_rbac
- Rules: Requester cannot approve own, institution cannot approve society-wide, requires quorum for civilization
- Acceptance: Prohibited changes are blocked, constitution violations blocked, missing rollback plan blocks activation

**Step 5: Trust Impact Assessment Service** (6-8 hours)
- Create `trust_impact_assessments` table
- Service: `trust-impact-assessment.service.ts`
- Methods: createAssessment, compareAgainstBaseline, runCalibrationRegressionEval, assessReputationImpact, assessDisputeImpact, assessSimulationLeakageRisk, produceRecommendation
- Recommendations: approve_for_canary, require_revision, block, require_human_review, sandbox_only
- Metrics: calibration_regression, confidence_shift, false_positive_impact, false_negative_impact, reputation_impact, dispute_impact, simulation_leakage_risk, safety_threshold_compliance, rollback_feasibility, audit_completeness
- Acceptance: Assessment persists real metrics, recommendation is computed (not hardcoded), failing assessment blocks canary

---

### Phase B: Governance & Accountability (Steps 6-8)
Add reputation tracking and failure handling.

**Step 6: Trust Reputation Ledger Service** (6-8 hours)
- Create `trust_reputation_ledger` table (event-sourced)
- Service: `trust-reputation.service.ts`
- Methods: recordEvent, computeReputation, applyToWeight, listEvents, createCorrectionEvent
- Entity types: agent, team, institution, society, civilization
- Events: accurate_prediction, failed_prediction, overconfident_claim, underconfident_correct, unsafe_action_blocked, dispute_resolution_quality, calibration_improvement/regression, rollback_triggered, protected_surface_violation, governance_review_quality
- Separate real vs. simulation reputation
- No manual overwrites; correction events are immutable
- Reputation used in trust policy weighting
- Acceptance: Reputation is event-sourced, immutable, updates via evidence

**Step 7: Calibration Drift Monitor Service** (4-6 hours)
- Create `calibration_drift_events` table
- Service: `calibration-drift-monitor.service.ts`
- Methods: detectDrift, recordEvent, proposeChange, resolveDrift, listEvents
- Drift types: overconfidence, underconfidence, resolution_delay, evidence_quality, reputation_drift, dispute_rate, simulation_leakage_risk, eval_failure_rate, rollback_rate
- Severe drift can propose trust-policy change (but not apply it)
- Critical drift can activate emergency freeze
- Acceptance: Drift detection uses persisted metrics/evals, proposes but doesn't apply changes

**Step 8: Trust Policy Canary & Rollback Service** (6-8 hours)
- Extend existing rollback logic to trust policies
- Service: `trust-policy-canary.service.ts`
- Methods: createCanary, startCanary, recordMetric, evaluateCanary, promote, rollback
- Canary starts small, respects scope limits
- Failed calibration metrics trigger automatic rollback
- Rollback restores previous active policy
- Acceptance: Canary changes policy only for approved scope, failed canary restores previous, rollback persists

---

### Phase C: Integration & API (Steps 9-11)
Wire everything together with routes and tests.

**Step 9: API Routes** (4-6 hours)
- Create or extend `backend/src/routes/governance.routes.ts`
- 24 endpoints:
  - Constitution: GET /api/civilization/calibration/constitution, POST (with governance review), POST /:id/activate
  - Trust policies: GET /api/civilization/trust/policies, POST, GET /:id, POST /:id/review, POST /:id/eval, POST /:id/activate, POST /:id/rollback
  - Change requests: GET /api/civilization/calibration/change-requests, POST, GET /:id, POST /:id/review, POST /:id/impact-assessment, POST /:id/canary, POST /:id/rollback
  - Reputation: GET /api/civilization/trust/reputation, GET /:type/:id, POST /events
  - Drift: GET /api/civilization/calibration/drift, POST /detect, POST /:id/propose-change, POST /:id/resolve
- Every write route: validates request, enforces RBAC/governance, calls real service, writes audit event, propagates trace_id, returns real DB state
- Acceptance: Routes call real services (not stubs), RBAC enforced, audit events recorded

**Step 10: Comprehensive Test Suite** (8-10 hours)
- Create `scripts/test_civilization_calibration_trust.py` with 22 assertions
- Test matrix:
  1. Civilization can propose trust-policy change ✓
  2. Proposed change cannot directly modify calibration code ✓
  3. Proposed change cannot modify resolver internals ✓
  4. Prohibited change type is blocked ✓
  5. Constitution check blocks unsafe change ✓
  6. Protected-surface scan blocks unsafe request ✓
  7. Trust policy version created from approved request ✓
  8. Trust impact assessment runs ✓
  9. Failing assessment blocks canary ✓
  10. Passing assessment allows scoped canary ✓
  11. Trust policy canary affects only approved scope ✓
  12. Failed canary rolls back to previous policy ✓
  13. Reputation ledger updates from persisted outcome/eval ✓
  14. Reputation cannot be manually overwritten ✓
  15. Simulation reputation separate from real-world ✓
  16. Drift monitor detects overconfidence drift ✓
  17. Drift event proposes change but doesn't apply ✓
  18. Emergency trust freeze blocks rollout ✓
  19. Requester cannot approve own change ✓
  20. Society cannot approve civilization-wide change alone ✓
  21. Audit events exist and immutable ✓
  22. Trace IDs propagate end-to-end ✓
- Acceptance: All 22 assertions pass with real DB evidence

**Step 11: Integrated Smoke Test** (2-3 hours)
- Create `make civilization-calibration-trust-smoke` target
- 15-step validation:
  1. Create civilization hierarchy (agents, teams, institutions, societies)
  2. Create active calibration constitution
  3. Create baseline trust policy
  4. Record trust reputation events from persisted outcomes/evals
  5. Detect calibration drift
  6. Create change request from drift
  7. Reject prohibited direct calibration mutation (blocked)
  8. Convert safe change to trust policy draft
  9. Run impact assessment
  10. Run eval
  11. Create scoped trust-policy canary
  12. Record canary metrics
  13. Trigger rollback on forced regression
  14. Verify previous policy restored
  15. Verify audit events + trace lineage + protected surfaces unchanged
- Output: ✅ CIVILIZATION CALIBRATION TRUST SMOKE PASSED (only with DB evidence)

---

### Phase D: Documentation (Step 12)
**Step 12: Docs** (2-3 hours)
- Create `docs/CIVILIZATION_CALIBRATION_TRUST_GOVERNANCE.md`
- Sections: Why (civilization influence but not ground-truth), Constitution, Trust Policy Lifecycle, Change Request Lifecycle, Impact Assessment, Reputation Ledger, Drift Monitoring, Canary/Rollback, Protected Surfaces, Prohibited Actions, Emergency Trust Freeze, Human/Governor Gating
- Update existing docs with civilization context

---

## Timeline Estimate

| Phase | Area | Hours | Status |
|-------|------|-------|--------|
| A | Foundation | 28-36 | Ready |
| B | Governance | 16-22 | Ready |
| C | Integration | 14-19 | Ready |
| D | Docs | 2-3 | Ready |
| **Total** | | **60-80** | **Ready** |

---

## Next Step

**Begin Phase A, Step 2: Calibration Constitution Service**

This is the root enforcement mechanism for the entire layer. Once in place, all other services validate against it.

---

## Success Criteria

✅ All 22 test assertions pass with real DB state  
✅ All 6 services implement real logic (not stubs)  
✅ All 24 API routes call real services  
✅ Prohibited changes actually blocked  
✅ Protected surfaces scanned and enforced  
✅ Emergency trust freeze works  
✅ Reputation immutable and event-sourced  
✅ Canary respects scope and restores on failure  
✅ Full audit trail immutable  
✅ Trace IDs link entire flow  
✅ Existing LEVEL_3 tests still pass

---

## Non-Negotiable Rules Enforced

1. ✅ No direct calibration mutation
2. ✅ No self-certification
3. ✅ No silent trust changes
4. ✅ No eval-threshold tampering
5. ✅ No simulation-to-reality leakage
6. ✅ No unilateral civilization override
7. ✅ Existing safety invariants preserved

---

## Critical Notes

- Each service operates on a SINGLE responsibility: Constitution validates, Policy manages versions, Change-Governance orchestrates workflow, Impact-Assessment evaluates, Reputation tracks history, Drift-Monitor detects, Canary deploys, APIs expose
- All services read from DB, compute nothing fake, persist all state
- Immutability enforced via SQL triggers (not application logic)
- Reputation cannot be "corrected" by an update; only by creating a new correction event
- Simulation-derived flag persists; blocks promotion unless governance explicitly approves
- Emergency trust freeze is a global off-switch (civilization-level only)
- Human/governor approval required for civilization-wide changes
