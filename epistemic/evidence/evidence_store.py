from __future__ import annotations

import hashlib
import json
import uuid

from epistemic.evidence.evidence_model import EvidenceRecord, EvidenceType


def compute_evidence_hash(payload: object) -> str:
    raw = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


class InMemoryEvidenceStore:
    def __init__(self) -> None:
        self._records: dict[str, EvidenceRecord] = {}

    def add_evidence(
        self,
        *,
        claim_id: str,
        evidence_type: EvidenceType,
        submitted_by: str,
        submitted_by_entity_type: str,
        evidence_payload: dict,
        source_uri: str | None = None,
        source_fingerprint: dict | None = None,
        admissibility_status: str = "submitted",
        strength_score: float | None = None,
    ) -> EvidenceRecord:
        record = EvidenceRecord(
            evidence_id=str(uuid.uuid4()),
            claim_id=claim_id,
            evidence_type=evidence_type,
            source_uri=source_uri,
            source_fingerprint=source_fingerprint,
            content_hash=compute_evidence_hash(evidence_payload),
            submitted_by=submitted_by,
            submitted_by_entity_type=submitted_by_entity_type,
            evidence_payload=evidence_payload,
            admissibility_status=admissibility_status,
            strength_score=strength_score,
        )
        self._records[record.evidence_id] = record
        return record

    def get_evidence_for_claim(self, claim_id: str) -> list[EvidenceRecord]:
        return [r for r in self._records.values() if r.claim_id == claim_id]

    def mark_admissibility(self, evidence_id: str, status: str) -> EvidenceRecord:
        old = self._records[evidence_id]
        new = EvidenceRecord(**{**old.__dict__, "admissibility_status": status})
        self._records[evidence_id] = new
        return new


def score_evidence_strength(record: EvidenceRecord) -> float:
    base = {
        "cryptographic_proof": 1.0,
        "test_result": 0.85,
        "ci_build_artifact": 0.85,
        "external_api_response": 0.8,
        "external_document": 0.7,
        "dataset_snapshot": 0.7,
        "human_expert_review": 0.65,
        "audit_log": 0.55,
        "agent_assertion": 0.1,
    }.get(record.evidence_type, 0.5)
    if record.admissibility_status != "admissible":
        return min(base, 0.25)
    return base
