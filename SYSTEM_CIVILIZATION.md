# Civilization Substrate — System Documentation

## Overview

The Civilization Substrate adds a multi-institution coordination layer on top of the Epistemic Reserve. Agent predictions and credentials (from the Reserve) flow upward through a three-level hierarchy; reputation propagates only from recomputable evidence.

---

## Three-Level Hierarchy

```
Institution  (top)
  └─ Department  (mid)
       └─ Agent  (leaf, via AgentMembershipEdge)
```

- **Institution**: Autonomous entity. `parent_id` must be NULL (enforced by DB CHECK).
- **Department**: Belongs to exactly one Institution. `parent_id` NOT NULL, FK to `institutions`.
- **Agent**: Joins a Department via `agent_membership_edges(agent_id, department_id, role_name, active)`.

No Society or Civilization entities exist. The hierarchy stops at Institution.

---

## Five-Department Template

Every institution is created with exactly five mandatory departments:

| Department   | Purpose |
|--------------|---------|
| Production   | Produces outputs for external release |
| Verification | Verifies outputs before external release |
| Audit        | Audits internal processes and compliance |
| Adversarial  | Adversarially challenges own outputs (mandatory, structural) |
| Improvement  | Continuous improvement and lesson integration |

---

## Institution Contract

Each institution requires a YAML contract at `civilization/contracts/{name.lower()}.yaml`.

Required fields:

```yaml
institution_name: Engineering
accepted_inputs: [...]        # non-empty list
produced_outputs: [...]       # non-empty list
verification_required: true
required_external_reviewer: Security   # MUST differ from institution_name (self-cert ban)
failure_conditions: [...]     # non-empty list
escalation_target: governance
reputation_metric: overall_log_score
```

`required_external_reviewer != institution_name` is validated at load time AND enforced at the DB layer.

---

## Self-Certification Ban

`institution_output_reviews` has a DB-level CHECK constraint:

```sql
CONSTRAINT no_self_certification
    CHECK (producing_institution_id <> reviewer_institution_id)
```

Any attempt to insert a self-review row raises `psycopg2.errors.CheckViolation`. This cannot be bypassed by application code.

---

## Review State Machine

```
proposed
  └─ under_review
       ├─ challenged
       │    ├─ approved  ──→ archived
       │    └─ rejected  ──→ archived
       ├─ approved  ──→ archived
       └─ rejected  ──→ archived
```

**Rules:**
- `approved` is only reachable after going through `under_review` (cannot jump from `proposed`).
- `proposed → approved` directly raises `ReviewTransitionError`.
- Every transition writes a `civilization_memory_events` row.

---

## Reputation Propagation Formula

Scores flow upward from Reserve credentials only. No score is written without a memory event.

**Agent score:**
```
agent_score(a) = Reserve credential overall_log_score for agent a
```
(from `calibration` engine `score_agent()`)

**Department score:**
```
department_score(d) = Σ(sample_count(a) × agent_score(a)) / Σ sample_count(a)
                      for all active agents a in department d
```
- Empty department → NULL (not 0)
- NULL agents excluded from sum

**Institution score:**
```
institution_score(i) = Σ(W(d) × department_score(d)) / Σ W(d)
                       for all departments d in institution i with non-NULL score
```
- Weights `W(d)` from `civilization/reputation_weights.yaml` (default 1.0 for all five)
- Empty institution or all-NULL departments → NULL

**Reputation guard:** `reputation_score` columns on `institutions` and `departments` are protected by a BEFORE UPDATE trigger. Any UPDATE that changes `reputation_score` without `SET LOCAL civilization.reputation_update_authorized = 'true'` in the same transaction raises:
```
REPUTATION GUARD: reputation_score may only be updated by the propagation service
```

The propagation service wraps the memory-event INSERT + SET LOCAL + score UPDATE in one explicit transaction (autocommit disabled for the duration).

---

## Governance Rules

All governance actions use `civilization/services/governance_service.py`.

**Valid decision types:** `create_institution`, `retire_institution`, `approve_high_risk_output`, `change_reputation_weights`, `change_contract`

**Status transitions:**
```
proposed → deliberating | approved | rejected
deliberating → approved | rejected
approved → executed | rolled_back
executed → rolled_back
```

**Invariants (all enforced in code):**
1. `approver_entity_id` MUST differ from the entity whose authority the decision expands (self-authority-expansion REJECTED).
2. Every status change writes an audit-log entry to `decision_log`.

---

## Anti-Chaos Controls

Loaded from `civilization/controls.yaml` on every governance call:

| Control | Default | Effect |
|---------|---------|--------|
| `institution_creation_budget` | 10 | (informational; not yet enforced as hard limit) |
| `duplicate_institution_detector` | true | Blocks `create_institution` proposal if active institution with same name exists |
| `unresolved_challenge_blocker` | true | Blocks `approve_high_risk_output` if output has open `challenged` review |
| `review_timeout_hours` | 48 | (informational; enforcement not yet wired) |
| `reputation_floor` | -2.0 | (informational; floor enforcement not yet wired) |
| `emergency_shutdown_flag` | false | When true, all `approve_high_risk_output` proposals are refused immediately |

---

## Memory Events

`civilization_memory_events` records all state changes. Valid `event_type` values (DB CHECK):

- `institution_created`
- `output_created`
- `review_transitioned`
- `reputation_updated`

Each row includes `entity_type`, `entity_id`, `summary`, `evidence_refs` (jsonb), `created_at`.

---

## Implemented vs Not Implemented

### Implemented

- Three-level hierarchy (Institution → Department → Agent)
- Five-department template created atomically with every institution
- Contract loading + validation (YAML, all required fields, self-cert ban)
- Self-certification ban at DB layer (CHECK constraint)
- Reputation guard trigger at DB layer (BEFORE UPDATE trigger)
- Review state machine with full transition table
- Reputation propagation with exact weighted formula
- Memory events on every state change
- Governance decisions with self-authority-expansion check
- Anti-chaos controls: emergency shutdown, duplicate detector, unresolved challenge blocker
- Audit-log entries to `decision_log` on every governance status change
- Phase 7 end-to-end test: Engineering + Security, real Reserve prediction, full loop (1 passed)
- Memory service query functions (get_agent_memory, get_department_memory, get_institution_memory)
- Seed script for additional institutions

### Not Implemented / Deferred

- Society and Civilization entity types (explicitly out of scope per spec)
- `review_timeout_hours` enforcement (informational only)
- `reputation_floor` enforcement (informational only)
- `institution_creation_budget` hard limit (informational only)
- Automatic review timeout sweep job
- Cross-institution reputation comparison views
- Department-level governance decisions
- Agent eviction / membership expiry logic
