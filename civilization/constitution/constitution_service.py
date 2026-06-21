"""
Constitution Service — manage civilization constitutions and rules.
"""
from __future__ import annotations

import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional


# Minimum constitution rules that must be enforced
REQUIRED_CONSTITUTION_RULES = [
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


def create_constitution_version(
    civilization_id: str,
    version: str,
    rules_json: dict,
    db=None,
) -> dict:
    """Create a new constitution version (not yet active)."""
    version_id = str(uuid.uuid4())
    text = json.dumps(rules_json, sort_keys=True)
    text_hash = hashlib.sha256(text.encode()).hexdigest()

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO constitution_versions
                (id, civilization_id, version, text_hash, rules_json, active, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, FALSE, %s)
            """,
            (version_id, civilization_id, version, text_hash, json.dumps(rules_json), datetime.now(timezone.utc)),
        )

    return {
        "id": version_id,
        "civilization_id": civilization_id,
        "version": version,
        "text_hash": text_hash,
        "rules": rules_json,
        "active": False,
    }


def activate_constitution_version(
    civilization_id: str,
    version_id: str,
    db=None,
) -> dict:
    """Activate a constitution version (deactivate any existing active version)."""
    with db.cursor() as cur:
        # Deactivate current active version
        cur.execute(
            "UPDATE constitution_versions SET active = FALSE WHERE civilization_id = %s AND active = TRUE",
            (civilization_id,),
        )

        # Activate new version
        cur.execute(
            "UPDATE constitution_versions SET active = TRUE WHERE id = %s",
            (version_id,),
        )

        # Retrieve activated version
        cur.execute(
            "SELECT id, version, rules_json, text_hash FROM constitution_versions WHERE id = %s",
            (version_id,),
        )
        row = cur.fetchone()

    return {
        "id": row[0],
        "version": row[1],
        "rules": row[2],
        "text_hash": row[3],
        "active": True,
    }


def get_active_constitution(civilization_id: str, db) -> Optional[dict]:
    """Get the currently active constitution version."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, version, rules_json, text_hash, created_at
            FROM constitution_versions
            WHERE civilization_id = %s AND active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (civilization_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "version": row[1],
        "rules": row[2],
        "text_hash": row[3],
        "created_at": row[4].isoformat() if row[4] else None,
    }


def validate_constitution_rules(rules: dict) -> bool:
    """
    Validate that a constitution includes all required minimum rules.
    Returns True if all required rules are present.
    """
    rules_list = rules.get("rules", [])
    for required in REQUIRED_CONSTITUTION_RULES:
        if required not in rules_list:
            raise ValueError(f"Constitution missing required rule: {required}")
    return True


def list_constitution_versions(civilization_id: str, db) -> list[dict]:
    """List all constitution versions for a civilization."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, version, text_hash, active, created_at
            FROM constitution_versions
            WHERE civilization_id = %s
            ORDER BY created_at DESC
            """,
            (civilization_id,),
        )
        rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "version": row[1],
            "text_hash": row[2],
            "active": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]
