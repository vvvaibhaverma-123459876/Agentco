# AGENTCO BENCHMARK FIXES - IMPLEMENTATION PLAN

**Status:** 🟡 **IN PROGRESS**
**Start Date:** 2026-06-22
**Target Completion:** 2026-09-22 (3 months)

---

## EXECUTIVE SUMMARY

Based on benchmark results showing **82.7% accuracy (+5.9% vs GPT-4)**, this plan implements critical fixes to improve calibration, adversarial robustness, trust scoring, and expert-level reasoning.

**Current State:**
- Overall Accuracy: 82.7% ✅
- Calibration Gap: 7.0% (acceptable but improvable)
- Expert-Level Accuracy: 71.7% (gap: 11%)
- Adversarial Robustness: 71.7% (gap: 11%)
- Trust Score: 0.62 (need 0.75+)

---

## IMPLEMENTATION ROADMAP

### PHASE 1: IMMEDIATE FIXES (Week 1-2) 🔴 HIGHEST PRIORITY

| Task | File | Status | Owner | Deadline |
|------|------|--------|-------|----------|
| 1.1 Production Safeguards (Source Citation) | backend/src/services/safety.service.ts | ⏳ TODO | Me | Day 2 |
| 1.2 Confidence Flagging System | backend/src/services/confidence.service.ts | ⏳ TODO | Me | Day 2 |
| 1.3 Knowledge Base Versioning | backend/src/db/migrations/020_kb_versioning.sql | ⏳ TODO | Me | Day 3 |

### PHASE 2: SHORT-TERM FIXES (Week 2-4) 🟡 HIGH PRIORITY

| Task | File | Status | Owner | Deadline |
|------|------|--------|-------|----------|
| 2.1 Conformal Prediction Layer | backend/src/services/conformal-prediction.service.ts | ⏳ TODO | Me | Day 5 |
| 2.2 Uncertainty Quantification | backend/src/services/uncertainty-quantification.service.ts | ⏳ TODO | Me | Day 7 |
| 2.3 6-Dimensional Trust Scoring | backend/src/services/trust-scoring.service.ts | ⏳ TODO | Me | Day 10 |
| 2.4 Adversarial Training Dataset | evals/regression/adversarial_test_dataset.py | ⏳ TODO | Me | Day 12 |
| 2.5 Adversarial Robustness Tests | evals/regression/test_adversarial_robustness.py | ⏳ TODO | Me | Day 14 |

### PHASE 3: MEDIUM-TERM FIXES (Month 2-3) 🟢 MEDIUM PRIORITY

| Task | File | Status | Owner | Deadline |
|------|------|--------|-------|----------|
| 3.1 Multi-Agent Reasoning Ensemble | backend/src/services/multi-agent-ensemble.service.ts | ⏳ TODO | Me | Week 5 |
| 3.2 Chain-of-Thought Integration | backend/src/services/reasoning-chain.service.ts | ⏳ TODO | Me | Week 6 |
| 3.3 Knowledge Base Expansion (50K facts) | backend/src/db/migrations/021_expanded_kb.sql | ⏳ TODO | Me | Week 7 |
| 3.4 Real-Time Update System | backend/src/services/kb-update-manager.service.ts | ⏳ TODO | Me | Week 8 |
| 3.5 Expert-Level Reasoning Benchmarks | evals/regression/test_expert_reasoning.py | ⏳ TODO | Me | Week 9 |

---

## DETAILED TASK BREAKDOWN

### PHASE 1: IMMEDIATE FIXES

#### 1.1 Production Safeguards - Source Citation
**Objective:** Every response includes source facts with verification counts

**Implementation:**
- Wrap responses with metadata: {answer, sources: [{fact_id, verification_count, confidence}]}
- Tag each claim with original fact ID from 25K knowledge base
- Display: "According to [702 verified sources], water boils at 100°C"

**Success Criteria:**
- ✅ All responses have sources
- ✅ Verification counts visible
- ✅ Searchable fact database

---

#### 1.2 Confidence Flagging System
**Objective:** Flag responses where confidence > 90% or accuracy low probability

**Implementation:**
- If confidence ≥ 90%: Add flag "⚠️ High confidence - verify before use"
- If confidence < 75%: Add flag "❓ Low confidence - may be incorrect"
- If confidence 75-90%: No flag (normal range)

**Success Criteria:**
- ✅ Automatic confidence flagging
- ✅ User-visible flags
- ✅ Calibration improved

---

#### 1.3 Knowledge Base Versioning
**Objective:** Track KB versions, enable rollback, manage updates

**Implementation:**
- Schema: kb_versions (version, created_at, fact_count, domain_breakdown)
- Schema: fact_audit_log (fact_id, version, timestamp, changed_by, change_type)
- Enable: snapshot KB at specific dates

**Success Criteria:**
- ✅ Version tracking active
- ✅ Audit trail maintained
- ✅ Rollback capability

---

### PHASE 2: SHORT-TERM FIXES

#### 2.1 Conformal Prediction Layer
**Objective:** Guarantee prediction set coverage (e.g., 95% confidence intervals)

**Implementation:**
- Implement conformal prediction algorithm
- Convert point predictions to intervals: [lower, upper]
- Guarantee: "True answer in interval with 95% probability"

**Example Output:**
```
Question: "What is the speed of light?"
Answer: "299,792,458 m/s ± 2,000 m/s"
Confidence: 95% guaranteed coverage
```

**Success Criteria:**
- ✅ Confidence intervals on all answers
- ✅ Coverage ≥ 95% (empirically verified)
- ✅ Calibration gap reduced to <5%

---

#### 2.2 Uncertainty Quantification
**Objective:** Express aleatory (data) and epistemic (model) uncertainty

**Implementation:**
- Aleatory: Uncertainty from multiple possible answers (e.g., "heart rate 60-100 bpm")
- Epistemic: Uncertainty from limited knowledge (e.g., "emerging research suggests...")
- Combine into composite uncertainty score

**Success Criteria:**
- ✅ Uncertainty decomposed
- ✅ Both types expressed in responses
- ✅ Users understand confidence bounds

---

#### 2.3 6-Dimensional Trust Scoring
**Objective:** Composite metric: Accuracy × Calibration × Consistency × Explainability × Uncertainty × Coverage

**Implementation:**
```python
trust_score = (
    accuracy_score: 0.827          # 82.7% correct answers
    × calibration_score: 0.93      # 7% gap (target <5%)
    × consistency_score: 0.95      # 85% std across domains
    × explainability_score: 0.90   # Source citations visible
    × uncertainty_score: 0.92      # Confidence intervals provided
    × coverage_score: 0.85         # 11 domains + expanding
)
= 0.62 (current) → target 0.75+
```

**Calculation:**
- Accuracy: % correct on test set (0-1)
- Calibration: 1 - calibration_gap (0-1)
- Consistency: std_dev of accuracy across domains (higher = more consistent)
- Explainability: % responses with source citations (0-1)
- Uncertainty: quality of confidence bounds (0-1)
- Coverage: % of topics in knowledge base (0-1)

**Success Criteria:**
- ✅ Trust score computed for all responses
- ✅ Score visible in UI
- ✅ Composite score ≥ 0.75 by Month 3

---

#### 2.4 Adversarial Training Dataset
**Objective:** 100+ trick questions to train system on edge cases

**Dataset Structure:**
```python
@dataclass
class AdversarialExample:
    question: str
    correct_answer: str
    common_wrong_answer: str
    semantic_trap: str  # What makes it tricky
    difficulty: str     # subtle, moderate, extreme
```

**Examples:**
- "Is evolution 'just a theory'?" (semantic trap: colloquial vs scientific)
- "Does light have mass?" (requires nuanced answer about rest mass)
- "Can biases be eliminated?" (requires "no but..." answer)
- "Was Renaissance real?" (historiographical construction question)

**Success Criteria:**
- ✅ 100+ adversarial examples created
- ✅ Categorized by trap type
- ✅ Used in training/evaluation

---

#### 2.5 Adversarial Robustness Tests
**Objective:** Evaluate performance on tricky questions

**Test Suite:**
- Semantic traps (word meaning confusion)
- Presupposition failures (false premises)
- Trick math/logic problems
- Historiographical edge cases
- Philosophical nuance

**Success Criteria:**
- ✅ Adversarial accuracy ≥ 78% (up from 71.7%)
- ✅ False confidence reduced
- ✅ Nuanced answers improved

---

### PHASE 3: MEDIUM-TERM FIXES

#### 3.1 Multi-Agent Reasoning Ensemble
**Objective:** Route hard questions to specialized expert agents

**Architecture:**
```
Expert Question (confidence < 0.70)
    ↓
Route to Specialized Agents:
    ├─ Math Expert (for mathematics synthesis)
    ├─ Physics Expert (for physics synthesis)
    ├─ Biology Expert (for biology synthesis)
    ├─ Philosophy Expert (for philosophical reasoning)
    └─ Integration Agent (synthesize answers)
    ↓
Consensus Answer with Higher Confidence
```

**Success Criteria:**
- ✅ Expert-level accuracy 78%+ (up from 71.7%)
- ✅ Routing logic implemented
- ✅ Consensus mechanism working

---

#### 3.2 Chain-of-Thought Integration
**Objective:** Show reasoning steps for complex questions

**Implementation:**
```
Question: "Why did Industrial Revolution start in Britain?"

Chain-of-Thought:
1. Prerequisite: Coal deposits available (fact verified)
2. Condition: Capital accumulation from trade (fact verified)
3. Catalyst: Textile demand from colonies (fact verified)
4. Result: Technology innovation emerged (fact verified)
5. Conclusion: Convergence of factors caused IR in Britain

Each step linked to fact ID and verification count
```

**Success Criteria:**
- ✅ Reasoning visible
- ✅ Steps traceable to facts
- ✅ User can audit logic

---

#### 3.3 Knowledge Base Expansion (50K facts)
**Objective:** Double knowledge base with recent research, medical protocols

**New Domains/Updates:**
- Recent Medical Protocols (2020-2026)
- Latest Physics Discoveries (gravitational waves, exoplanets)
- Climate Science (consensus findings)
- AI/ML Principles (modern techniques)
- Recent History (2000-2026)
- Updated Economics (post-2008 financial crisis models)

**Success Criteria:**
- ✅ 50,000 facts total (up from 25,119)
- ✅ All verified (≥90% confidence)
- ✅ No factual conflicts
- ✅ New domains integrated

---

#### 3.4 Real-Time Update System
**Objective:** Quarterly KB updates, knowledge decay tracking

**Implementation:**
- Scheduled quarterly updates (3/15, 6/15, 9/15, 12/15)
- Ebbinghaus curve tracking: retention of facts over time
- Auto-deprecate facts with low usage/outdated info
- Merge new facts with existing knowledge graph

**Success Criteria:**
- ✅ Update pipeline automated
- ✅ Quarterly releases scheduled
- ✅ Knowledge decay tracked
- ✅ Fact quality maintained

---

#### 3.5 Expert-Level Reasoning Benchmarks
**Objective:** Comprehensive test suite for expert-level performance

**Test Coverage:**
- Mathematical proofs (multi-step)
- Physics synthesis (reconcile theories)
- Biology explanation (complex systems)
- Historical causality (cause-effect chains)
- Philosophical nuance (edge cases)

**Success Criteria:**
- ✅ 50+ expert-level questions
- ✅ Accuracy ≥ 78%
- ✅ Reasoning verifiable
- ✅ Trust score > 0.75

---

## DEPENDENCIES & SEQUENCING

```
Phase 1 (Week 1-2):
├─ 1.1 Safeguards       (prerequisite for all)
├─ 1.2 Confidence Flag  (depends on 1.1)
└─ 1.3 KB Versioning   (parallel)

Phase 2 (Week 2-4):
├─ 2.1 Conformal Pred   (depends on 1.2)
├─ 2.2 Uncertainty      (depends on 2.1)
├─ 2.3 Trust Score      (depends on 2.1, 2.2)
├─ 2.4 Adversarial DS   (parallel)
└─ 2.5 Adversarial Test (depends on 2.4)

Phase 3 (Month 2-3):
├─ 3.1 Ensemble         (depends on 2.3)
├─ 3.2 CoT Integration  (depends on 3.1)
├─ 3.3 KB Expansion     (depends on 1.3)
├─ 3.4 Update System    (depends on 1.3, 3.3)
└─ 3.5 Expert Bench     (depends on 3.1, 3.2)
```

---

## SUCCESS CRITERIA (END OF PHASE 3)

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Overall Accuracy | 82.7% | 85%+ | 🟡 In Progress |
| Expert Accuracy | 71.7% | 78%+ | 🟡 In Progress |
| Adversarial Accuracy | 71.7% | 78%+ | 🟡 In Progress |
| Calibration Gap | 7.0% | <5% | 🟡 In Progress |
| Trust Score | 0.62 | 0.75+ | 🟡 In Progress |
| KB Size | 25K facts | 50K facts | 🟡 In Progress |
| Domain Coverage | 11 | 15+ | 🟡 In Progress |
| Source Citation | 0% | 100% | ⏳ TODO |
| Confidence Flagging | 0% | 100% | ⏳ TODO |
| Uncertainty Intervals | 0% | 100% | ⏳ TODO |

---

## DEPLOYMENT CHECKPOINTS

**Week 2 (Phase 1 Complete):**
- ✅ Safeguards in place
- ✅ All responses cited
- ✅ KB versioning active
- **Action:** Can deploy to beta users with caution

**Week 4 (Phase 2 Complete):**
- ✅ Conformal prediction working
- ✅ Trust score computed
- ✅ Adversarial robustness tested
- **Action:** Can deploy to production with safety protocols

**Week 9 (Phase 3 Complete):**
- ✅ Expert reasoning improved
- ✅ KB expanded to 50K
- ✅ Trust score ≥ 0.75
- **Action:** Full production deployment recommended

---

## RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Conformal prediction too conservative | Medium | Low | Use adaptive coverage |
| KB expansion introduces conflicts | Medium | Medium | Version control + validation |
| Expert agent failures | Low | Medium | Fallback to base system |
| Trust score gaming | Low | Low | Audit trail + monitoring |

---

## RESOURCES REQUIRED

- **Engineering Time:** ~400 hours (50 days full-time)
- **Testing Time:** ~100 hours
- **Documentation:** ~50 hours
- **Total:** ~550 hours (14 weeks at 40 hrs/week)

---

## NEXT STEPS

1. ✅ **Approve Plan** (this document)
2. ⏳ **Phase 1 Implementation** (start immediately)
3. ⏳ **Phase 2 Implementation** (week 2)
4. ⏳ **Phase 3 Implementation** (month 2)
5. ⏳ **Final Testing & Deployment** (month 3)

---

**Last Updated:** 2026-06-22
**Next Review:** Daily standup
**Status:** 🟡 IN PROGRESS
