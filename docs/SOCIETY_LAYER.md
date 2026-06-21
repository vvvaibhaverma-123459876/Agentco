# Society Layer (Phase J)

## Overview

The Society Layer enables multi-institution governance through a collection of institutions that agree on shared standards, domain definitions, and resolution procedures.

A **Society** is a set of institutions unified by:
- **Domain**: The area of governance (engineering, safety, economics, governance, memory)
- **Purpose**: The shared mission and objectives
- **Authority Scope**: The domains and decisions the society has authority over
- **Reputation**: Aggregated from member institution reputations

## Architecture

### Core Entities

#### Society
- `id`: Unique identifier (UUID)
- `name`: Human-readable name (e.g., "Engineering Society")
- `domain`: Primary domain of governance
- `purpose`: Statement of purpose and mission
- `status`: `active` | `suspended` | `retired`
- `authority_scope`: List of domains the society has authority over
- `reputation_score`: Computed from member institutions
- `constitution_ref`: Reference to constitution (future work)
- `metadata`: Arbitrary JSONB data
- `created_at`, `updated_at`: Timestamps

#### Society-Institution Membership
- `society_id`, `institution_id`: Primary key
- `membership_status`: `proposed` | `active` | `suspended` | `retired`
- `role`: Member role (e.g., "member", "reviewer", "lead")
- `joined_at`, `expires_at`: Lifecycle timestamps

### Core Services

#### `society_service.py`
Creates and manages societies and their membership.

**Key functions:**
- `create_society(name, domain, purpose, authority_scope, db)` — Create a new society
- `admit_institution(society_id, institution_id, role, db)` — Admit an active institution
- `suspend_institution_from_society(society_id, institution_id, db)` — Suspend (reversible)
- `retire_institution(society_id, institution_id, db)` — Permanently retire
- `get_society_members(society_id, db, active_only=True)` — List members
- `assign_external_reviewer(society_id, inst_id, reviewer_inst_id, db)` — Assign cross-institution reviewer

#### `society_reputation_service.py`
Aggregates institution reputations into society reputations.

**Key functions:**
- `compute_society_reputation(society_id, db)` → `float` — Average of member reputations
- `update_society_reputation(society_id, db)` → `float` — Persist new score
- `aggregate_member_reputations(society_id, db)` → `dict` — Detailed breakdown

#### `society_governance_service.py`
Governance decisions: admission proposals, approvals, dispute resolution.

**Key functions:**
- `propose_admission(society_id, institution_id, proposed_by, db)` — Create proposal
- `approve_proposal(society_id, proposal_id, approved_by, db)` — Approve and execute
- `reject_proposal(society_id, proposal_id, reason, db)` — Reject proposal
- `can_society_judge_dispute(society_id, dispute_id, db)` → `bool` — Check eligibility
- `resolve_inter_institution_dispute(society_id, dispute_id, ruling, evidence_ref, db)` — Judge dispute

## Seed Societies

On initialization (via `scripts/seed_societies.py`), the following societies are created:

1. **Engineering Society** — engineering standards, code review, architecture
2. **Safety Society** — safety standards, risk management, incident response
3. **Economic Society** — economic policies, budget, compliance
4. **Governance Society** — governance rules, dispute resolution, authority
5. **Memory Society** — institutional memory, precedents, history

## Governance Model

### Admission Flow
1. **Proposal**: An institution is proposed for admission to a society
2. **Approval**: Society leadership approves the proposal
3. **Membership**: Institution becomes active member with assigned role
4. **Membership Update**: Can be suspended (reversible) or retired (permanent)

### Dispute Resolution
- A society can judge inter-institution disputes **among its members**
- A society **cannot** judge disputes where it is the defendant
- Rulings are issued by the society and recorded append-only

### External Reviewers
- When an institution produces output, society can assign an **external reviewer** from a different member institution
- No self-review (reviewer must be from a different institution)
- Ensures cross-institutional accountability

## Reputation Aggregation

A society's reputation is computed as the **average reputation of active members**:

```
society_reputation = mean([inst.reputation_score for inst in active_members])
```

When a member institution's reputation changes, the society reputation should be recomputed.

## Constraints and Limitations

### What Is Implemented
✅ Multi-institution membership  
✅ Governance proposals and approval  
✅ Reputation aggregation  
✅ External reviewer assignment  
✅ Dispute tracking (societies cannot be defendants)  
✅ Append-only audit logs  

### What Is NOT Implemented (Future Work)
❌ Constitution support (Phase K)  
❌ Law registry (Phase K)  
❌ Amendment procedures (Phase K)  
❌ Full cross-society governance  
❌ Emergency controls tied to societies  
❌ Complex multi-signature approvals  

## Database Schema

### `societies`
```sql
CREATE TABLE societies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','suspended','retired')),
    authority_scope JSONB NOT NULL DEFAULT '[]',
    reputation_score DOUBLE PRECISION,
    constitution_ref TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `society_institution_edges`
```sql
CREATE TABLE society_institution_edges (
    society_id TEXT NOT NULL REFERENCES societies(id),
    institution_id TEXT NOT NULL REFERENCES institutions(id),
    membership_status TEXT NOT NULL CHECK (membership_status IN (
        'proposed','active','suspended','retired'
    )),
    role TEXT NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (society_id, institution_id)
);
```

### `society_governance_proposals`
```sql
CREATE TABLE society_governance_proposals (
    id TEXT PRIMARY KEY,
    society_id TEXT NOT NULL REFERENCES societies(id),
    proposal_type TEXT NOT NULL CHECK (proposal_type IN ('admission', 'amendment', 'discipline')),
    subject_id TEXT NOT NULL,
    proposed_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'approved', 'rejected')),
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `society_audit_log`
Append-only audit trail of all society actions.

## Testing

Tests are in `tests/civilization/test_society_layer.py`:

```bash
pytest tests/civilization/test_society_layer.py -v
```

**Test Coverage:**
- ✅ Create society
- ✅ Admit institution through governance
- ✅ Duplicate admission rejected
- ✅ Suspend institution from society
- ✅ Society reputation computed from members
- ✅ Society cannot judge own disputes
- ✅ External reviewer assignment
- ✅ Documentation claims validated

## Usage Example

```python
from civilization.societies import (
    create_society,
    propose_admission,
    approve_proposal,
    get_society_members,
)

# Create a society
eng_society = create_society(
    name="Engineering Society",
    domain="engineering",
    purpose="Govern engineering practices",
    db=conn,
)

# Get all societies
from civilization.societies import list_societies
all_societies = list_societies(conn)

# Propose admission of an institution
proposal = propose_admission(
    society_id=eng_society.id,
    institution_id="some-institution-id",
    proposed_by="admin",
    db=conn,
)

# Approve the proposal
approve_proposal(
    society_id=eng_society.id,
    proposal_id=proposal["proposal_id"],
    approved_by="admin",
    db=conn,
)

# Get active members
members = get_society_members(eng_society.id, conn, active_only=True)
for member in members:
    print(f"  {member['institution_name']} ({member['role']})")
```

## Product Claims

### Allowed (After Phase J Completion)
- "Agentco has a Society layer for multi-institution governance"
- "Societies aggregate reputation from member institutions"
- "Societies can judge disputes between members"
- "Societies can assign external reviewers"
- "Institutional governance can be federated across societies"

### Forbidden (Until Phase K)
- "Agentco has a full civilization layer"
- "Agentco supports constitutional governance"
- "Agentco has laws and amendment procedures"
- "Agentco is a production-grade autonomous civilization"

## Next Steps

After Phase J is complete and tested, proceed to **Phase K: Civilization Layer**, which adds:
- Constitution support with versioning
- Law registry with governance approval
- Amendment procedures
- Full civilization entity with emergency controls
