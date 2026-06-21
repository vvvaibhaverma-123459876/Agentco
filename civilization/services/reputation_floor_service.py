"""Reputation floor enforcement for institutions and departments."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

CONTROLS_FILE = Path(__file__).resolve().parents[1] / "controls.yaml"


def enforce_reputation_floor(db) -> list[dict]:
    controls = _load_controls()
    floor = float(controls.get("reputation_floor", -2.0))
    suspended: list[dict] = []
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        for table, entity_type in (("institutions", "institution"), ("departments", "department")):
            cur.execute(
                f"""
                SELECT id, reputation_score
                  FROM {table}
                 WHERE status = 'active'
                   AND reputation_score IS NOT NULL
                   AND reputation_score < %s
                """,
                (floor,),
            )
            rows = cur.fetchall()
            for entity_id, reputation_score in rows:
                cur.execute(f"UPDATE {table} SET status = 'suspended', updated_at = %s WHERE id = %s", (now, entity_id))
                cur.execute(
                    """
                    INSERT INTO civilization_memory_events
                        (id, entity_type, entity_id, event_type, summary, evidence_refs, created_at)
                    VALUES (%s, %s, %s, 'entity_suspended', %s, %s::jsonb, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        entity_type,
                        entity_id,
                        f"{entity_type} suspended below reputation floor",
                        json.dumps({"reputation_score": reputation_score, "floor": floor}),
                        now,
                    ),
                )
                suspended.append({"entity_type": entity_type, "entity_id": entity_id, "reputation_score": reputation_score})
    return suspended


def _load_controls() -> dict:
    if not CONTROLS_FILE.exists():
        return {}
    with open(CONTROLS_FILE) as f:
        return yaml.safe_load(f) or {}
