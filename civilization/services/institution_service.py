"""
Civilization layer — Institution service.

create_institution(name, contract, db) inserts the institution + its five mandatory
departments in a single transaction.

Contract loading and validation is also here.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "contracts"
CONTROLS_FILE = Path(__file__).resolve().parents[1] / "controls.yaml"

FIVE_DEPARTMENTS = [
    ("Production",    "Produces outputs for the institution"),
    ("Verification",  "Verifies outputs before external release"),
    ("Audit",         "Audits internal processes and compliance"),
    ("Adversarial",   "Adversarially challenges own outputs (mandatory)"),
    ("Improvement",   "Continuous improvement and lesson integration"),
]

VALID_MEMBER_ROLES = frozenset({
    "contributor", "producer", "reviewer", "auditor", "adversary",
    "improver", "lead", "member", "engineer",
})


# ── Contract loading + validation ────────────────────────────────────────────

class ContractValidationError(ValueError):
    pass


def load_contract(institution_name: str) -> dict:
    """Load and validate the YAML contract for an institution. Raises on any violation."""
    path = CONTRACTS_DIR / f"{institution_name.lower()}.yaml"
    if not path.exists():
        raise ContractValidationError(
            f"No contract file for institution '{institution_name}': expected {path}"
        )
    with open(path) as f:
        contract = yaml.safe_load(f)

    _validate_contract(contract)
    return contract


def _validate_contract(c: dict) -> None:
    required_keys = [
        "institution_name", "accepted_inputs", "produced_outputs",
        "verification_required", "required_external_reviewer",
        "failure_conditions", "escalation_target", "reputation_metric",
    ]
    for k in required_keys:
        if k not in c:
            raise ContractValidationError(f"Contract missing required key: {k}")

    if not c["accepted_inputs"]:
        raise ContractValidationError("accepted_inputs must be non-empty")
    if not c["produced_outputs"]:
        raise ContractValidationError("produced_outputs must be non-empty")
    if not c["failure_conditions"]:
        raise ContractValidationError("failure_conditions must be non-empty")
    if not c["reputation_metric"]:
        raise ContractValidationError("reputation_metric must be non-empty")
    if c["required_external_reviewer"] == c["institution_name"]:
        raise ContractValidationError(
            "required_external_reviewer must differ from institution_name (self-cert ban)"
        )


# ── Institution factory ───────────────────────────────────────────────────────

def create_institution(name: str, contract: dict, db) -> dict:
    """
    Insert an institution + its five mandatory departments in one transaction.
    Returns {'institution_id': ..., 'department_ids': {...}}.

    Writes a 'institution_created' memory event in the same transaction.
    """
    _validate_contract(contract)
    _enforce_creation_controls(name, contract, db)

    inst_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with db.cursor() as cur:
        # Institution row
        purpose = contract.get("purpose", name)
        cur.execute(
            """
            INSERT INTO institutions
                (id, name, entity_type, parent_id, status, purpose,
                 authority_scope, metadata, created_at, updated_at)
            VALUES (%s, %s, 'institution', NULL, 'active', %s, %s::jsonb, '{}'::jsonb, %s, %s)
            """,
            (
                inst_id, name, purpose,
                json.dumps(contract.get("accepted_inputs", [])),
                now, now,
            ),
        )

        # Contract row
        cur.execute(
            "INSERT INTO institution_contracts (institution_id, contract, created_at) "
            "VALUES (%s, %s::jsonb, %s)",
            (inst_id, json.dumps(contract), now),
        )

        # Five mandatory departments
        dept_ids = {}
        for dept_name, dept_purpose in FIVE_DEPARTMENTS:
            dept_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO departments
                    (id, name, entity_type, parent_id, status, purpose,
                     authority_scope, metadata, created_at, updated_at)
                VALUES (%s, %s, 'department', %s, 'active', %s, '[]'::jsonb, '{}'::jsonb, %s, %s)
                """,
                (dept_id, dept_name, inst_id, dept_purpose, now, now),
            )
            dept_ids[dept_name] = dept_id

        # Memory event — institution_created (no reputation change)
        cur.execute(
            """
            INSERT INTO civilization_memory_events
                (id, entity_type, entity_id, event_type, summary, evidence_refs, created_at)
            VALUES (%s, 'institution', %s, 'institution_created', %s, '{}'::jsonb, %s)
            """,
            (str(uuid.uuid4()), inst_id, f"Institution '{name}' created with 5 departments", now),
        )

    return {"institution_id": inst_id, "department_ids": dept_ids}


def get_institution(institution_id: str, db) -> Optional[dict]:
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, name, status, reputation_score FROM institutions WHERE id = %s",
            (institution_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "status": row[2], "reputation_score": row[3]}


def get_departments(institution_id: str, db) -> list[dict]:
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, name, status, reputation_score FROM departments WHERE parent_id = %s",
            (institution_id,),
        )
        rows = cur.fetchall()
    return [{"id": r[0], "name": r[1], "status": r[2], "reputation_score": r[3]} for r in rows]


def add_agent_to_department(agent_id: str, department_id: str, role_name: str, db) -> None:
    if role_name not in VALID_MEMBER_ROLES:
        raise ValueError(f"Invalid role_name: {role_name}")
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_membership_edges (agent_id, department_id, role_name, active, created_at)
            VALUES (%s, %s, %s, TRUE, %s)
            ON CONFLICT (agent_id, department_id) DO UPDATE SET active = TRUE
            """,
            (agent_id, department_id, role_name, now),
        )


def add_agent_membership(
    agent_id: str,
    department_id: str,
    role_name: str,
    db,
    expires_at: Optional[datetime] = None,
) -> None:
    if role_name not in VALID_MEMBER_ROLES:
        raise ValueError(f"Invalid role_name: {role_name}")
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_membership_edges
                (agent_id, department_id, role_name, active, expires_at, evicted_at, eviction_reason, created_at)
            VALUES (%s, %s, %s, TRUE, %s, NULL, NULL, %s)
            ON CONFLICT (agent_id, department_id) DO UPDATE
               SET role_name = EXCLUDED.role_name,
                   active = TRUE,
                   expires_at = EXCLUDED.expires_at,
                   evicted_at = NULL,
                   eviction_reason = NULL
            """,
            (agent_id, department_id, role_name, expires_at, now),
        )


def evict_agent(agent_id: str, department_id: str, reason: str, db) -> None:
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE agent_membership_edges
               SET active = FALSE, evicted_at = %s, eviction_reason = %s
             WHERE agent_id = %s AND department_id = %s
            """,
            (now, reason, agent_id, department_id),
        )
        if cur.rowcount == 0:
            raise ValueError("membership not found")


def list_active_members(department_id: str, db) -> list[str]:
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT agent_id FROM agent_membership_edges
             WHERE department_id = %s
               AND active = TRUE
               AND evicted_at IS NULL
               AND (expires_at IS NULL OR expires_at > %s)
            """,
            (department_id, now),
        )
        return [r[0] for r in cur.fetchall()]


def get_cross_institution_reputation(db) -> list[dict]:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT i.id, i.name, i.status, i.reputation_score, COUNT(d.id) AS department_count
              FROM institutions i
              LEFT JOIN departments d ON d.parent_id = i.id
             GROUP BY i.id, i.name, i.status, i.reputation_score
             ORDER BY i.name
            """
        )
        rows = cur.fetchall()
    return [
        {
            "institution_id": r[0],
            "name": r[1],
            "status": r[2],
            "reputation_score": r[3],
            "department_count": r[4],
        }
        for r in rows
    ]


def _load_controls() -> dict:
    if not CONTROLS_FILE.exists():
        return {}
    with open(CONTROLS_FILE) as f:
        return yaml.safe_load(f) or {}


def _enforce_creation_controls(name: str, contract: dict, db) -> None:
    controls = _load_controls()
    if controls.get("duplicate_institution_detector", True):
        with db.cursor() as cur:
            cur.execute("SELECT id FROM institutions WHERE name = %s AND status = 'active'", (name,))
            if cur.fetchone():
                raise ValueError(f"DUPLICATE INSTITUTION: active institution with name='{name}' already exists")
    budget = controls.get("institution_creation_budget")
    if budget is not None:
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM institutions WHERE status = 'active'")
            count = cur.fetchone()[0]
        if count >= int(budget):
            raise ValueError("INSTITUTION CREATION BUDGET EXCEEDED")
