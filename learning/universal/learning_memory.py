"""
Learning Memory System — Layered storage of learning traces.

Stores raw, semantic, episodic, procedural, and calibration memories.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid


@dataclass
class MemoryRecord:
    """A learning memory record."""

    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""  # Agent, institution, or system ID
    memory_type: str = ""  # raw|semantic|episodic|procedural|calibration|institutional|civilizational
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    linked_claim_ids: List[str] = field(default_factory=list)
    linked_experiment_ids: List[str] = field(default_factory=list)
    linked_institution_id: Optional[str] = None
    confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"  # active|archived|deprecated


class LearningMemoryService:
    """Service for storing and retrieving learning memories."""

    def __init__(self):
        """Initialize memory store."""
        self.memories: Dict[str, MemoryRecord] = {}
        self.entity_index: Dict[str, List[str]] = {}  # entity_id -> memory_ids
        self.type_index: Dict[str, List[str]] = {}  # memory_type -> memory_ids

    def store_memory(
        self,
        entity_id: str,
        memory_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecord:
        """Store a new memory record."""
        record = MemoryRecord(
            entity_id=entity_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
        )

        self.memories[record.memory_id] = record

        # Update indices
        if entity_id not in self.entity_index:
            self.entity_index[entity_id] = []
        self.entity_index[entity_id].append(record.memory_id)

        if memory_type not in self.type_index:
            self.type_index[memory_type] = []
        self.type_index[memory_type].append(record.memory_id)

        return record

    def retrieve_memory(
        self,
        entity_id: str,
        memory_type: Optional[str] = None,
        query_filters: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryRecord]:
        """Retrieve memory records."""
        memory_ids = self.entity_index.get(entity_id, [])

        if memory_type:
            type_ids = self.type_index.get(memory_type, [])
            memory_ids = [mid for mid in memory_ids if mid in type_ids]

        records = [self.memories[mid] for mid in memory_ids if mid in self.memories]

        # Update accessed_at
        for record in records:
            record.accessed_at = datetime.utcnow()

        return records

    def link_memory_to_claim(self, memory_id: str, claim_id: str) -> bool:
        """Link a memory record to a claim."""
        if memory_id not in self.memories:
            return False

        if claim_id not in self.memories[memory_id].linked_claim_ids:
            self.memories[memory_id].linked_claim_ids.append(claim_id)

        return True

    def extract_lesson_from_pattern(
        self, entity_id: str, pattern_description: str
    ) -> Optional[MemoryRecord]:
        """Extract a lesson from repeated patterns."""
        memories = self.retrieve_memory(entity_id, memory_type="episodic")

        if len(memories) >= 3:  # Threshold for pattern
            lesson = self.store_memory(
                entity_id=entity_id,
                memory_type="procedural",
                content=f"Lesson: {pattern_description}",
                metadata={"derived_from_memories": len(memories)},
            )
            return lesson

        return None
