"""
Civilization layer — Institution and Department domain models.

Exact fields per spec. reputation_score has NO setter; written only by the
Phase 5 propagation function in a transaction that also writes a memory event.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Institution:
    id: str
    name: str
    entity_type: str          # always 'institution'
    parent_id: Optional[str]  # must be None for institutions
    status: str               # 'active' | 'suspended' | 'retired'
    purpose: str
    authority_scope: list     # JSONB list of permitted action types
    _reputation_score: Optional[float]  # private; use reputation_score property
    metadata: dict
    created_at: datetime
    updated_at: datetime

    @property
    def reputation_score(self) -> Optional[float]:
        return self._reputation_score

    def __post_init__(self):
        if self.entity_type != "institution":
            raise ValueError("Institution.entity_type must be 'institution'")
        if self.parent_id is not None:
            raise ValueError("Institution.parent_id must be None")
        if self.status not in ("active", "suspended", "retired"):
            raise ValueError(f"Invalid status: {self.status}")


@dataclass
class Department:
    id: str
    name: str
    entity_type: str           # always 'department'
    parent_id: str             # NOT NULL — FK to institutions.id
    status: str                # 'active' | 'suspended' | 'retired'
    purpose: str
    authority_scope: list
    _reputation_score: Optional[float]
    metadata: dict
    created_at: datetime
    updated_at: datetime

    @property
    def reputation_score(self) -> Optional[float]:
        return self._reputation_score

    def __post_init__(self):
        if self.entity_type != "department":
            raise ValueError("Department.entity_type must be 'department'")
        if not self.parent_id:
            raise ValueError("Department.parent_id must be non-null")
        if self.status not in ("active", "suspended", "retired"):
            raise ValueError(f"Invalid status: {self.status}")


@dataclass
class AgentMembershipEdge:
    agent_id: str
    department_id: str
    role_name: str
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
