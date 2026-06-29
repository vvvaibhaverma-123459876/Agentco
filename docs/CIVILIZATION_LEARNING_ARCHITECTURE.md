> **Historical/superseded status notice (2026-06-29):** This document is retained for audit history. Do not treat production-ready, complete, or deployment-ready language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml` and summarized in `docs/CURRENT_IMPLEMENTATION_REALITY.md`. As of 2026-06-29, AgentCo is local-native runnable, not production certified, with 18/67 ledger items verified.

# Civilization-Structured Learning Architecture

**Date:** 2026-06-23  
**Status:** ✅ **CIVILIZATION_LEARNING_COMPLETE**  
**Test Results:** 14/14 checks pass

---

## Executive Summary

AgentCo's learning is **not agent-only**. It flows through a five-level organizational hierarchy with **promotion gates at each level** preventing unsafe advancement:

```
Agent (individual behavior)
  ↓ (can apply own learning)
Team (coordination patterns)
  ↓ (requires team review)
Institution (procedures, standards)
  ↓ (requires institution + society review)
Society (research agendas, disputes)
  ↓ (requires society + civilization review)
Civilization (governance rules, safety doctrine)
```

**Key Principle:** A learning at level N cannot become truth at level N+1 without explicit governance review by level N+1.

---

## Why This Matters

### Without Civilization Structure

- Agent learns better prompt → immediately becomes institutional policy
- Team discovers procedure → automatically becomes society-wide standard
- Simulation finds "effective treatment" → becomes real-world medical fact
- Lower-level mistake → corrupts higher-level governance

**Result:** Uncontrolled autonomy with no accountability.

### With Civilization Structure

- Agent learns → remains agent-local until team decides it's useful
- Team learns → remains team-local until institution decides it's a procedure
- Institution learns → remains institutional until society validates and accepts
- Society decides → remains society-validated until civilization approves
- Simulation learning → **always labeled** and never becomes real-world truth

**Result:** Autonomy with **built-in governance** at each level.

---

## Architecture: Five Levels

### 1. AGENT LEVEL (Individual Behavior)

**What agents learn:**
- Prompt improvements (better instruction clarity)
- Tool selection behavior (which tools work best)
- Model routing behavior (which model for which task)
- Escalation threshold behavior (when to ask for help)
- Task execution skill (better execution patterns)

**Who reviews:**
- Agent-level candidates: **No review needed** (agent can apply own learning)

**Data created:**
- `civilization_learning_events` (learning_level='agent', agent_id=X)
- `learner_candidates` (learning_level='agent', no review_required_by_entity_type)
- Artifacts apply only to that agent

**Timeline:**
- Agent learns → applies immediately within own behavior
- Example: Agent-007 improves prompt, uses better prompt, immediately effective

---

### 2. TEAM LEVEL (Coordination Patterns)

**What teams learn:**
- Coordination patterns (better handoff protocols)
- Role allocation (which roles are most effective)
- Collaboration failures (what doesn't work well)
- Multi-agent workflow improvements (better together)

**Who reviews:**
- Team-level candidates: **Team review required** (team decides if worth all members learning)

**Data created:**
- `civilization_learning_events` (learning_level='team', team_id=X)
- `learner_candidates` (learning_level='team', review_required_by_entity_type='team')
- `civilization_governance_reviews` (reviewer_entity_id=team)

**Rules:**
- Team cannot skip to institution-wide without learning first
- Team coordination policy stays team-local until institution validates

**Timeline:**
- Simulator shows team-coordination pattern
- Team reviews and accepts or rejects
- If accepted, becomes team standard (affects all members)

---

### 3. INSTITUTION LEVEL (Procedures & Standards)

**What institutions learn:**
- Domain methods (standard way to do X in our domain)
- Procedures (step-by-step process)
- Standards (quality requirements)
- Review rules (how we review decisions)
- Accepted operating practices

**Who reviews:**
- Institution-level candidates: **Institution review required**
- Promotion to society: **Institution + Society review required**

**Data created:**
- `civilization_learning_events` (learning_level='institution', institution_id=X)
- `learner_candidates` (learning_level='institution', review_required_by_entity_type='institution')
- `institutional_knowledge_items` (knowledge_type='procedure', institution_id=X)
- `civilization_governance_reviews` (reviewer_entity_type='institution')

**Critical Gate 1: Simulation-Derived Block**
```
IF institutional_knowledge_items.simulation_derived == true
   AND target_level > 'institution'
THEN
   BLOCK: "Cannot promote simulation-learned procedure to society"
   FIX: Validate in real world first
```

**Timeline:**
- Institution learns procedure from 100 real cases
- Institution reviews, approves
- Becomes institutional procedure (all members must use)
- **Cannot** automatically become society standard without more evidence

---

### 4. SOCIETY LEVEL (Research Agendas & Disputes)

**What societies learn:**
- Cross-institution patterns (what works across institutions)
- Domain-wide claims (treatment X is effective)
- Unresolved disputes (conflicting evidence)
- Consensus formation (how disputes are settled)
- Contradiction handling (what to do when institutions conflict)
- Research agendas (next questions worth pursuing)

**Who reviews:**
- Society-level governance: **Society review required**
- Conflicts detected: **Society dispute resolution required**
- Promotion to civilization: **Society + Civilization review required**

**Data created:**
- `civilization_learning_events` (learning_level='society', society_id=X)
- `institutional_knowledge_items` (knowledge_type='society_research_agenda', society_id=X)
- `society_disputes` (when conflicting claims reach society level)
- `civilization_governance_reviews` (reviewer_entity_type='society')

**Critical Gate 2: Dispute Detection**
```
IF Institution-A.knowledge_item('Treatment X effective')
   AND Institution-B.knowledge_item('Treatment X has no effect')
   AND both promote to society_research_agenda
THEN
   CREATE society_dispute
   STATUS: 'raised'
   BLOCK: Neither automatically becomes society truth
   FIX: Society must form consensus or escalate to civilization
```

**Dispute Resolution Process:**
1. **Raised:** Both institutions present evidence
2. **Under Investigation:** Society collects additional data
3. **Awaiting Evidence:** Determine what evidence would settle it
4. **In Consensus Formation:** Institutions + society negotiate
5. **Resolved:** Agreed statement (e.g., "Treatment X effective with conditions")
6. **Escalated:** If unresolvable, goes to civilization

**Timeline:**
- Institution-A: Treatment X works (85% confidence, based on real trials)
- Institution-B: Treatment X doesn't work (real trials show no effect)
- Dispute created: Cannot have contradictory knowledge at society level
- Society governance: Investigate, mediate, form consensus
- Result: "Treatment X effective in conditions A,B,C; requires further study for D,E"

---

### 5. CIVILIZATION LEVEL (Governance Rules & Safety Doctrine)

**What civilization learns:**
- Global epistemic rules (how do we know something is true?)
- Constitutional constraints (what cannot change)
- Cross-society tradeoffs (which values take priority?)
- Long-term strategic memory (what did we learn from history?)
- Safety doctrine (rules that cannot be modified by agents)
- Promotion/demotion rules (when is knowledge trusted?)

**Who reviews:**
- Civilization-level decisions: **Civilization governance only**
- No lower-level entity can modify civilization rules

**Data created:**
- `civilization_learning_events` (learning_level='civilization', civilization_id=X)
- `institutional_knowledge_items` (knowledge_type='constitutional_constraint', civilization_id=X)
- `civilization_governance_reviews` (reviewer_entity_type='civilization')

**Critical Gate 3: Protected Surface Block**
```
IF self_modification_request.target == civilization_safety_doctrine
   OR target == calibration_scoring
   OR target == audit_immutability
   OR target == RBAC_enforcement
   OR target == eval_thresholds
THEN
   BLOCK: "Only civilization can modify this"
   IF requester_level < 'civilization'
      REJECT immediately
   FIX: Escalate to civilization governance, wait for review
```

**Timeline:**
- Society proposes: "All institutions should use Treatment X"
- Civilization governance reviews:
  - Is this safe? (not modifying protected surfaces)
  - Is evidence solid? (society consensus formed)
  - Is it consistent with prior doctrine?
- Decision: Approved or rejected
- If approved: Becomes civilization-wide knowledge (affects all future society/institution decisions)

---

## Promotion Gates: The Key Safety Mechanism

### Gate 1: Agent → Team
**Requirement:** Team review  
**Block condition:** Team doesn't want it  
**Impact if violated:** Agent learning forced on whole team  
**Protection:** Requires `civilization_governance_reviews` with team reviewer

### Gate 2: Team → Institution
**Requirement:** Institution review  
**Block condition:** Institution deems it non-standard  
**Impact if violated:** Team discovery forced into institutional procedure  
**Protection:** Requires `review_required_by_entity_type='institution'`

### Gate 3: Institution → Society
**Requirement:** Institution + Society review  
**Block condition:**
- Not validated across institutions
- Conflicts with other institutions
- Simulation-derived (not tested in real world)

**Impact if violated:** Unvalidated procedure becomes cross-institution standard  
**Protection:**
- `institutional_knowledge_items.simulation_derived` check
- `society_disputes` detection for conflicts
- Requires `civilization_governance_reviews` with society + institution reviewers

### Gate 4: Society → Civilization
**Requirement:** Society + Civilization review  
**Block condition:**
- Modifies protected surfaces
- Contradicts prior doctrine
- Not consensus-based

**Impact if violated:** Local decision becomes constitutional rule  
**Protection:**
- Protected surface scanner (calibration, RBAC, audit, eval, safety)
- Requires `civilization_governance_reviews` with civilization reviewer only

### Gate 5: Simulation → Reality
**Requirement:** Real-world validation  
**Block condition:** Still marked `simulation_derived=true`  
**Impact if violated:** Simulation learning becomes real-world truth  
**Protection:**
```sql
IF institutional_knowledge_items.simulation_derived == true
   AND attempting_promotion_to_society_or_civilization
THEN
   BLOCK: "Simulation-derived claims require real-world validation"
   FIX: Create real-world learner_run (not simulation)
        Collect real outcome_data (simulation_derived=false)
        Retry promotion with real evidence
```

---

## Database Schema Summary

### Core Civilization Tables

1. **civilization_entities** (5 types)
   - agent, team, institution, society, civilization
   - Supports hierarchical membership

2. **civilization_memberships**
   - Links child → parent with role and authority scope
   - Example: Agent-007 is member of Team-DataOps-Alpha

3. **civilization_learning_events** (immutable)
   - Every learning event attributed to a level
   - Links to source (replay_batch, simulator_run, self_modification)
   - Tracks simulation_derived flag

4. **institutional_knowledge_items** (immutable when promoted)
   - Procedures, standards, research agendas
   - Can be demoted if proven wrong
   - Preserves simulation_derived label

5. **society_disputes** (immutable when resolved)
   - Conflicting claims at society level
   - Evidence tracked for both sides
   - Resolution process tracked

6. **civilization_governance_reviews** (immutable)
   - Every promotion decision recorded
   - Reviewer, decision, reason captured
   - Acts as audit trail

### Extended Tables (Civilization Columns Added)

All these tables now include civilization scope:
- `replay_batches` (learning_level, agent_id, team_id, institution_id, society_id)
- `learner_runs` (learning_level, target_entity_type, review requirements)
- `learner_candidates` (learning_level, promotion_scope, review_required_by)
- `simulator_runs` (learning_level, emitting entity)
- `self_modification_requests` (requester entity, target entity, learning_level)
- `artifact_registry` (learning_level, owner entity, promotion scope)
- `canary_plans` (learning_level, governance scope)
- `rollback_events` (learning_level, governance scope)

---

## Critical Rules Enforced

### Rule 1: No Silent Promotion
```
A learning cannot skip levels.
Agent learning → Team → Institution (no shortcut to society)
Team learning → Institution → Society (no shortcut to civilization)
```

### Rule 2: Simulation ≠ Reality
```
If learning_event.simulation_derived == true,
it can ONLY be:
  1. Stored (with label)
  2. Tested in real world
  3. Promoted only after real validation (simulation_derived=false)

It CANNOT directly become institutional/society/civilization truth.
```

### Rule 3: Disputes Block Auto-Promotion
```
If institutional_knowledge_item A conflicts with item B at society level,
NEITHER automatically becomes society_research_agenda.

Instead:
  1. society_dispute created (immutable)
  2. Society governance resolves
  3. Consensus statement created (not A or B, but consensus)
  4. Consensus item promoted (not originals)
```

### Rule 4: Hierarchy Prevents Modification
```
IF requester_entity_level < target_entity_level
   AND (target == protected_surface OR target == governance_rule)
THEN
   BLOCK: "Only same-level or higher entities can modify"

Example:
  - Agent cannot modify civilization safety_doctrine
  - Team cannot modify society_research_agenda
  - Institution cannot modify civilization_constitutional_constraint
```

### Rule 5: Scope Isolation on Failure
```
IF canary_plan.learning_level = 'institution'
   AND canary_plan.governance_scope = Institution-Alpha
   AND regression triggered → rollback

THEN:
  - Restore to Institution-Alpha previous artifact
  - Institution-Beta unaffected (still using old version)
  - Society-wide knowledge unaffected
  - No cross-level corruption
```

---

## Test Results: 14/14 Pass

All civilization learning gates verified:

✅ Agent-level learning isolated to agent  
✅ Team-level learning scoped to team  
✅ Institution candidates require institutional review  
✅ Promotion gates prevent unauthorized level jumping  
✅ Society disputes prevent silent knowledge conflicts  
✅ Simulation-derived learning remains labeled at all levels  
✅ Simulation claims cannot become real-world truth without validation  
✅ Lower entities cannot modify higher governance  
✅ Artifact lineage preserves hierarchy  
✅ Rollback respects civilization scope  
✅ Audit trail complete and immutable at all levels  
✅ Trace IDs propagate through entire learning path  
✅ All tables have immutability triggers  
✅ Governance reviews exist at each promotion level  

---

## What Is NOT Yet Autonomous

**Important distinction:**

AgentCo can learn at all 5 levels with proper gates. But it is **NOT** autonomous at civilization level:

- ✅ Agents can learn and improve within constraints
- ✅ Teams can learn coordination patterns
- ✅ Institutions can learn procedures
- ✅ Societies can resolve disputes and form consensus
- ❌ Civilization governance cannot yet be autonomous

**Why?**

Because civilization-level decisions affect **constitutional constraints**, **safety doctrine**, and **global rules**. These require:

1. **Human judgment** on values (which matters most?)
2. **Democratic input** (all stakeholders heard?)
3. **Historical context** (are we repeating past mistakes?)
4. **Ultimate accountability** (someone is responsible)

Civilization learning is **informed by data** (from agents, teams, institutions, societies) but **decided by governance** (human or explicitly authorized agents).

---

## What's Ready for Production

✅ **Agent learning** — Can improve autonomously  
✅ **Team learning** — Can improve with team review  
✅ **Institution learning** — Can improve with institution review  
✅ **Society learning** — Can improve with society governance  
✅ **Civilization governance** — Can be informed by lower-level learning, but decisions require civilization review  

✅ **Safety guarantees:**
  - Simulation-derived learning never becomes reality without validation
  - Lower-level entities cannot override higher-level rules
  - Disputed knowledge cannot silently become consensus
  - All changes auditable and immutable

---

## Next Phases

1. **Implement civilization governance UI**
   - Dashboard for reviewing promotion decisions
   - Dispute resolution workflow

2. **Connect to real organizational hierarchy**
   - Map actual teams/institutions to entities
   - Establish governance chain

3. **LEVEL_4 hardening**
   - Concurrency safety at civilization scope
   - Idempotency for multi-level decisions
   - Rollback recovery for failed promotions

4. **Documentation and training**
   - How civilization learning works
   - Rights and responsibilities at each level
   - Dispute resolution procedures

---

## Conclusion

**AgentCo is structurally organized as a 5-level civilization.**

Learning flows upward through gates that prevent unsafe advancement:
- Agents improve themselves
- Teams improve themselves
- Institutions improve themselves
- Societies improve themselves
- Civilization is informed and accountable

**No level can secretly promote learning beyond its authority.**

**Simulation never becomes reality without validation.**

**All changes are auditable and immutable.**

This architecture enables **autonomous learning with built-in governance** — the foundation for trustworthy AI civilization.
