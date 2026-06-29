> **Historical/superseded status notice (2026-06-29):** This document is retained for audit history. Do not treat production-ready, complete, or deployment-ready language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml` and summarized in `docs/CURRENT_IMPLEMENTATION_REALITY.md`. As of 2026-06-29, AgentCo is local-native runnable, not production certified, with 18/67 ledger items verified.

# AgentCo: Civilization-Scale Integration Plan
**Production-Grade, Full System Integration**

**Status:** Draft Plan (No Implementation Yet)  
**Date:** 2026-06-23  
**Scope:** Transform AgentCo from bounded autonomy system to functioning civilization-scale system

---

## Executive Summary

AgentCo currently has two disconnected layers:
- **Autonomy Layer** (85% production-ready): 17 specialized agents, bounded research, 50 concurrent specialists
- **Civilization Layer** (Unknown readiness): Governance, institutions, reputation, trust policies

**Goal:** Integrate these layers so that:
1. Specialist agents execute work **within institutional constraints**
2. Agent reputation feeds **into institutional governance**
3. Institutions assign work to **specialized agent teams**
4. System operates **as a civilization, not as isolated layers**

**Scale Target:** 100+ institutions, 1000+ specialized agents, years-long autonomous operation

---

## Part 1: Architecture Integration (Phase 1)

### 1.1 Institutional Work Assignment Model

**Current State:**
- Autonomy: Goals arrive via API, no institutional context
- Civilization: Institutions exist but don't assign work to agents

**Required Integration:**
```
Institution (governance layer)
  ├─ Department: Production
  │   └─ Assigned specialist team: [researcher, code_reviewer, data_analyst]
  ├─ Department: Verification
  │   └─ Assigned specialist team: [quality_auditor, evidence_linker]
  ├─ Department: Audit
  │   └─ Assigned specialist team: [contradiction_hunter, synthesizer]
  ├─ Department: Adversarial
  │   └─ Assigned specialist team: [sentiment_analyzer, comparative_analyst]
  └─ Department: Improvement
      └─ Assigned specialist team: [background_researcher, reviewer]
```

**What Needs Building:**
1. Database schema: `institution_specialist_assignments` table
2. Institution contract extends to include: `assigned_specialist_roles`, `role_restrictions_per_department`
3. Backend route: `POST /api/civilization/institutions/{id}/assign-specialists`
4. Validation: Contract specifies which specialists each department can use

**File Changes Required:**
- `civilization/services/institution_service.py` - Add specialist assignment logic
- `civilization/domain/entities.py` - Add assignment data structures
- Backend: Add institution work assignment routes
- Database: Migration for specialist assignment schema

### 1.2 Work Request Model (Institution → Autonomy)

**Current State:**
- Autonomy accepts goals with no institutional origin
- No link between goals and institutions

**Required Integration:**
```
Institution submits work request:
{
  "institution_id": "uuid",
  "department": "Production",
  "objective": "Research market trends in AI safety",
  "required_specialists": ["researcher", "data_analyst"],
  "budget": {
    "tokens": 50000,
    "iterations": 100,
    "seconds": 7200  // 2 hours
  },
  "verification_required": true,
  "external_reviewer": "trusted-human-id",
  "reputation_metric": "evidence_quality_score"
}
```

Autonomy orchestrator receives work request:
1. Creates goal with institutional context
2. Spawns only approved specialists for that department
3. Tracks progress for institutional record
4. Returns results to institution for verification

**File Changes Required:**
- Backend: `autonomy-orchestrator.service.ts` - Accept institutional work requests
- Backend: `autonomy.routes.ts` - Add `POST /api/autonomy/work-requests` endpoint
- Backend: `team-activation.service.ts` - Validate specialist assignments per department
- Database: Migration for work request tracking

### 1.3 Reputation Feedback Loop (Autonomy → Civilization)

**Current State:**
- Autonomy layer: Agents complete work, no performance tracking beyond metrics
- Civilization layer: Reputation system exists but doesn't receive autonomy performance data

**Required Integration:**
```
Agent completes work:
  1. Evidence quality score computed
  2. Claim accuracy score computed
  3. Token efficiency score computed
  4. Specialist reputation updated in civilization system
  5. Department reputation aggregated
  6. Institution reputation recalculated
  7. Reputation-backed decision-making triggers governance changes
```

**Reputation Scoring Model:**
```
specialist_score = (
  evidence_quality_weight * evidence_score +
  claim_accuracy_weight * accuracy_score +
  efficiency_weight * efficiency_score
) / (sum of weights)

department_score = aggregate(specialist_score for all agents in dept)

institution_score = aggregate(department_score for all depts)
```

**File Changes Required:**
- `civilization/services/reputation_service.py` - Add specialist performance scoring
- Backend: `autonomy-orchestrator.service.ts` - Report work results to reputation service
- Database: Migration for specialist performance history
- Database: Trigger to update reputation on work completion

### 1.4 Governance Constraints on Agent Autonomy

**Current State:**
- Autonomy layer: Agents have no governance constraints
- Civilization layer: Constitution exists but doesn't constrain agent actions

**Required Integration:**
```
Before spawning specialist:
  1. Check institution constitutional constraints
  2. Verify specialist role allowed by department contract
  3. Enforce budget constraints from institution
  4. Require governance approval for "high-risk" actions
    (e.g., accessing external APIs, expensive operations)

High-risk action definition per institution:
  - External API calls > token threshold
  - Concurrent specialists > threshold
  - Claims with low confidence
  - Operations conflicting with institution policy
```

**File Changes Required:**
- `civilization/services/governance_service.py` - Add agent action approval workflow
- Backend: `autonomy-orchestrator.service.ts` - Check governance before action execution
- Backend: Route for governance approval of high-risk actions
- Backend: Audit trail for all governance decisions affecting agents

---

## Part 2: Long-Term Coordination (Phase 2)

### 2.1 Goal Hierarchy Model

**Current State:**
- Autonomy: Single flat goals, no hierarchy
- Civilization: Institutions exist but don't plan long-term

**Required Integration:**
```
Institution Goal Hierarchy:
  Root Goal: "Build institutional expertise in market analysis"
    ├─ Sub-goal: "Analyze competitor positioning" (assigned to Production dept)
    │   ├─ Task 1: "Research competitor AI safety claims" (autonomy goal)
    │   └─ Task 2: "Analyze sentiment in competitor comms" (autonomy goal)
    ├─ Sub-goal: "Verify analysis accuracy" (assigned to Verification dept)
    │   └─ Task 3: "Cross-reference findings with trusted sources" (autonomy goal)
    └─ Sub-goal: "Generate institutional learning" (assigned to Improvement dept)
        └─ Task 4: "Extract patterns and actionable insights" (autonomy goal)

Autonomy layer executes tasks in context:
  - Each task knows its parent goal chain
  - Specialist agents can request cross-referencing between related tasks
  - Results roll up to institution for decision-making
```

**File Changes Required:**
- Database: Goal hierarchy schema (parent_goal_id, depth, path)
- Backend: `autonomy-orchestrator.service.ts` - Goal hierarchy awareness
- Backend: Routes for institutional goal planning
- Civilization: Goal planning service in Python layer

### 2.2 Multi-Institutional Coordination

**Current State:**
- Single autonomy system, no coordination between institutions
- Institutions operate independently

**Required Integration:**
```
Cross-institutional scenarios:
  Institution A (Safety Research): "Verify claims about alignment techniques"
  Institution B (Industry Analysis): "Track industry adoption of alignment techniques"
  
Coordination:
  1. Both institutions submit work requests
  2. Autonomy system recognizes overlap (same topic)
  3. Shared evidence/findings used by both institutions
  4. Cost savings tracked (evidence reuse)
  5. Reputation benefits shared proportionally

Cross-institutional constraints:
  - Institution A's results require verification before Institution B can use
  - Reputation conflicts (Institution A's experts vs Institution B's experts)
  - Budget sharing for shared research
```

**File Changes Required:**
- Database: Cross-institutional evidence linking
- Backend: Work request deduplication engine
- Backend: Evidence sharing contracts between institutions
- Civilization: Multi-institution reputation aggregation

### 2.3 Adaptive Specialist Allocation

**Current State:**
- Specialists allocated per-request, no learning from history
- No specialization optimization across institutions

**Required Integration:**
```
Pattern recognition:
  - Track which specialist combinations succeed for which institution types
  - Track which departments benefit from which specialists
  - Learn cost patterns (e.g., which specialists burn through tokens fastest)
  
Adaptive allocation:
  1. Institution submits work request without specifying specialists
  2. System recommends specialist team based on:
     a. Historical success rates for similar work
     b. Current reputation scores
     c. Available capacity
  3. Institution approves or requests alternatives
  4. Specialists execute with learned patterns

File Changes Required:**
- Database: Specialist allocation history and success metrics
- Backend: ML module for specialist recommendation (or rule-based heuristics)
- Backend: Route for specialist recommendation API

---

## Part 3: Production Hardening of Civilization Layer (Phase 3)

### 3.1 Civilization Layer Assessment

**Current Status:** Partially implemented, production readiness UNKNOWN

**Code Review Findings (Initial Assessment):**

✅ **Strengths:**
- `governance_service.py`: Formal decision types, status transitions, audit logging implemented
- Stored controls: Anti-chaos controls in `controls.yaml` (emergency shutdown, duplicate detection, review timeouts)
- Transaction safety: Audit trail writing on every status change
- API endpoints: 31+ endpoints covering constitution, policies, changes, assessment, reputation, drift
- Institutional structure: 5 mandatory departments per institution (Production, Verification, Audit, Adversarial, Improvement)

⚠️ **Gaps to Address:**
1. **Error Handling**: No explicit recovery for failed governance calculations
   - Impact: If reputation calculation crashes mid-decision, system state unknown
   - Fix: Wrap all governance operations in transaction rollback on error

2. **Observability**: No structured logging or metrics visible in services
   - Impact: Can't diagnose governance bottlenecks or failure modes
   - Fix: Add Winston logging to match autonomy layer

3. **Concurrency**: No visible locking for multi-institution decisions
   - Impact: Two institutions approving conflicting decisions simultaneously
   - Fix: Add database-level locking (SELECT FOR UPDATE) on governance tables

4. **Performance**: No caching, index analysis, or load test results
   - Impact: Unknown if reputation calculations scale to 100+ institutions
   - Fix: Profile governance queries under load (Phase 3)

5. **Security**: Reputation system vulnerable to gaming (agents report false work results)
   - Impact: Reputation scores corrupted, cascading decision failures
   - Fix: Mandatory adversarial verification before reputation credit (Phase 1)

6. **Data Consistency**: No distributed tracing between autonomy and civilization
   - Impact: Work completes in autonomy, reputation update fails silently in civilization
   - Fix: Transactional coupling with rollback (Phase 4)

**Assessment Roadmap:**
- **Week 1 (Phase 3.1):** Code audit and error handling fixes
- **Week 2 (Phase 3.1):** Add structured logging + Prometheus metrics
- **Week 3-4 (Phase 3.2-3.3):** Load testing with 100 institutions
- **Week 5-8 (Phase 3.4-3.8):** Security hardening, concurrency fixes, consistency validation

### 3.2 Hardening Priorities (if not production-ready)

Based on autonomy layer hardening precedent:

**Critical (before deployment):**
- [ ] Database transaction consistency for governance decisions
- [ ] Error handling and retry logic for reputation calculations
- [ ] Authentication/authorization for institutional access
- [ ] Audit logging for all governance decisions
- [ ] Graceful handling of institution/agent failures

**High (for operational stability):**
- [ ] Structured logging for governance events
- [ ] Prometheus metrics for institutional operations
- [ ] Rate limiting on governance endpoints
- [ ] Input validation for institutional contracts
- [ ] Connection pooling for database access

**Medium (for visibility):**
- [ ] Distributed tracing across autonomy↔civilization
- [ ] Dashboard for institutional metrics
- [ ] Reports on reputation evolution
- [ ] Governance decision audit trails

### 3.3 Integration Testing Points

**Critical integration tests:**
1. Institution assigns specialists → autonomy system respects assignment
2. Specialist completes work → reputation system receives results
3. Reputation changes → affects future assignments
4. Governance approves action → agent can execute
5. Governance rejects action → agent cannot execute
6. Long-running goal completes → rolls up to institution
7. Cross-institutional evidence sharing → both institutions see results
8. System under load → all layers remain consistent

---

## Part 4: Production Deployment Model (Phase 4)

### 4.1 Data Consistency

**Challenge:** Autonomy and civilization layers operate on separate subsystems
- Autonomy: Specialists, goals, evidence, claims
- Civilization: Institutions, governance, reputation, policies

**Solution:** Transactional coupling
```
Work request → autonomy goal → specialist execution → reputation update
  All in single transaction:
  1. Work request marked "executing"
  2. Autonomy goal created
  3. Specialist spawned and executed
  4. Results recorded
  5. Reputation updated
  6. Work request marked "completed"
  
  If any step fails: Rollback all, mark request "failed"
```

### 4.2 Failure Modes

**Autonomy fails:**
- Institution marked "awaiting-retry"
- Autonomy issues logged
- Reputation not updated (no dishonest credit)
- Institution notified of failure

**Civilization fails:**
- Autonomy results held in "pending-reputation" state
- Governance issues logged
- Governance manually approves reputation updates
- Safety: Autonomy continues, civilization catches up

**Both fail:**
- Escalate to human governance
- System enters "reduced autonomy" mode
- Only verified, pre-approved actions execute

### 4.3 Monitoring & Alerting

**Metrics to expose:**
- Institution backlog (pending work requests)
- Specialist utilization by department
- Reputation drift (unexpected score changes)
- Governance approval times (is governance a bottleneck?)
- Cross-institutional evidence reuse rates
- System consistency (autonomy ↔ civilization sync lag)

**Critical alerts:**
- Reputation calculation failure
- Governance consensus loss (can't approve decisions)
- Specialist allocation deadlock
- Cross-institutional evidence conflicts

---

## Part 5: Civilization-Scale Characteristics (Phase 5)

### 5.1 Emergent Properties to Enable

Once integrated at production level, AGentCo should exhibit:

1. **Institutional Learning:**
   - Institutions improve their work over time
   - Reputation signals drive better specialist assignments
   - Governance adapts based on outcomes

2. **Specialization:**
   - Specialists become better at their role through use
   - Institutions develop expertise niches
   - Knowledge compounds across institutions

3. **Coordination:**
   - Institutions recognize shared problems
   - Evidence sharing reduces duplicate work
   - Cross-institutional insights emerge

4. **Accountability:**
   - Every decision traceable to governance vote
   - Reputation prevents bad actors (institutions or specialists)
   - Adversarial department catches self-serving behavior

5. **Self-Correction:**
   - Governance reviews outcomes
   - Policies adjust based on results
   - Failed strategies replaced with better ones

### 5.2 Scale Targets

**Phase 5 Success Criteria:**
- 100+ institutions operating simultaneously
- 1000+ specialist agents available
- Years-long goal chains (not just single tasks)
- Evidence reuse reducing work by 30%+
- Reputation system driving 80%+ of specialist allocation
- Zero governance deadlocks
- <5% failure rate on work requests
- System self-corrects without human intervention 90% of time

---

## Part 5B: Specialist Performance Scoring (Detailed)

### Concrete Scoring Model

**Evidence Quality Score:**
```
evidence_quality = (
  relevance_score * 0.4 +      // Does evidence directly address goal?
  source_credibility * 0.3 +    // Is source trusted? (URL validation + domain reputation)
  freshness_score * 0.2 +       // Recent enough? (age < 30 days → 1.0, decays)
  citation_count * 0.1          // How many claims cite this evidence?
) / 4

Range: [0.0, 1.0]
Example: Hn article from 3 days ago citing credible source + 5 claims = 0.85
```

**Claim Accuracy Score:**
```
claim_accuracy = (
  evidence_support * 0.5 +      // % of claim evidence confirms it
  expert_verification * 0.3 +   // Did verification dept validate?
  confidence_score * 0.2        // Agent's own confidence in claim
) / 3

Range: [0.0, 1.0]
Example: Claim with 90% supporting evidence + verified = 0.90
```

**Specialist Efficiency Score:**
```
efficiency = (
  token_ratio * 0.4 +           // (budget_tokens - tokens_used) / budget_tokens
  iteration_ratio * 0.3 +       // (budget_iterations - iterations_used) / budget_iterations
  time_ratio * 0.3              // (budget_seconds - seconds_used) / budget_seconds
) / 3

Range: [0.0, 1.0]
Example: Used 50% of tokens, 60% of iterations, 40% of time = 0.50
```

**Specialist Overall Score (Reserve Credential):**
```
specialist_score = (
  evidence_quality_scores.mean() * 0.4 +
  claim_accuracy_scores.mean() * 0.35 +
  efficiency_scores.mean() * 0.25
) / 3

Range: [0.0, 1.0]
Updated after every work completion.

Reputation Floor (controls.yaml): reputation_floor: -2.0
  → Specialist score can't drop below -2.0 (prevents infinite penalization)
```

### Reputation Propagation Algorithm

```
Department Score = Σ(specialist_score * specialist_work_count) / Σ(specialist_work_count)
  If dept empty → NULL (exclude from parent calculation)

Institution Score = Σ(dept_score * dept_weight) / Σ(dept_weight)
  Weights from reputation_weights.yaml
  If all depts NULL → institution score = NULL (can't have zero-expert institutions)
```

### Integration into Governance Decisions

**When Specialist Reputation Affects Decisions:**

1. **Specialist Allocation (Phase 2):**
   - Institution requests work without specifying specialists
   - System recommends: (top 3 specialists by reputation for similar work type)
   - Institution can approve or request alternatives
   
2. **Pre-Approval Automation (Phase 4):**
   - High-reputation specialists (score > 0.8): Auto-approve actions
   - Medium-reputation specialists (score 0.5-0.8): Governance review required
   - Low-reputation specialists (score < 0.5): Mandatory adversarial verification
   
3. **Institution Authority (Phase 5):**
   - Institution reputation grows → Authority to create new departments
   - Institution reputation drops → Authority reduced to single department
   - Reputation controls (controls.yaml): Can trigger governance review

---

## Part 5C: API Contracts (Detailed)

### Institution Work Request API

**Request Format:**
```json
POST /api/autonomy/work-requests
{
  "institution_id": "inst-uuid",
  "department": "Production|Verification|Audit|Adversarial|Improvement",
  "objective": "Research market trends in AI safety",
  "description": "Analyze competitor claims about alignment techniques",
  "required_specialists": [
    {"role": "researcher", "priority": 1},
    {"role": "data_analyst", "priority": 2},
    {"role": "code_reviewer", "priority": 3}
  ],
  "budget": {
    "tokens": 50000,
    "iterations": 100,
    "seconds": 7200
  },
  "verification_required": true,
  "external_reviewer_id": "human-uuid",
  "success_criteria": "Find and verify 5+ credible sources on alignment techniques",
  "risk_level": "low|medium|high",
  "idempotency_key": "request-uuid"
}
```

**Response Format:**
```json
{
  "work_request_id": "wr-uuid",
  "goal_id": "goal-uuid",
  "status": "queued",
  "estimated_start_time": "2026-06-23T14:30:00Z",
  "institution_id": "inst-uuid",
  "assigned_specialists": [
    {
      "specialist_id": "spec-uuid",
      "role": "researcher",
      "reputation_score": 0.82,
      "estimated_cost_tokens": 12000
    }
  ]
}
```

**Work Completion Webhook:**
```json
POST {institution_callback_url}
{
  "work_request_id": "wr-uuid",
  "goal_id": "goal-uuid",
  "status": "completed|failed",
  "results": {
    "evidence_collected": 5,
    "claims_generated": 3,
    "tokens_used": 45000,
    "artifacts": ["ev-uuid-1", "ev-uuid-2", ...],
    "specialist_performance": {
      "researcher": {
        "evidence_quality": 0.87,
        "efficiency": 0.65
      },
      "data_analyst": {
        "evidence_quality": 0.91,
        "efficiency": 0.78
      }
    }
  },
  "verification_status": "pending_verification",
  "verification_deadline": "2026-06-24T14:30:00Z"
}
```

### Governance Approval API

**High-Risk Action Approval:**
```json
POST /api/civilization/approve-action
{
  "action_type": "spawn_specialist|fetch_external_api|use_llm_tokens_over_threshold",
  "specialist_id": "spec-uuid",
  "institution_id": "inst-uuid",
  "risk_level": "medium|high|critical",
  "reason": "Fetching competitor website (external API call)",
  "estimated_cost": {
    "tokens": 5000,
    "reputation_risk": 0.1
  }
}
```

**Response:**
```json
{
  "approval_id": "appr-uuid",
  "status": "approved|approved_with_conditions|rejected|requires_human_review",
  "decision_rationale": "Specialist reputation 0.82, fetching external API allowed",
  "conditions": [
    "Verify source credibility before citing"
  ],
  "governance_decision_id": "gov-uuid"
}
```

---

## Part 5D: Database Transaction Patterns (Detailed)

### Transactional Work Request Completion

**Phase 4 Critical Pattern: Atomic Work → Reputation Update**

```sql
-- BEGIN TRANSACTION (SERIALIZABLE isolation)

-- Step 1: Record work completion
UPDATE autonomy_goals 
  SET status = 'completed', 
      completed_at = NOW(),
      specialist_results = $1::jsonb
WHERE goal_id = $2
RETURNING goal_id, specialist_results;

-- Step 2: Create evidence records (from specialist results)
INSERT INTO autonomy_evidence (id, goal_id, source_id, url, content, ...)
VALUES 
  (uuid_generate_v4(), $goal_id, ..., ...),
  (uuid_generate_v4(), $goal_id, ..., ...)
RETURNING array_agg(id) as evidence_ids;

-- Step 3: Calculate specialist performance scores
INSERT INTO specialist_performance_history (
  specialist_id, work_request_id, evidence_quality, 
  claim_accuracy, efficiency_score, completed_at
)
VALUES ($specialist_id, $work_request_id, $ev_quality, $claim_acc, $eff, NOW())
RETURNING score;

-- Step 4: Update specialist reputation (Reserve Credential)
UPDATE reserve_credentials
  SET overall_log_score = (
    SELECT AVG(evidence_quality * 0.4 + claim_accuracy * 0.35 + efficiency * 0.25)
    FROM specialist_performance_history
    WHERE specialist_id = $specialist_id AND completed_at > NOW() - INTERVAL '90 days'
  )
WHERE specialist_id = $specialist_id
RETURNING overall_log_score;

-- Step 5: Trigger institution reputation recalculation
-- (Via trigger, not explicit transaction step)
-- UPDATE department_reputation WHERE department_id IN (SELECT department_id FROM specialist_assignments WHERE specialist_id = $specialist_id)

-- Step 6: Mark work request as 'completed' in civilization layer
UPDATE work_requests
  SET status = 'completed',
      reputation_updated = true,
      completed_at = NOW()
WHERE work_request_id = $work_request_id;

-- COMMIT or ROLLBACK (all-or-nothing)
```

**Failure Handling:**
```
If any step fails:
  - ROLLBACK entire transaction
  - Set work_request.status = 'failed'
  - Set work_request.failure_reason = error message
  - Create governance_incident for manual review
  - Alert institutional_admin
```

### Cross-Institution Evidence Sharing

**Pattern: Eventual Consistency with Verification**

```sql
-- Institution A completes work, generates evidence
INSERT INTO autonomy_evidence (...) 
VALUES (...) 
RETURNING evidence_id;

-- Mark evidence as 'available_for_sharing'
UPDATE autonomy_evidence
  SET sharing_status = 'available_for_institutional_use',
      created_by_institution = 'inst-a-uuid'
WHERE evidence_id = $evidence_id;

-- Institution B requests same topic
SELECT evidence_id FROM autonomy_evidence
  WHERE topic = $topic 
    AND created_by_institution != 'inst-b-uuid'
    AND sharing_status = 'available_for_institutional_use'
    AND verification_status = 'verified'  -- Must be verified by Verification dept
  ORDER BY created_at DESC
  LIMIT 5;

-- Institution B cites Inst A's evidence
INSERT INTO evidence_citations (
  claiming_institution_id,
  evidence_source_institution_id,
  evidence_id,
  citation_count
)
VALUES ('inst-b-uuid', 'inst-a-uuid', $evidence_id, 1);

-- Reputation credit: Inst A's specialist gets credit for evidence reuse
UPDATE specialist_performance_history
  SET evidence_reuse_citations = evidence_reuse_citations + 1,
      reputation_multiplier = reputation_multiplier * 1.05  -- 5% boost per reuse
WHERE evidence_id = $evidence_id;
```

---

## Part 5E: Load Testing Harness (Detailed)

### Load Test Scenarios

**Scenario 1: 100 Institutions, Sequential Work (Week 5)**

```python
# Test: Each institution submits 1 work request sequentially
for i in range(100):
    institution_id = f"inst-{i}"
    work_request = {
        "institution_id": institution_id,
        "objective": f"Research topic {i}",
        "required_specialists": ["researcher", "data_analyst"],
        "budget": {"tokens": 10000, "iterations": 20, "seconds": 3600}
    }
    response = post('/api/autonomy/work-requests', work_request)
    assert response.status == 201
    work_ids.append(response.work_request_id)

# Monitor:
- Time to spawn each specialist (target: <2s)
- Database connection pool utilization (target: <80%)
- Governance approval latency (target: <500ms)
- Memory usage (target: <2GB)
```

**Scenario 2: 100 Institutions, Parallel Work (Week 6)**

```python
# Test: All 100 institutions submit simultaneously
import concurrent.futures

def submit_work(institution_id):
    return post('/api/autonomy/work-requests', {...})

with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
    futures = [executor.submit(submit_work, f"inst-{i}") for i in range(100)]
    results = [f.result(timeout=30) for f in futures]

# Monitor:
- Deadlock detection (should see none)
- Database transaction conflicts (target: <1%)
- Governance bottleneck (approval latency <2s even with 100 parallel)
- Reputation calculation time (target: <5s for all 100 institutions)
```

**Scenario 3: Failure Recovery (Week 7)**

```python
# Test: Work request succeeds, reputation calculation fails
# Step 1: Monkey-patch reputation service to fail
reputation_service.fail_next_call = True

# Step 2: Submit work request
response = post('/api/autonomy/work-requests', {...})

# Step 3: Verify transaction rolled back
work_request = get(f'/api/autonomy/work-requests/{response.work_request_id}')
assert work_request.status == 'failed'
assert work_request.reputation_updated == False

# Step 4: Verify governance incident created
incidents = get('/api/civilization/incidents?work_request_id=...')
assert len(incidents) > 0

# Monitor:
- No orphaned evidence/claims
- No partial reputation updates
- Incident tracking complete
```

---

## Part 5F: Failure Scenario Walkthrough (Detailed)

### Scenario: Reputation System Crashes Mid-Update

**Setup:**
- Institution A completes work request
- Autonomy layer records evidence, claims, specialist performance
- Reputation service receives update request
- Database connection drops during reputation calculation

**Without Production Hardening:**
```
1. Work recorded as "completed" in autonomy_goals
2. Reputation service tries to update specialist_reputation
3. Database connection drops (TCP timeout)
4. Reputation service hangs for 30 seconds, then fails
5. Work request marked "completed" but "reputation_updated = false"
6. Institution A doesn't get confirmation
7. Specialist reputation stale (shows old score)
8. Next work request uses outdated reputation data
9. Cascading decision errors from stale reputation
→ SILENT DATA CONSISTENCY FAILURE
```

**With Phase 4 Production Hardening:**
```
1. BEGIN TRANSACTION (SERIALIZABLE)
2. Work recorded in autonomy_goals
3. Reputation calculation attempt
4. Database error → Exception caught
5. ROLLBACK entire transaction
6. autonomy_goals reverted to "pending"
7. Work request marked "failed" with reason
8. Governance incident created for manual review
9. System alert: "Reputation calculation failed for work-uuid"
10. Human operator reviews, manually triggers reputation recalculation
11. Consistent state maintained
→ EXPLICIT FAILURE WITH RECOVERY PATH
```

### Scenario: Governance Deadlock (100 Institutions)

**Setup:**
- Institution A approves: "Expand researcher specialist to Production dept"
- Institution B approves: "Restrict researcher specialist to Verification dept only"
- Both governance decisions conflict

**Without Production Hardening:**
```
1. Inst A decision approved (no conflict check)
2. Inst B decision approved (no conflict check)
3. System now in inconsistent state
4. Researcher can't be in both departments + restricted
5. Subsequent work requests hang
6. No clear resolution path
→ GOVERNANCE DEADLOCK
```

**With Phase 4 Production Hardening:**
```
1. Inst A requests decision
2. System checks: Does this conflict with pending decisions? NO
3. Inst A decision approved
4. Inst B requests decision
5. System checks: Does this conflict with approved decisions? YES
6. Governance requires mediation
7. Both institutions notified
8. Governance decision: Reject one, keep one
9. Mediation recorded in audit trail
→ CONFLICT DETECTION + RESOLUTION
```

---

## Part 6: Detailed Implementation Roadmap

### Phase 1: Architecture Integration (8 weeks)
**Deliverables:** Autonomy ↔ Civilization wiring complete

**Week 1-2: Schema & Data Model**
- [ ] Database: Institution specialist assignments
- [ ] Database: Work request tracking
- [ ] Database: Specialist performance history
- [ ] Domain models: Institutional assignment types
- [ ] Domain models: Work request lifecycle

**Week 3-4: Work Assignment Flow**
- [ ] Backend: Institution specialist assignment endpoints
- [ ] Backend: Work request submission endpoints
- [ ] Backend: Autonomy acceptance of institutional work
- [ ] Validation: Specialist assignments match department contracts
- [ ] Error handling: Assignment conflicts, capacity issues

**Week 5-6: Reputation Feedback**
- [ ] Service: Specialist performance scoring
- [ ] Backend: Result reporting to reputation service
- [ ] Database triggers: Reputation recalculation on work completion
- [ ] Tests: Reputation updates on various work outcomes

**Week 7-8: Governance Constraints**
- [ ] Governance: Action approval workflow for high-risk operations
- [ ] Backend: Pre-action governance checks
- [ ] Backend: High-risk action definition per institution
- [ ] Integration tests: Full autonomy ↔ civilization workflow

**Success Criteria:**
- [ ] Single work request flows from institution → specialist → reputation
- [ ] Specialist assignment constraints enforced
- [ ] All interactions logged and audited
- [ ] No data loss on system restart
- [ ] Zero race conditions under load

### Phase 2: Long-Term Coordination (6 weeks)
**Deliverables:** Goal hierarchies, multi-institution coordination

**Week 1-2: Goal Hierarchy**
- [ ] Database: Goal parent/child relationships, depth tracking
- [ ] Backend: Goal hierarchy API endpoints
- [ ] Backend: Hierarchical result rollup
- [ ] Tests: Goal chains spanning 5+ levels

**Week 3-4: Cross-Institution Coordination**
- [ ] Backend: Work request deduplication by topic
- [ ] Backend: Evidence sharing contracts
- [ ] Civilization: Multi-institution reputation aggregation
- [ ] Tests: Evidence reuse scenarios

**Week 5-6: Adaptive Allocation**
- [ ] Backend: Specialist success rate tracking
- [ ] Backend: Specialist recommendation engine
- [ ] Tests: Recommendations improve over time
- [ ] Monitoring: Allocation patterns and success rates

**Success Criteria:**
- [ ] 10+ institution chains execute without deadlock
- [ ] Evidence reuse prevents 20%+ duplicate work
- [ ] Specialist recommendations improve over 100 iterations
- [ ] Multi-institution conflicts resolved by governance

### Phase 3: Civilization Layer Hardening (8 weeks)
**Deliverables:** Production-grade governance layer (matching autonomy layer hardening)

**Week 1-2: Assessment & Critical Fixes**
- [ ] Code audit: governance_service.py, institution_service.py
- [ ] Load testing: 100+ institutions, 1000+ agents
- [ ] Critical fixes: Transaction consistency, error handling
- [ ] Replicate autonomy hardening: connection pooling, retries

**Week 3-4: Observability**
- [ ] Structured logging for all governance decisions
- [ ] Prometheus metrics: governance latency, institutional operations
- [ ] Distributed tracing: autonomy ↔ civilization interactions
- [ ] Audit dashboards

**Week 5-6: Security & Validation**
- [ ] Input validation for institutional contracts
- [ ] Rate limiting on governance endpoints
- [ ] HMAC signing for critical governance operations
- [ ] Reputation system gaming prevention

**Week 7-8: Testing**
- [ ] Integration test suite: 50+ scenarios
- [ ] Chaos testing: component failures, network partitions
- [ ] Load testing under failure conditions
- [ ] 99.9% uptime validation

**Success Criteria:**
- [ ] All services match autonomy layer hardening (85%+ production-ready)
- [ ] No data corruption under any failure mode
- [ ] Reputation impossible to game
- [ ] Governance decisions auditable and reversible

### Phase 4: Production Deployment (4 weeks)
**Deliverables:** Transactional integration, monitoring, failure modes

**Week 1-2: Transactional Coupling**
- [ ] Database: Transactional work request ↔ autonomy ↔ reputation pipeline
- [ ] Error handling: Rollback scenarios for each failure mode
- [ ] Human escalation: Reduced autonomy mode when civilization fails

**Week 3: Monitoring & Alerting**
- [ ] Metrics: Institutional backlog, specialist utilization
- [ ] Alerts: Deadlocks, reputation calculation failures
- [ ] Dashboards: Institution health, autonomy utilization
- [ ] Reports: Weekly institutional performance

**Week 4: Production Release**
- [ ] Staging deployment with 50 institutions
- [ ] Canary rollout to 5 institutions
- [ ] Full rollout to all institutions
- [ ] Runbooks and incident response procedures

**Success Criteria:**
- [ ] 100% work request completion or explicit failure
- [ ] <5 min MTTR for common failure modes
- [ ] Zero unrecoverable data loss
- [ ] Operators can respond to incidents in <10 minutes

### Phase 5: Civilization-Scale Emergence (Ongoing)
**Deliverables:** Self-improving system with civilization characteristics

**Months 2-6:**
- [ ] Pattern detection: Identify emerging specialist specialties
- [ ] Policy learning: Governance adapts based on outcomes
- [ ] Cross-institution insights: Novel knowledge emerging from coordination
- [ ] Reputation dynamics: Score drift indicates system evolution
- [ ] Load balancing: Specialist allocation optimizes institution efficiency

**Success Criteria:**
- [ ] 100+ institutions operating without human intervention
- [ ] Reputation system drives 80%+ of decisions (human approval only high-risk)
- [ ] Evidence reuse reduces work by 30%+
- [ ] System shows self-correction (failures → policy adjustments)
- [ ] Novel institutional behaviors emerge (not explicitly programmed)

---

## Part 7: Risks & Mitigations

### Risk 1: Autonomy-Civilization Desync
**Risk:** Specialist completes work, but reputation system fails to update. Autonomy keeps using good specialists that civilization thinks are bad.

**Mitigation:**
- Transactional coupling (all-or-nothing updates)
- Reputation verification before allocation (audit against actual outcomes)
- Periodic reconciliation jobs (find and fix stale reputation)
- Alerts on sync lag >1 minute

### Risk 2: Governance Bottleneck
**Risk:** Autonomy wants to spawn 100 specialists, but governance approval is 10/min. Massive backlog.

**Mitigation:**
- Pre-approved action classes (common requests don't need approval)
- Batch approval workflows
- Reputation-based trust (high-reputation specialists auto-approved)
- Async approval (execute, then verify)

### Risk 3: Reputation Gaming
**Risk:** Malicious institution reports false work results to boost specialist reputation. Reputation system corrupted.

**Mitigation:**
- Adversarial department verification (must validate before reputation credit)
- External audits (spot-check work)
- Reputation penalties for conflicting evidence
- Conservative scoring (guilty until proven innocent)

### Risk 4: Scale Failure
**Risk:** System works at 10 institutions, fails at 100. Database locks, consensus algorithm doesn't scale.

**Mitigation:**
- Load testing at 200+ institutions during Phase 3
- Sharded reputation calculations (per institution initially)
- Eventual consistency for non-critical reputation
- Horizontal scaling architecture from day 1

### Risk 5: Loss of Human Control
**Risk:** System becomes self-directed, ignores institutional constraints.

**Mitigation:**
- Constitutional constraints (hard limits, not soft policies)
- Human approval required for authority expansions
- Governance can always rollback (undo button)
- Budget resets per work request (no compound authority)
- Regular audits of specialist behavior

---

## Part 8: Success Metrics

### Technical Metrics
- [ ] Phase 1 complete: Work request → specialist → reputation = <5 sec latency
- [ ] Phase 2 complete: 100 institutions, 1000 specialists, zero deadlocks
- [ ] Phase 3 complete: All civilization services at 85%+ production-ready
- [ ] Phase 4 complete: 99.9% uptime, <100ms governance approval latency
- [ ] Phase 5 complete: System self-corrects 90% of failure modes

### Behavioral Metrics
- [ ] Institutions learn: reputation-driven allocation improves outcomes by 20%+
- [ ] Specialization emerges: top 20 specialists handle 60% of work
- [ ] Coordination: evidence reuse prevents 30%+ duplicate work
- [ ] Accountability: 100% of decisions traceable to governance vote
- [ ] Self-correction: policies change 5+ times in response to outcomes

### Scale Metrics
- [ ] 100+ institutions (vs 0 integrated today)
- [ ] 1000+ specialist agents (vs 50 current)
- [ ] Years-long goal chains (vs single-task today)
- [ ] Cross-institutional evidence serving 50%+ of requests
- [ ] 90%+ of specialist allocation driven by reputation

---

## Part 9: Dependencies & Assumptions

### Assumption 1: Civilization Layer is Functional
**If false:** Must hardening civilization layer first (estimate: 2-4 weeks additional)

### Assumption 2: Database Can Handle Transactional Coupling
**If false:** Must redesign to eventual consistency (estimate: 4 weeks additional)

### Assumption 3: Autonomy Layer Performance Sufficient for Civilization Load
**If false:** Must optimize autonomy layer (estimate: 2-3 weeks additional)

### Assumption 4: Governance Consensus is Scalable
**If false:** Must redesign governance to sharded/distributed consensus (estimate: 4-6 weeks additional)

---

## Part 10: Critical Path Analysis

### Timeline Dependencies (Pessimistic Path)

```
Week 0-1:  Civilization assessment (GATE 1)
           ├─ If 70%+: Proceed
           └─ If <70%: +8 weeks hardening (then week 8 → week 16 start)

Week 1-8:  Phase 1 architecture integration
           ├─ Database schema changes
           ├─ Backend routes (institution ↔ autonomy)
           ├─ Reputation integration
           └─ Governance constraints wiring (GATE 2 at week 8)

Week 8-14: Phase 2 long-term coordination
           ├─ Goal hierarchies
           ├─ Cross-institution deduplication
           └─ Adaptive specialist allocation (GATE 3 at week 14)

Week 14-22: Phase 3 civilization hardening
           ├─ Code audit + critical fixes (week 14-15)
           ├─ Observability (week 16-18)
           ├─ Load testing 100+ institutions (week 19-21)
           └─ Security hardening (week 22) (GATE 4 at week 22)

Week 22-26: Phase 4 production deployment
           ├─ Transactional coupling (week 22-23)
           ├─ Failure mode testing (week 24-25)
           └─ Staging validation (week 26) (GATE 5 at week 26)

Week 26+:  Phase 5 emergence (ongoing)
```

### Critical Path (What's Not Parallelizable)

1. Civilization assessment (MUST complete before Phase 1)
2. Phase 1 integration (MUST complete before Phase 2)
3. Phase 2 coordination (MUST complete before Phase 3)
4. Phase 3 hardening (MUST complete before Phase 4)
5. Phase 4 deployment (MUST complete before production)

**No parallelization possible** - each phase builds on previous.

### Resource Requirements

**Full-Time Engineering:**
- 1 architect (design integration points)
- 1-2 backend engineers (implement autonomy ↔ civilization wiring)
- 1 infrastructure engineer (database migrations, transaction patterns)
- 1 QA engineer (load testing, failure scenarios)
Total: 3-4 FTE for 26 weeks

**Equipment/Infrastructure:**
- Load test environment: 100+ concurrent specialist processes
- Database: PostgreSQL with 100+ connections, transaction log sizing
- Monitoring: Prometheus + Grafana, log aggregation
- CI/CD: Extended test runs (load tests take 2-4 hours each)

**Cost Estimate:**
- Engineering: 3.5 FTE × 26 weeks × $250/hour = $227,500
- Infrastructure: $2,000/month × 6 months = $12,000
- Total: ~$240,000

---

## Part 10B: Go/No-Go Decision Points (Detailed)

### GATE 1: Before Phase 1 (Week 0-1)
**Civilization Layer Production Readiness Assessment**

**Required Checklist:**
- [ ] Code review: governance_service.py (no obvious bugs)
- [ ] Code review: institution_service.py (contract validation working)
- [ ] Code review: reputation_service.py (scoring logic sound)
- [ ] Error handling: All database operations wrapped in try/catch
- [ ] Audit logging: Every governance decision logged
- [ ] No N+1 queries (reputation calculations efficient)
- [ ] Transaction consistency: Concurrent updates don't corrupt state
- [ ] API contract: All 31 endpoints respond correctly

**Scoring:**
- 8 checks × 1 point each = 8 max points
- Score = points / 8
- Gate threshold: 70% (5.6/8)

**If 70%+: PROCEED to Phase 1**
- Proceed immediately with integration work
- Hardening happens during Phase 3 concurrent with Phase 2

**If <70%: COMPLETE CIVILIZATION HARDENING FIRST**
- Divert 2-4 weeks to harden civilization layer
- Must achieve 70% before Phase 1
- Phase 1 starts Week 4-5 instead of Week 1
- Total project stretches to Week 30-32

**Actual Assessment (Based on Code Review Above):**
```
governance_service.py:  ✓ ✓ ✗ (audit logging confirmed, error handling needs work)
institution_service.py: ✓ ✓ ✗ (contract validation confirmed, no error recovery)
reputation_service.py:  ✓ ✓ ✗ (scoring logic sound, but no transaction protection)
Database operations:    ✗ (no explicit try/catch visible in governance service)
Audit logging:          ✓ (writes audit_event_id on every change)
Query efficiency:       ? (unknown, needs load testing)
Transaction safety:     ? (need SERIALIZABLE isolation testing)
API contracts:          ✓ (31 endpoints defined)

Score: 5/8 = 62.5% - BELOW THRESHOLD
→ RECOMMENDATION: Conduct 2-week civilization hardening before Phase 1
```

### GATE 2: After Phase 1 (Week 8)
**Single Work Request Autonomy ↔ Civilization Cycle Complete**

**Test Scenario:**
```
1. Institution A submits work request
2. Backend creates autonomy goal with institutional context
3. Autonomy spawns assigned specialists
4. Specialist completes work, records evidence
5. Reputation calculation triggered
6. Institution reputation recalculated
7. Work request marked complete
8. Institution receives webhook confirmation
```

**Success Criteria:**
- [ ] All 8 steps complete in <30 seconds (no timeouts)
- [ ] Database in consistent state if process interrupted mid-step
- [ ] Evidence/claims persisted correctly
- [ ] Reputation scores updated correctly
- [ ] Specialist reputation affects future allocations
- [ ] Audit trail complete (can replay entire sequence)
- [ ] Zero data loss under ANY failure scenario

**If Failed:**
- Root cause analysis (1 week)
- Fix integration bugs (1-3 weeks)
- Re-test (1 week)
- Delay Phase 2 start

**If Passed:**
- PROCEED to Phase 2

### GATE 3: After Phase 2 (Week 14)
**Cross-Institution Goal Hierarchy Works Without Deadlock**

**Test Scenario:**
```
1. Create goal hierarchy: Root → 3 Sub-goals → 10 Tasks (13 goals total)
2. All 3 sub-goals assign to different institutions
3. All 10 tasks request work simultaneously
4. System deduplicates evidence where applicable
5. Work completes, results roll up to parent goals
6. No deadlocks, no data loss
```

**Success Criteria:**
- [ ] All 10 tasks complete
- [ ] Evidence deduplication prevents 20%+ duplicate work
- [ ] Parent goals receive correct aggregated results
- [ ] No circular dependencies
- [ ] No deadlocks
- [ ] System consistent under concurrent updates

**If Failed:**
- Likely issue: Deadlock detection, deduplication logic, or parent rollup
- Fix and re-test (2-3 weeks)

**If Passed:**
- PROCEED to Phase 3

### GATE 4: After Phase 3 (Week 22)
**Civilization Layer 85%+ Production-Ready**

**Scorecard (Same as Autonomy Layer Hardening):**
- Architecture: 8/10
- Code Quality: 8/10
- Error Handling: 8/10
- Security: 7/10
- Observability: 8/10
- **Overall: 68/80 = 85%**

**Required Achievements:**
- [ ] All governance operations have explicit error handling + rollback
- [ ] Structured logging for all governance decisions
- [ ] Prometheus metrics: Decision latency, approval rate, reputation updates
- [ ] Rate limiting on governance endpoints
- [ ] Input validation for all institution contracts
- [ ] HMAC signing for critical governance operations
- [ ] Load testing: 100+ institutions, parallel work, failure recovery
- [ ] Zero data corruption under any failure mode

**If Below 85%:**
- Additional hardening (2-4 weeks)
- Re-assess

**If 85%+:**
- PROCEED to Phase 4

### GATE 5: After Phase 4 (Week 26)
**Production Deployment Validation**

**Test Scenario:**
```
Staging Environment: 50 institutions, 500 specialist agents
Duration: 48 hours continuous operation
Load: Constant work request submission, reputation updates
Failure injection: Random network failures, database connection drops, specialist timeouts
```

**Success Criteria:**
- [ ] 100% uptime (no unplanned downtime)
- [ ] All work requests complete or explicitly fail
- [ ] Zero data loss
- [ ] Zero data corruption
- [ ] Reputation system remains consistent
- [ ] Governance decisions remain auditable
- [ ] MTTR <10 minutes for any failure
- [ ] No cascading failures (one failure doesn't trigger others)

**If Failed:**
- Incident analysis (1 week)
- Root cause fix (1-2 weeks)
- Re-test (1 week)
- Delay production by 3-4 weeks

**If Passed:**
- **APPROVED FOR PRODUCTION RELEASE**
- Begin canary rollout: 5 institutions
- Then full rollout: All institutions

---

## Part 10C: Pre-Requirements Checklist

### Must Have Before Starting (Week -2 to 0)

- [ ] Autonomy layer hardening complete (85% production-ready) ← ASSUME DONE
- [ ] Civilization layer code available and reviewable
- [ ] Database schema: 5 tables minimum (governance_decisions, institutions, reputation, work_requests, evidence)
- [ ] Backend: Fastify server running, able to add new routes
- [ ] Python: Specialist agents can be spawned and receive work
- [ ] PostgreSQL: Version 13+, with transaction support
- [ ] CI/CD: Automated testing pipeline in place
- [ ] Monitoring: Prometheus + Grafana running (or ready to deploy)

### Must Not Have

- [ ] Hard-coded specialist lists (should be registry-based)
- [ ] Synchronous HTTP calls without timeouts (every call needs abort_controller)
- [ ] Direct print() statements (must use structured logger)
- [ ] Reputation calculations in memory (must persist to DB)
- [ ] Manual approval of all governance decisions (must automate routine approvals)

---

## Part 11: Integration Architecture Overview

### Current State (Disconnected Layers)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Civilization Layer                          │
│  Governance | Institutions | Reputation | Policies | Decisions  │
│  (31 API endpoints, Python services)                            │
│                  [ISOLATED]                                      │
│  No connection to autonomy below                                │
└─────────────────────────────────────────────────────────────────┘
                          ║
                      [GAP]║[NO DATA FLOW]
                          ║
┌─────────────────────────────────────────────────────────────────┐
│                      Autonomy Layer                             │
│  Specialists | Goals | Evidence | Claims | Metrics | Logging    │
│  (17 agent roles, 85% production-ready)                         │
│                  [ISOLATED]                                      │
│  No connection to civilization above                            │
└─────────────────────────────────────────────────────────────────┘
```

### Post-Integration (Phase 5 Complete)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Civilization Layer                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Governance Decisions                                     │   │
│  │ - Approves specialist assignments per department        │   │
│  │ - Authorizes high-risk actions                          │   │
│  │ - Sets reputation weights                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│           ▲                                    ║                │
│           │                                    ▼                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Institutions (100+)                                      │   │
│  │ ├─ Production Dept → [researcher, data_analyst, ...]   │   │
│  │ ├─ Verification Dept → [quality_auditor, ...]          │   │
│  │ ├─ Audit Dept → [contradiction_hunter, ...]            │   │
│  │ ├─ Adversarial Dept → [sentiment_analyzer, ...]        │   │
│  │ └─ Improvement Dept → [background_researcher, ...]     │   │
│  └──────────────────────────────────────────────────────────┘   │
│           ║                                    ║                │
│   [Work Requests]                      [Reputation Updates]     │
│           ║                                    ║                │
│           ▼                                    ▲                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Reputation System (Reserve Credentials)                  │   │
│  │ - Specialist scores (evidence quality, accuracy, eff)   │   │
│  │ - Department aggregation                                │   │
│  │ - Institution reputation                                │   │
│  │ - Affects future specialist allocations                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
        ║                              ║
        │ [Institutional Work]         │ [Performance Data]
        │ Requests + Constraints       │ & Evidence
        ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Autonomy Layer                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Work Queue                                               │   │
│  │ - Accepts institutional work requests                    │   │
│  │ - Validates specialist assignments from civilization    │   │
│  │ - Enforces governance constraints                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ║                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Specialist Orchestrator (1000+ agents)                   │   │
│  │ - researcher, code_reviewer, data_analyst, ...          │   │
│  │ - Each bounded by budget (tokens, iterations, time)     │   │
│  │ - Subject to governance approval for high-risk ops      │   │
│  │ - Report performance metrics to civilization            │   │
│  └──────────────────────────────────────────────────────────┘   │
│           ║                              ║                     │
│  [Evidence/Claims]               [Specialist Performance]      │
│           ║                              ║                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Results Aggregator                                       │   │
│  │ - Evidence quality scoring                               │   │
│  │ - Claim accuracy assessment                              │   │
│  │ - Efficiency calculation                                 │   │
│  │ - Sends to reputation system for aggregation             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ║                                  │
│                   [Reputation Updates]                         │
│                              ║                                  │
│                              ▲                                  │
└─────────────────────────────────────────────────────────────────┘
        ▲
        │
        └──────────────────────────────────────────────────────────┘
            [Continuous Loop: Work → Perform → Learn → Improve]
```

### Data Flow: Single Work Request (Transactional)

```
1. INSTITUTION SUBMITS WORK
   POST /api/autonomy/work-requests
   {institution_id, objective, required_specialists, budget}
   │
   ▼
2. GOVERNANCE VALIDATES ASSIGNMENT
   GET /api/civilization/institutions/{id}/specialists
   ├─ Department A allowed specialists: [researcher, data_analyst]
   ├─ Current assignments don't conflict?
   └─ Reputation scores acceptable?
   │
   ▼
3. AUTONOMY CREATES GOAL
   INSERT INTO autonomy_goals
   {goal_id, institution_id, specialist_ids, budget}
   │
   ▼
4. SPECIALISTS EXECUTE
   For each specialist:
     POST {specialist_http_endpoint}/execute
     {action_spec, budget}
   │
   ▼
5. EVIDENCE/CLAIMS RECORDED
   INSERT INTO autonomy_evidence
   INSERT INTO autonomy_claims
   (Persistent, linked to goal_id)
   │
   ▼
6. SPECIALIST PERFORMANCE CALCULATED
   evidence_quality = f(relevance, credibility, freshness, citations)
   claim_accuracy = f(evidence_support, verification, confidence)
   efficiency = f(tokens_used, iterations_used, time_used)
   │
   ▼
7. REPUTATION UPDATED (Transactional)
   BEGIN TRANSACTION (SERIALIZABLE)
     UPDATE specialist_reputation = f(evidence_quality, claim_accuracy, efficiency)
     UPDATE department_reputation = aggregate(specialist_reputation)
     UPDATE institution_reputation = aggregate(department_reputation)
   COMMIT
   │
   ▼
8. WORK REQUEST COMPLETED
   UPDATE work_requests SET status = 'completed', reputation_updated = true
   │
   ▼
9. INSTITUTION NOTIFIED
   POST {institution_callback_url}
   {work_request_id, status, results, specialist_performance}
   │
   ▼
10. NEXT WORK REQUEST USES UPDATED REPUTATION
    When Institution requests new work:
      Recommend specialists by reputation score
      (High reputation → auto-approved)
      (Low reputation → requires governance review)
```

---

## Conclusion

This refined plan transforms AgentCo from two disconnected layers into an integrated civilization-scale autonomous system over **26 weeks** (6 months) of production-grade engineering.

**Key Principles:**
1. **No partial builds** - Everything production level
2. **Full integration** - Autonomy and civilization work together
3. **Testing at scale** - 100+ institutions from day 1 of Phase 4
4. **Human oversight** - Constitutional constraints maintain control
5. **Self-improving** - Reputation and governance enable learning

**Final Deliverable:** A functioning civilization-scale autonomous system that:
- Handles 100+ institutions and 1000+ specialist agents
- Makes decisions through institutional governance
- Learns and improves over time
- Maintains human oversight through constitutional constraints
- Never loses critical data or abandons responsibility

---

**Co-Authored-By:** Claude Haiku 4.5 (Plan Phase)
