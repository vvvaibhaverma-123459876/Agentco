# Civilization Layer (Phase K)

## Overview

The Civilization Layer implements a minimal civilization entity with constitutional governance, law registry, society membership, and emergency controls.

**Warning:** This is a foundational implementation. Full civilization features (multi-signature governance, amendment procedures, complete law enforcement) are future work.

## Architecture

### Core Entities

#### Civilization
- `id`: Unique identifier (UUID)
- `name`: Human-readable name (e.g., "Agentco Civilization")
- `constitution_version`: Current constitution version hash
- `status`: `active` | `emergency` | `suspended` | `retired`
- `legitimacy_score`: Computed reputation metric
- `created_at`, `updated_at`: Timestamps

#### Constitution Version
- `id`: Unique identifier
- `civilization_id`: Reference to civilization
- `version`: Semantic version (e.g., "1.0", "2.1")
- `text_hash`: SHA256 hash of canonical constitution text
- `rules_json`: The actual constitution rules
- `active`: Boolean flag (only one active per civilization)
- `created_at`: Timestamp

#### Law
- `id`: Unique identifier
- `civilization_id`: Optional reference (civilization-wide law)
- `society_id`: Optional reference (society-specific law)
- `law_type`: Category of law (e.g., "evidence_policy", "authority_grant")
- `rule_json`: The rule definition
- `status`: `active` | `retired`
- `created_by_decision_id`: Link to governance decision
- `created_at`: Timestamp

#### Civilization-Society Membership
- `civilization_id`, `society_id`: Primary key
- `membership_status`: `active` | `suspended` | `retired`
- `joined_at`: Timestamp

### Core Services

#### `civilization_service.py`
Creates and manages civilizations.

**Key functions:**
- `create_civilization(name, constitution_version, db)` — Create a new civilization
- `get_civilization(civ_id, db)` — Retrieve a civilization
- `admit_society(civilization_id, society_id, db)` — Admit a society
- `get_civilization_societies(civilization_id, db, active_only=True)` — List societies
- `activate_emergency_shutdown(civilization_id, reason, db)` — Block high-risk operations
- `deactivate_emergency_shutdown(civilization_id, db)` — Restore normal operation
- `is_emergency_active(civilization_id, db)` — Check emergency status

#### `constitution_service.py`
Manages constitution versions and rules.

**Key functions:**
- `create_constitution_version(civilization_id, version, rules_json, db)` — Create (inactive)
- `activate_constitution_version(civilization_id, version_id, db)` — Activate one version
- `get_active_constitution(civilization_id, db)` — Get current active constitution
- `validate_constitution_rules(rules)` — Ensure required rules present
- `list_constitution_versions(civilization_id, db)` — List all versions
- `REQUIRED_CONSTITUTION_RULES` — List of minimum required rules

#### `law_registry.py`
Maintains laws at civilization and society levels.

**Key functions:**
- `register_law(law_type, rule_json, civilization_id, society_id, db)` — Register a law
- `get_law(law_id, db)` — Retrieve a law
- `list_civilization_laws(civilization_id, db, status)` — List civilization laws
- `list_society_laws(society_id, db, status)` — List society laws
- `retire_law(law_id, db)` — Deactivate a law

## Minimum Constitution Rules

Every active constitution must include these rules:

```python
[
    "no_self_certification",
    "external_world_claims_require_evidence",
    "simulation_cannot_promote_to_reality",
    "no_authority_expansion_by_self_approval",
    "emergency_powers_expire",
    "unresolved_critical_disputes_block_releases",
    "reputation_cannot_be_manually_written",
    "credential_authority_requires_valid_non_expired_credential",
    "court_rulings_must_be_append_only",
    "laws_require_governance_decision",
]
```

These rules encode fundamental constraints that cannot be overridden.

## Emergency Controls

### Emergency Shutdown

When critical issues arise, a civilization can activate **emergency shutdown** to block high-risk operations:

```python
activate_emergency_shutdown(civ_id, "critical security breach", db)
```

This:
1. Sets civilization status to `emergency`
2. Blocks credential issuance (requires explicit approval)
3. Blocks new task dispatch (requires explicit approval)
4. Logs the emergency activation with reason
5. Requires explicit deactivation (not time-based)

### Emergency Deactivation

```python
deactivate_emergency_shutdown(civ_id, db)
```

Must be an explicit action; emergencies do not auto-expire.

## Constraints and Limitations

### What Is Implemented
✅ Single civilization entity  
✅ Constitution versioning with one active version  
✅ Law registry (civilization and society level)  
✅ Emergency shutdown controls  
✅ Society membership  
✅ Required rule validation  

### What Is NOT Implemented (Future Work)
❌ Amendment procedures (requires multi-signature governance)  
❌ Complete law enforcement (checks not wired into operations)  
❌ Multi-signature approvals  
❌ Civilization-level dispute resolution  
❌ Complete governance lifecycle  
❌ Production civilization readiness  

## Database Schema

### `civilizations`
```sql
CREATE TABLE civilizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    constitution_version TEXT,
    status TEXT NOT NULL CHECK (status IN ('active','emergency','suspended','retired')),
    legitimacy_score DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `constitution_versions`
```sql
CREATE TABLE constitution_versions (
    id TEXT PRIMARY KEY,
    civilization_id TEXT NOT NULL REFERENCES civilizations(id),
    version TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    rules_json JSONB NOT NULL,
    adopted_by_decision_id TEXT,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `laws`
```sql
CREATE TABLE laws (
    id TEXT PRIMARY KEY,
    civilization_id TEXT REFERENCES civilizations(id),
    society_id TEXT REFERENCES societies(id),
    law_type TEXT NOT NULL,
    rule_json JSONB NOT NULL,
    status TEXT NOT NULL,
    created_by_decision_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Testing

Tests are in `tests/civilization/test_civilization_layer.py`:

```bash
pytest tests/civilization/test_civilization_layer.py -v
```

**Test Coverage:**
- ✅ Create civilization
- ✅ Admit society to civilization
- ✅ Activate constitution version
- ✅ Only one constitution active
- ✅ Emergency shutdown/deactivation
- ✅ Law registration
- ✅ Required rules validation

## Usage Example

```python
from civilization.civilization import (
    create_civilization,
    admit_society,
    activate_emergency_shutdown,
)
from civilization.constitution import (
    create_constitution_version,
    activate_constitution_version,
)
from civilization.societies import create_society

# Create civilization
civ = create_civilization("Agentco", db=conn)

# Create and activate constitution
const_rules = {
    "rules": [
        "no_self_certification",
        "external_world_claims_require_evidence",
        "simulation_cannot_promote_to_reality",
        "no_authority_expansion_by_self_approval",
        "emergency_powers_expire",
        "unresolved_critical_disputes_block_releases",
        "reputation_cannot_be_manually_written",
        "credential_authority_requires_valid_non_expired_credential",
        "court_rulings_must_be_append_only",
        "laws_require_governance_decision",
    ],
}
const_v = create_constitution_version(civ["id"], "1.0", const_rules, db=conn)
activate_constitution_version(civ["id"], const_v["id"], db=conn)

# Admit societies
eng_soc = create_society("Engineering", "engineering", "...", db=conn)
admit_society(civ["id"], eng_soc.id, db=conn)

# If crisis: emergency shutdown
activate_emergency_shutdown(civ["id"], "critical issue detected", db=conn)
```

## Product Claims

### Allowed (After Phase K Completion)
- "Agentco has a Civilization layer with constitution support"
- "Agentco enforces minimum constitution rules"
- "Agentco has emergency shutdown capability"
- "Agentco can admit societies into civilizations"

### Forbidden (Until Full Implementation)
- "Agentco is a production-grade civilization"
- "Agentco has complete law enforcement"
- "Agentco has autonomous civilization governance"
- "Agentco amendments are fully governed"

## Next Steps

After Phase K, proceed to:
- **Phase L:** Product API Surface
- **Phase M:** Product UI/Dashboard
- **Phase N:** CI, Acceptance, Release

Then complete the complete civilization implementation in future work.
