from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from epistemic.disputes.ruling_service import Ruling


@dataclass(frozen=True)
class Precedent:
    precedent_id: str
    source_ruling_id: str
    summary: str
    binding_scope: str
    binding_level: str
    applies_to_policy_ids: list[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class InMemoryPrecedentService:
    def __init__(self) -> None:
        self.precedents: dict[str, Precedent] = {}

    def create_from_ruling(self, ruling: Ruling, *, summary: str, binding_scope: str, binding_level: str, applies_to_policy_ids: list[str] | None = None) -> Precedent:
        precedent = Precedent(
            precedent_id=str(uuid.uuid4()),
            source_ruling_id=ruling.ruling_id,
            summary=summary,
            binding_scope=binding_scope,
            binding_level=binding_level,
            applies_to_policy_ids=applies_to_policy_ids or [],
        )
        self.precedents[precedent.precedent_id] = precedent
        return precedent
