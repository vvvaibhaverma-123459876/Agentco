from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

EvidenceType = Literal[
    "agent_assertion",
    "internal_memory",
    "audit_log",
    "ledger_row",
    "signed_event",
    "test_result",
    "ci_build_artifact",
    "dataset_snapshot",
    "external_document",
    "external_api_response",
    "human_expert_review",
    "sensor_record",
    "transaction_record",
    "cryptographic_proof",
    "market_outcome_data",
    "replication_result",
    "court_or_governance_ruling",
]


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    claim_id: str
    evidence_type: EvidenceType
    source_uri: str | None
    source_fingerprint: dict | None
    content_hash: str | None
    submitted_by: str
    submitted_by_entity_type: str
    evidence_payload: dict
    admissibility_status: str
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strength_score: float | None = None


EXTERNAL_EVIDENCE_TYPES = {
    "external_document",
    "external_api_response",
    "human_expert_review",
    "sensor_record",
    "transaction_record",
    "market_outcome_data",
    "replication_result",
}

MECHANICAL_EVIDENCE_TYPES = {
    "test_result",
    "ci_build_artifact",
    "cryptographic_proof",
}
