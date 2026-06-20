"""Value specification and norm clarification (Phase 6)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


@dataclass
class NormDefinition:
    """Norm specification."""
    norm_id: str
    norm_name: str
    definition: str
    governable: bool
    revisable: bool
    status: str  # 'draft', 'clarified', 'adopted'
    versions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ValueSpecificationCommittee:
    """Define and clarify normative terms."""

    def __init__(self):
        self.norms: dict[str, NormDefinition] = {}

    def define_norm(self, norm_name: str, definition: str, governable: bool = True, revisable: bool = True) -> NormDefinition:
        """
        Define a norm.

        Args:
            norm_name: Name of norm
            definition: Initial definition
            governable: Can be changed by governance
            revisable: Can be revised later

        Returns:
            NormDefinition
        """
        norm = NormDefinition(
            norm_id=str(uuid.uuid4()),
            norm_name=norm_name,
            definition=definition,
            governable=governable,
            revisable=revisable,
            status="draft",
            versions=[definition],
        )

        self.norms[norm.norm_id] = norm
        return norm

    def clarify_term(self, norm_id: str, stakeholder_feedback: str) -> NormDefinition:
        """
        Clarify a normative term.

        Args:
            norm_id: Norm ID
            stakeholder_feedback: Feedback from stakeholders

        Returns:
            Updated NormDefinition
        """
        if norm_id not in self.norms:
            return None

        norm = self.norms[norm_id]
        # Simplified: append feedback to definition
        norm.definition += f"\n[Clarification]: {stakeholder_feedback}"
        norm.versions.append(norm.definition)
        norm.status = "clarified"

        return norm

    def get_norm(self, norm_id: str) -> NormDefinition:
        """Get norm by ID."""
        return self.norms.get(norm_id)
