"""
Memory-Agent — Step 4 of the 6-hour learning loop.

After a human-approved TrainingProposal is applied, Memory-Agent:
- Updates the shared knowledge store with what was learned
- Records the cycle's outcomes for future Intelligence-Agent analysis
- Tags all new knowledge as "provisional" (NOT reality_validated)
- Updates the decay schedule for affected belief domains

INVARIANT: Memory-Agent cannot write reality_validated beliefs.
           Only ResolutionService can do that via pre-registered predictions.
           Memory-Agent writes provisional entries with explicit uncertainty.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    entry_id: str
    cycle_id: str
    content: str
    domain: str
    source: str             # "learning_loop_cycle"
    validation_status: str  # always "provisional" — never reality_validated
    confidence: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    human_approved_proposal_id: Optional[str] = None


class MemoryAgent(BaseAgentV2):

    AGENT_ID = "memory-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-haiku-4-5-20251001"   # high-frequency writes → Haiku
    DEPARTMENT = "learning"

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)
        self._memory_store: list[MemoryEntry] = []

    def run(self, task: dict) -> dict:
        action_type = task.get("action_type", "")
        if action_type == "store_cycle_outcomes":
            return self._store_cycle_outcomes(task)
        elif action_type == "retrieve":
            return self._retrieve(task)
        return {"status": "unknown_action"}

    def _store_cycle_outcomes(self, task: dict) -> dict:
        """
        Store outcomes from an approved training cycle.
        All entries are provisional — source of truth is the Calibration Engine.
        """
        cycle_id = task.get("cycle_id", "unknown")
        approved_changes = task.get("approved_changes", [])
        proposal_id = task.get("proposal_id")

        if not task.get("human_approved", False):
            return {
                "status": "blocked",
                "reason": "Memory writes from learning cycles require human_approved=True. "
                          "Unapproved proposals cannot update memory.",
            }

        entries_written = []
        for change in approved_changes:
            entry = MemoryEntry(
                entry_id=str(uuid.uuid4()),
                cycle_id=cycle_id,
                content=change.get("description", ""),
                domain=change.get("domain", "general"),
                source="learning_loop_cycle",
                validation_status="provisional",  # NEVER reality_validated
                confidence=change.get("confidence", 0.5),
                human_approved_proposal_id=proposal_id,
            )
            self._memory_store.append(entry)
            entries_written.append(entry.entry_id)
            logger.info(
                "MEMORY: stored provisional entry %s for cycle=%s domain=%s",
                entry.entry_id, cycle_id, entry.domain
            )

        action = AgentActionV2(
            action_type="write_memory",
            description=f"Write {len(entries_written)} provisional memory entries for cycle {cycle_id}",
            payload={
                "cycle_id": cycle_id,
                "entry_ids": entries_written,
                "validation_status": "provisional",
                "human_approved_proposal_id": proposal_id,
            },
            risk_level="medium",
            stated_confidence=0.85,
            domain="learning",
            claim_type="memory_update",
        )

        try:
            result = self.execute_action(action)
            return {
                "status": "memory_updated",
                "entries_written": len(entries_written),
                "validation_status": "provisional",
                "cycle_id": cycle_id,
            }
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id}

    def _retrieve(self, task: dict) -> dict:
        domain = task.get("domain")
        entries = self._memory_store
        if domain:
            entries = [e for e in entries if e.domain == domain]
        return {
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "content": e.content,
                    "domain": e.domain,
                    "validation_status": e.validation_status,
                    "confidence": e.confidence,
                    "created_at": e.created_at.isoformat(),
                }
                for e in entries
            ],
            "count": len(entries),
            "note": "All entries are provisional. validation_status=reality_validated is never set by Memory-Agent.",
        }
