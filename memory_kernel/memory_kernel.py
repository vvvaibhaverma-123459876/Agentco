from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _hash(content: object) -> str:
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class MemoryEvent:
    memory_id: str
    principal_id: str
    memory_type: str
    content_hash: str
    provenance_ref: str
    content: dict
    created_at: str


@dataclass
class OperationalMemory:
    key: str
    value: dict
    supersedes: str | None = None


class MemoryKernel:
    def __init__(self):
        self.experiential: list[MemoryEvent] = []
        self.operational: dict[str, OperationalMemory] = {}

    def write_experience(self, principal_id: str, memory_type: str, content: dict, provenance_ref: str) -> MemoryEvent:
        if not provenance_ref:
            raise ValueError("trusted memory requires provenance_ref")
        event = MemoryEvent(
            memory_id=str(uuid.uuid4()),
            principal_id=principal_id,
            memory_type=memory_type,
            content_hash=_hash(content),
            provenance_ref=provenance_ref,
            content=content,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.experiential.append(event)
        return event

    def upsert_operational(self, key: str, value: dict) -> OperationalMemory:
        previous = self.operational.get(key)
        item = OperationalMemory(key=key, value=value, supersedes=previous.key if previous else None)
        self.operational[key] = item
        return item

    def retrieve(self, query: str) -> list[MemoryEvent]:
        needle = query.casefold()
        return [event for event in self.experiential if needle in json.dumps(event.content).casefold()]
