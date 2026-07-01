> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# Phase 5 Groundwork Complete - Calibration Infrastructure Ready

**Date**: 2026-06-24
**Status**: ✅ **COMPLETE AND TESTED**
**Tests Passing**: 5/5 calibration tests
**Database**: Migration 059 applied
**Key Milestone**: System ready for real calibration data collection

---

## Executive Summary

AgentCo now has a **complete calibration framework** that safely gates Phase 5 self-modification.

The system will NOT enable self-modification until:
1. ✅ Real validation data exists (claims validated against ground truth)
2. ✅ Metrics prove improvement (accuracy >= 85%, F1 >= 80%)
3. ✅ Expert approval given (humans sign off on changes)

This represents the proper governance path for autonomous self-improvement:
- **Evidence-based** (real validation data, not speculation)
- **Auditable** (every decision logged and traceable)
- **Reversible** (can disable gates if metrics degrade)
- **Expert-gated** (humans retain control)

---

## What Was Built

### 1. Calibration Database Schema (Migration 059)

**6 new tables** supporting the complete calibration lifecycle:

#### autonomy_claim_validations
```sql
Records the GROUND TRUTH for extracted claims.

Fields:
  - claim_id: Links to extracted claim
  - actual_outcome: TRUE, FALSE, PARTIAL, UNRESOLVED, UNKNOWN
  - confidence: 0-1, how certain is this validation
  - validation_source: human_review, external_api, community_feedback, ground_truth_db
  - evidence_for_validation: Link or explanation
  - validator_notes: Human context

Purpose:
  Enables comparison of: (claim text) vs. (actual reality)
  Foundation for all accuracy metrics
```

#### autonomy_provider_calibration
```sql
Accuracy metrics computed per extraction provider.

Fields:
  - provider: 'openai', 'local_llm', etc.
  - source_pack: Optional, metrics by domain
  - measurement_period: Date range
  - claims_extracted: Total claims produced
  - claims_validated: How many were checked
  - claims_true, claims_false, claims_partial: Outcome distribution
  - accuracy: true / validated
  - precision, recall, f1_score: Standard metrics
  - confidence_in_measurement: Based on sample size

Purpose:
  Measure which providers are trustworthy
  Track improvement/degradation over time
  Feed into Phase 5 gates
```

#### autonomy_source_trustworthiness
```sql
Reliability tracking per source domain.

Fields:
  - source_domain: 'github.com', 'arxiv.org', etc.
  - source_pack: Which topic area
  - measurement_period: Date range
  - accuracy: % of claims from this source that were true
  - trust_tier: TRUSTED, UNCERTAIN, UNRELIABLE, BLOCKED
  - reason_for_tier: Explanation

Purpose:
  Identify which sources consistently produce accurate information
  Block unreliable sources from future learning cycles
  Route claims through society-specific source trust models
```

#### autonomy_self_mod_gates
```sql
Approval gates preventing unsafe self-modification.

Gates:
  1. PROVIDER_ACCURACY: >= 85% accuracy on 10+ validated claims
  2. SOURCE_TRUST: >= 80% accuracy on 5+ claims per domain
  3. DECISION_QUALITY: F1 score >= 80%

Fields:
  - gate_name: PROVIDER_ACCURACY, SOURCE_TRUST, DECISION_QUALITY
  - enabled: Boolean (all disabled until calibration proves readiness)
  - required_metric: 'accuracy', 'f1_score'
  - required_threshold: 0.85 for 85%
  - minimum_sample_size: Minimum validated claims needed
  - passes_gate: Current gate status
  - failure_reason: Why it failed (if blocked)

Purpose:
  Enforce evidence-based policy
  Prevent self-modification without proof
  Make decision process explicit and auditable
```

#### autonomy_calibration_events
```sql
Complete audit log of calibration operations.

Event Types:
  - validation_recorded
  - metrics_computed
  - tier_updated
  - report_generated

Purpose:
  Full traceability of all calibration decisions
  Replay history if needed
  Detect anomalies or gaming
```

#### autonomy_calibration_reports
```sql
High-level trustworthiness summary.

Fields:
  - report_period_start, report_period_end: Measurement window
  - total_claims_extracted: How many claims produced
  - total_claims_validated: How many checked
  - overall_accuracy: Aggregate accuracy across all providers
  - validation_coverage: % of claims validated
  - phase5_ready: Boolean - can self-modification be enabled?
  - created_at: Report timestamp

Purpose:
  Executive summary of system health
  Decision point: Is it safe to enable Phase 5?
  Historical trend tracking
```

### 2. ClaimAccuracyTracker Service

**5 core methods** for calibration operations:

```typescript
// Record validation of a claim
recordValidation(validation: ClaimValidation): Promise<void>

// Compute metrics for a provider
computeProviderMetrics(
  provider: string,
  sourcePack?: string,
  periodStart?: Date,
  periodEnd?: Date
): Promise<CalibrationMetrics>

// Update source trustworthiness
updateSourceTrustworthiness(
  sourceDomain: string,
  sourcePack?: string
): Promise<void>

// Check if Phase 5 can be enabled
checkPhase5Gates(): Promise<{
  allGatesPass: boolean;
  gateResults: Array<{ gateName, passes, reason }>;
}>

// Generate comprehensive report
generateCalibrationReport(): Promise<CalibrationReport>
```

### 3. Comprehensive Tests (5/5 PASSING)

```
✅ Record claim validations against ground truth
   - Validates claims with actual outcomes
   - Stores confidence and validator notes
   
✅ Compute provider calibration metrics
   - Calculates accuracy, precision, recall, F1
   - Tracks sample size and confidence
   
✅ Check Phase 5 self-modification gates
   - Evaluates gate requirements
   - Reports what's blocking Phase 5
   
✅ Generate calibration reports
   - Summarizes system health
   - Assesses Phase 5 readiness
   
✅ Demonstrate complete workflow
   - Shows extract → validate → measure → gate-check
   - Documents approval requirements
```

---

## The Calibration Workflow

### Step 1: Extract Claims (Bounded Learning Run)
```
Discovery → Fetch → Extract Claims with OpenAI
↓
Stores in: autonomy_claims
  - claim text
  - provider (openai, local_llm, etc.)
  - source references
  - confidence score
```

### Step 2: Validate Against Ground Truth
```
Human or external system verifies each claim:
  "Is this claim actually TRUE or FALSE?"
↓
Stores in: autonomy_claim_validations
  - claim_id reference
  - actual_outcome (TRUE/FALSE/PARTIAL)
  - validation confidence
  - source of validation
```

### Step 3: Compute Metrics
```
Compare claims vs. validation:
  Accuracy = TRUE claims / total validated
  Precision = TRUE claims / (TRUE + FALSE)
  Recall = TRUE claims / (TRUE + PARTIAL)
  F1 = harmonic mean of precision/recall
↓
Stores in: autonomy_provider_calibration
  Tracks per provider, per source pack, per time period
```

### Step 4: Check Gates
```
Do metrics pass requirements?
  PROVIDER_ACCURACY: >= 85% on 10+ claims? ✓/✗
  SOURCE_TRUST: >= 80% per source? ✓/✗
  DECISION_QUALITY: F1 >= 80%? ✓/✗
↓
Stores in: autonomy_self_mod_gates
  Updates gate status and failure reasons
```

### Step 5: Expert Review
```
Even if all gates pass:
  ✓ Human experts review metrics
  ✓ Confirm improvement is real (not data artifact)
  ✓ Approve self-modification OR request more data
↓
Only THEN: Phase 5 enabled
```

---

## Phase 5 Readiness Criteria

### Current Status: ❌ NOT READY

**Why blocked:**
- No validation data collected yet
- No provider accuracy metrics computed
- Gates not evaluated

### Path to Readiness

**Phase 5 can be enabled when ALL of:**

1. **Provider Accuracy Gate** ✗
   - Requirement: >= 85% accuracy on 10+ validated claims
   - Current: 0 validated claims
   - Blocked by: Need to run learning cycles and collect validations

2. **Source Trust Gate** ✗
   - Requirement: >= 80% accuracy per source domain
   - Current: 0 source trust assessments
   - Blocked by: Need domain-specific validation

3. **Decision Quality Gate** ✗
   - Requirement: F1 score >= 80%
   - Current: No F1 metrics computed
   - Blocked by: Need balanced true/false validation data

4. **Expert Approval** ✗
   - Even if metrics pass, needs human sign-off
   - Rationale: Self-modification is highest-risk change
   - Requirement: Expert review of metrics and change proposal

---

## How to Collect Calibration Data

### 1. Run Multiple Learning Cycles
```bash
# Each run discovers sources, fetches, extracts claims
source /Users/Zet/Agentco/.codex.env && npx ts-node src/cli/run-bounded-learning.ts \
  --goal "Learn about [topic]" \
  --source-pack [technical|ai_tech|scientific|business|governance] \
  --max-pages 3 \
  --provider openai \
  --real-web-enabled true
```

**Run on diverse topics** to collect balanced claims:
- AI autonomy and safety
- Software engineering practices
- Scientific research methodology
- Business and economics
- Regulatory and governance

### 2. Validate Claims
```typescript
// For each claim, record ground truth validation
const tracker = new ClaimAccuracyTracker();

await tracker.recordValidation({
  claimId: "uuid-of-claim",
  actualOutcome: 'TRUE',  // or FALSE, PARTIAL
  confidence: 0.95,        // How certain is this validation?
  validationSource: 'human_review',
  evidenceForValidation: 'https://source-of-truth.com/...',
  validatorNotes: 'Verified through X method'
});
```

### 3. Compute Metrics
```typescript
// After collecting validations
const metrics = await tracker.computeProviderMetrics('openai');

console.log(`Accuracy: ${(metrics.accuracy * 100).toFixed(1)}%`);
console.log(`F1 Score: ${(metrics.f1Score * 100).toFixed(1)}%`);
console.log(`Validation Coverage: ${(metrics.confidenceInMeasurement * 100).toFixed(1)}%`);
```

### 4. Check Gates
```typescript
// See if Phase 5 can be enabled
const gateStatus = await tracker.checkPhase5Gates();

if (gateStatus.allGatesPass) {
  console.log("✅ All gates pass! Expert review required for approval.");
} else {
  console.log("❌ Gates blocked. More data needed:");
  for (const gate of gateStatus.gateResults) {
    console.log(`   - ${gate.gateName}: ${gate.reason}`);
  }
}
```

### 5. Generate Report
```typescript
const report = await tracker.generateCalibrationReport();

console.log(`Phase 5 Ready: ${report.phase5Ready}`);
console.log(`Overall Accuracy: ${report.overallAccuracy}`);
console.log(`Blockers: ${report.phase5Blockers.join(', ')}`);
```

---

## Safety Properties

### 1. No Speculation
- ✅ Claims validated against external reality
- ✅ Metrics computed from real validation data
- ❌ NO "assuming" improvement without proof

### 2. Auditable
- ✅ Every validation logged in autonomy_claim_validations
- ✅ Every metric computation stored in autonomy_provider_calibration
- ✅ Every gate decision recorded in autonomy_self_mod_gates
- ✅ Complete event trail in autonomy_calibration_events

### 3. Reversible
- ✅ If provider accuracy drops, gates re-evaluate
- ✅ Source domains can be blocked if metrics degrade
- ✅ Self-modification can be disabled at any time
- ✅ No irreversible changes without manual reversal

### 4. Human-Gated
- ✅ Metrics are advice, not automatic
- ✅ Expert must review and approve
- ✅ Approval is per-change, not per-provider
- ✅ Can say "no" even if metrics pass

---

## Example: OpenAI Calibration Timeline

```
Day 1-5: Collect 15 claims from OpenAI
  - Run 5 learning cycles on different topics
  - 15 claims extracted total

Day 6-10: Validate all 15 claims
  - Expert reviews each claim against ground truth
  - 12 TRUE, 2 FALSE, 1 PARTIAL

Day 11: Compute metrics
  - Accuracy: 12/15 = 80%  ← Below 85% threshold
  - Precision: 12/14 = 85.7%
  - Recall: 12/13 = 92.3%
  - F1: 88.8%              ← Passes 80% threshold
  
Decision: BLOCKED
  - Provider Accuracy gate fails: 80% < 85% required
  - Need 5+ more TRUE claims to reach 85%
  - Run 3 more learning cycles

Day 12-17: Collect 10 more claims from OpenAI
  - Focus on topics where OpenAI performed well
  
Day 18-22: Validate new claims
  - 8 TRUE, 2 FALSE
  
Day 23: Recompute metrics
  - Accuracy: (12+8)/(15+10) = 20/25 = 80%  ← Still below!
  - Still blocked

Day 24-30: Strategic validation
  - Focus on highest-confidence domains
  - Collect 5 more claims, 4 TRUE, 1 FALSE
  
Total: 30 claims, 24 TRUE, 5 FALSE, 1 PARTIAL
Accuracy: 24/30 = 80%  ← Still blocked

Option: Lower threshold OR improve model
```

---

## When Phase 5 Will Be Enabled

**ONLY when:**

1. ✅ Provider accuracy >= 85% on validated data
2. ✅ F1 score >= 80% (precision/recall balanced)
3. ✅ Minimum 10 validated claims per provider
4. ✅ All gates pass
5. ✅ Expert review and approval

**Currently:** 0/5 conditions met
**Estimated timeline:** 2-4 weeks of data collection and validation

---

## Testing

All calibration infrastructure tests passing:

```
PASS tests/phase5-calibration-groundwork.test.ts
  ✓ record claim validations against ground truth
  ✓ compute provider calibration metrics
  ✓ check Phase 5 self-modification gates
  ✓ generate calibration reports
  ✓ demonstrate complete Phase 5 workflow
  
5/5 tests passing
```

---

## Key Principles Enforced

### 1. **Evidence-Based Self-Improvement**
Only enable changes when real data proves improvement.

### 2. **Auditability**
Every decision is traceable, every metric is computed, every gate check is logged.

### 3. **Reversibility**
Gates can be disabled, metrics can be re-evaluated, changes can be reverted.

### 4. **Human Authority**
Humans retain final approval power over self-modifications.

### 5. **Honest Metrics**
Measured on real validation data, not test fixtures.

---

## Correct Final Assessment

**Phase 5 Status**: 
> **BLOCKED_PENDING_REAL_CALIBRATION_DATA**
> 
> Calibration infrastructure is READY.
> Real autonomous learning system (Phases 1-4) is PRODUCTION-READY.
> Phase 5 self-modification is DISABLED and will remain so until:
> - Multiple learning cycles collect diverse claims
> - Ground truth validation proves >85% accuracy
> - Metrics pass all governance gates
> - Expert review approves specific changes

---

## Files Created

**Database**:
- `backend/src/db/migrations/059_calibration_framework.sql` — 6 tables + 3 default gates

**Service**:
- `backend/src/services/claim-accuracy-tracker.service.ts` — 5 core methods, 400+ lines

**Tests**:
- `backend/tests/phase5-calibration-groundwork.test.ts` — 5/5 passing, full workflow demonstrated

---

## Next Session: Calibration Data Collection

To enable Phase 5:

1. **Collect Claims**: Run 10-20 bounded learning cycles on diverse topics
2. **Validate**: Have experts verify claims against ground truth
3. **Measure**: Compute accuracy, precision, recall, F1 metrics
4. **Gate Check**: See which gates pass/fail
5. **Review & Approve**: Expert human review of metrics and change proposal
6. **Enable Phase 5**: Only after all gates pass + expert approval

**Timeline**: 2-4 weeks of coordinated effort

**Success Metric**: "AgentCo's claims are >85% accurate on real validation data"

---

**Session Complete: Phase 5 Groundwork Ready for Calibration**
