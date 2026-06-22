from __future__ import annotations

from calibration.evidence import EvidenceKernel
from ingestion.base import IngestedDocument
from ingestion.claim_extractor import ClaimExtractor
from ingestion.source_registry import SourceRegistry


class IngestionPipeline:
    def __init__(self, evidence_kernel: EvidenceKernel | None = None):
        self.evidence_kernel = evidence_kernel or EvidenceKernel()
        self.extractor = ClaimExtractor()
        self.sources = SourceRegistry()
        self.audit_events: list[dict] = []

    def ingest_document(self, document: IngestedDocument) -> dict:
        source = self.sources.register(document.source_uri, document.source_type)
        claims = [
            self.evidence_kernel.create_claim(
                claim_text,
                source_uri=source.source_uri,
                source_type=source.source_type,
            )
            for claim_text in self.extractor.extract(document)
        ]
        event = {
            "event_type": "ingestion.completed",
            "source_uri": source.source_uri,
            "claims_created": len(claims),
            "evidence_status": source.evidence_status,
            "extraction_method": document.extraction_method,
        }
        self.audit_events.append(event)
        return {"source": source, "claims": claims, "audit_event": event}
