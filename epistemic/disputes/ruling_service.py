from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Ruling:
    ruling_id: str
    dispute_id: str
    ruling_body_id: str
    outcome: str
    reasoning: str
    penalties: dict | None = None
    precedent_created: bool = False
    final: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class InMemoryRulingService:
    def __init__(self) -> None:
        self.rulings: dict[str, Ruling] = {}

    def add_ruling(
        self,
        dispute_id: str,
        ruling_body_id: str,
        outcome: str,
        reasoning: str,
        *,
        penalties: dict | None = None,
        precedent_created: bool = False,
        final: bool = False,
    ) -> Ruling:
        ruling = Ruling(
            ruling_id=str(uuid.uuid4()),
            dispute_id=dispute_id,
            ruling_body_id=ruling_body_id,
            outcome=outcome,
            reasoning=reasoning,
            penalties=penalties,
            precedent_created=precedent_created,
            final=final,
        )
        self.rulings[ruling.ruling_id] = ruling
        return ruling

    def apply_final_ruling_status(self, current_claim_status: str, ruling: Ruling) -> str:
        if not ruling.final:
            return current_claim_status
        return {
            "overturned": "overturned",
            "fraudulent": "fraudulent",
            "non_falsifiable": "non_falsifiable",
            "requires_more_evidence": "insufficient_evidence",
            "narrowed": "adversarially_reviewed",
            "upheld": current_claim_status,
        }.get(ruling.outcome, current_claim_status)
