"""Review timeout escalation for the institution kernel."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CONTROLS_FILE = Path(__file__).resolve().parents[1] / "controls.yaml"


def escalate_review_timeouts(db, *, now: datetime | None = None) -> list[str]:
    controls = _load_controls()
    timeout_hours = int(controls.get("review_timeout_hours", 48))
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=timeout_hours)
    escalated: list[str] = []
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, output_id, producing_institution_id, status
              FROM institution_output_reviews
             WHERE status IN ('under_review', 'challenged')
               AND updated_at < %s
            """,
            (cutoff,),
        )
        for review_id, output_id, producing_id, status in cur.fetchall():
            cur.execute(
                """
                INSERT INTO civilization_memory_events
                    (id, entity_type, entity_id, event_type, summary, evidence_refs, created_at)
                VALUES (%s, 'institution', %s, 'review_timed_out', %s, %s::jsonb, %s)
                """,
                (
                    str(uuid.uuid4()),
                    producing_id,
                    f"Review timeout escalated for output '{output_id}'",
                    json.dumps({"review_id": review_id, "status": status, "timeout_hours": timeout_hours}),
                    now or datetime.now(timezone.utc),
                ),
            )
            escalated.append(review_id)
    return escalated


def _load_controls() -> dict:
    if not CONTROLS_FILE.exists():
        return {}
    with open(CONTROLS_FILE) as f:
        return yaml.safe_load(f) or {}
