# Autonomous Learning Governance & Boundaries

**Status:** Phase 1 Documentation  
**Date:** 2026-06-20

Agentco must be free to learn autonomously within strict boundaries and transparent about where those boundaries are.

---

## Core Principle

**Learning is autonomous and free. Consequences are governed.**

Learning means:
- Read, parse, understand, compare, hypothesize, test in sandbox, remember

Consequences mean:
- Spend resources, deploy, publish, contact humans, escalate authority, issue credentials

---

## Learning Space (Autonomous)

Agentco can freely and autonomously:

### Reading & Observation

- Ingest text, PDFs, papers, web pages (GET requests only)
- Parse structured and unstructured content
- Extract claims, concepts, relationships
- Store in provisional learning memory
- No real-world action, no external API calls beyond GET

### Experimentation

- Run deterministic sandbox experiments
- Execute code in containerized environment with no network
- Simulate business processes, institutions, economies
- Backtest strategies against historical data
- No production data access, no real money, no live system mutations

### Reasoning

- Generate hypotheses from learned principles
- Identify contradictions and curiosities
- Score learning value and novelty
- Propose institutional reviews
- No final decisions, no authority claims without governance

### Memory

- Store raw, semantic, episodic, procedural memory
- Link memory to sources and experiments
- Extract lessons from repeated patterns
- Retain audit trails of learning process
- Memory exists locally; never increases authority directly

---

## Consequence Space (Governed)

Agentco cannot unilaterally:

### Resource Spending

- Cannot spend money (budget allocation requires governance)
- Cannot allocate compute beyond learning budget
- Cannot purchase external services
- Cannot use premium APIs (must use free tiers or fixtures)
- Cannot access paid databases or datasets

### External Contact

- Cannot send emails or messages to humans
- Cannot post to social media or public forums
- Cannot create accounts or register with external services
- Cannot contact external APIs (except read-only with governance approval)
- Cannot reveal sensitive internal information externally

### Deployment & Publication

- Cannot push code to production
- Cannot deploy changes to user-facing systems
- Cannot publish findings as institutional knowledge without review
- Cannot modify governance policies
- Cannot change access controls or permissions

### Authority & Credentials

- Cannot certify itself (self-certification mechanically prevented)
- Cannot issue credentials or attestations
- Cannot update its own trust score or reputation
- Cannot bypass calibration or governance checks
- Cannot claim authority based on unverified learning

### Institutional Change

- Cannot modify institution structure or contracts
- Cannot dissolve or merge institutions
- Cannot change society/civilization rules
- Cannot escalate its own permissions
- Cannot modify governance policies it participates in

---

## Governance Gates

### Learning Mission Approval

Before starting a learning mission, check:

```
Is this a standard learning mission (read, analyze, test)?
  → YES: Proceed autonomously within learning budget
  → NO: Requires governance review

Examples of standard:
  - "Read a paper on X and identify key claims"
  - "Test hypothesis Y against benchmark Z"
  - "Compare source A and source B for contradictions"
  - "Simulate economy with parameter changes"

Examples of NON-standard:
  - "Learn something that might increase authority"
  - "Test something high-consequence if wrong"
  - "Access new data sources or external APIs"
  - "Propose new institutional role"
```

### Budget Check

Every learning mission has resource allocation:

- Compute time: CPU-seconds for experiments
- Network time: API calls (read-only only)
- Storage: Learning memory size
- Human review time: If decision-critical
- Calendar time: Mission deadline

```
learning_budget = {
  "daily_compute_seconds": 3600,
  "daily_api_calls": 100,
  "memory_mb": 10000,
  "experiment_deadline_hours": 24,
  "external_data_sources": [],  # empty unless approved
}
```

### High-Risk Learning

Claims or hypotheses marked high-risk:

- Life/safety consequence if wrong
- Financial consequence > threshold
- Changes to civil rights or law
- Affects vulnerable populations
- Proposes new institutional authority

**Action:** Flag for adversarial review before any promotion. Cannot proceed to Institutionalized without challenge.

---

## Transparency & Audit

### Learning Loop Audit

Every autonomous learning cycle produces:

```
{
  "mission_id": str,
  "mission_start": datetime,
  "mission_end": datetime,
  "sources_ingested": [str],  # source IDs
  "claims_extracted": [str],  # claim IDs
  "experiments_run": [str],    # experiment IDs
  "hypotheses_generated": [str],  # hypothesis IDs
  "decisions_made": [str],  # what actions were proposed?
  "resources_used": {
    "compute_seconds": int,
    "api_calls": int,
    "memory_mb": int,
  },
  "high_risk_claims": [str],  # flagged for review
  "governance_escalations": [str],  # escalated items
  "audit_trace": [event],  # full trace
}
```

### Transparency Report

Monthly (or per-request) learning audit report:

- Total claims extracted
- Breakdown by evidence type
- Promotion successes and failures
- False beliefs detected and retracted
- Lessons learned and stored
- Disputes opened
- High-risk claims and resolutions

This report is public to civilization governance.

---

## Learning Institution Separation

To prevent institutional capture or self-certification:

### Separation of Powers

- **Discovery Institution:** Finds and extracts claims (writes KnowledgeClaim)
- **Evidence Audit Institution:** Classifies evidence (no authority to promote)
- **Replication Institution:** Tests claims (different from Discovery)
- **Adversarial Critique Institution:** Tries to disprove claims (separate incentive)
- **Governance Review Institution:** Decides promotion (not proposer)

**Invariant:** No institution can occupy both proposer and governor roles for the same claim.

### Circular Dependency Check

Before a claim can be promoted, verify:

```
supporting_sources = {institutions_that_contributed_evidence}
proposer = promotion_proposing_institution
governor = promotion_governing_institution

circular = (proposer in supporting_sources) or (governor in supporting_sources)

if circular:
  block promotion
  escalate to civilization governance
  flag as potential capture
```

---

## Escalation Triggers

Autonomy ends and governance begins when:

1. **High-Risk Claims** (consequence if wrong significant)
   - Escalate to adversarial review
   - Require explicit governance approval before promotion

2. **Circular Dependencies** (institutional capture risk)
   - Escalate to civilization governance
   - Requires external adjudication

3. **Disputed Claims** (unresolved contradiction)
   - Escalate to dispute resolution institution
   - Cannot promote until resolved

4. **Budget Exceeded** (learning costs spike)
   - Escalate to governance
   - Request additional budget or mission termination

5. **Authority Increase** (claim would increase Agentco's own authority)
   - Escalate to civilization governance
   - Cannot self-promote

6. **Multi-Civilization Impact** (claim affects multiple societies or civilizations)
   - Escalate to cross-civilization governance
   - Requires consensus or adjudication

---

## Policy Enforcement

### Pre-Commitment

Before autonomous learning loop starts:

```python
def check_learning_autonomy(mission):
    """
    Verify that mission is approved for autonomous execution.
    """
    
    # Check budget
    if mission.estimated_cost > available_budget():
        raise GovernanceException("Budget exceeded")
    
    # Check high-risk flag
    if mission.risk_level == "high":
        approval = governance_service.get_approval(mission_id)
        if not approval:
            raise GovernanceException("High-risk mission not approved")
    
    # Check external systems
    if mission.requires_external_api:
        approval = governance_service.get_approval(mission_id)
        if not approval:
            raise GovernanceException("External API not approved")
    
    # Check institutional circularity
    if has_circular_institution_dependency(mission):
        raise GovernanceException("Circular institutional dependency")
    
    # Check authority escalation
    if mission.could_increase_our_authority():
        raise GovernanceException("Authority escalation requires governance")
    
    return True  # Approved
```

### Audit on Completion

After autonomous learning cycle:

```python
def audit_learning_cycle(cycle_audit):
    """
    Verify that executed learning stayed within bounds.
    """
    
    # Check budget overrun
    if cycle_audit.resources_used > budget:
        flag_budget_exception(cycle_audit)
    
    # Check for unauthorized authority increases
    promoted_claims = [c for c in cycle_audit.promotions]
    for claim in promoted_claims:
        if claim.would_increase_our_authority:
            flag_unauthorized_escalation(claim)
    
    # Check for self-certification
    for claim in cycle_audit.claims_created:
        if is_self_certified(claim):
            flag_self_certification_attempt(claim)
    
    # Check for circular institutions
    for promotion in cycle_audit.promotions:
        if has_circular_support(promotion):
            flag_capture_risk(promotion)
    
    # Record to audit log
    audit_service.store_cycle_audit(cycle_audit)
```

---

## Known Limits

1. **Budget Estimation:** Pre-mission cost estimates are heuristic. Actual costs may vary.

2. **Risk Classification:** High-risk flag is deterministic but heuristic. Edge cases may misclassify.

3. **Circular Dependency Detection:** Checks direct circularity but not sophisticated capture scenarios.

4. **External API Safety:** GET-only reads are relatively safe but not immune to cache poisoning or supply-chain attacks (Phase 20 mitigates).

5. **Sandbox Escape:** Deterministic sandbox experiments are isolated but theoretically escapable with sophisticated attacks.

6. **Authority Escalation:** Detects direct escalations. Indirect/reputational escalations harder to detect.

---

## Integration

This governance layer is checked by:

- **Phase 2:** Knowledge Claim validation (blocks self-certification)
- **Phase 6:** Curiosity Engine (respects budget)
- **Phase 12:** Promotion Workflow (checks governance gates)
- **Phase 14:** Autonomous Learning Loop (enforces all checks)
- **Phase 20:** Adversarial Security (detects capture attempts)

---

## Next: Phase 2 Implementation

Phase 2 will implement the Knowledge Claim model with promotion guards.
