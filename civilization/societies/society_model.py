"""
Society Model — data structures for multi-institution societies.

A Society is a collection of institutions that agree on shared standards,
domain definitions, and resolution procedures.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class SocietyMembership:
    """Membership edge between society and institution."""
    society_id: str
    institution_id: str
    membership_status: str  # 'proposed', 'active', 'suspended', 'retired'
    role: str  # 'member', 'reviewer', 'lead', etc.
    joined_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class Society:
    """A multi-institution society with shared governance and reputation."""
    id: str
    name: str
    domain: str  # e.g., "engineering", "safety", "economics"
    purpose: str
    status: str  # 'active', 'suspended', 'retired'
    authority_scope: list  # JSON list of authority domains
    reputation_score: Optional[float] = None
    constitution_ref: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @staticmethod
    def create(
        name: str,
        domain: str,
        purpose: str,
        authority_scope: Optional[list] = None,
    ) -> Society:
        """Create a new society."""
        now = datetime.now(timezone.utc)
        return Society(
            id=str(uuid.uuid4()),
            name=name,
            domain=domain,
            purpose=purpose,
            status="active",
            authority_scope=authority_scope or [],
            reputation_score=0.0,
            metadata={},
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "purpose": self.purpose,
            "status": self.status,
            "authority_scope": self.authority_scope,
            "reputation_score": self.reputation_score,
            "constitution_ref": self.constitution_ref,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
