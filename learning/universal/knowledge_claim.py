"""
Knowledge Claim Model — The canonical representation of learned facts.

Every extracted claim, hypothesis, and piece of learned knowledge
is represented as a KnowledgeClaim with full provenance tracking.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List, Tuple


class ClaimType(Enum):
    """Types of claims that can be extracted from sources."""

    DEFINITION = "definition"
    MATHEMATICAL_STATEMENT = "mathematical_statement"
    FORMAL_PROOF = "formal_proof"
    EMPIRICAL_CLAIM = "empirical_claim"
    CAUSAL_CLAIM = "causal_claim"
    STATISTICAL_CLAIM = "statistical_claim"
    BENCHMARK_CLAIM = "benchmark_claim"
    ENGINEERING_CLAIM = "engineering_claim"
    SCIENTIFIC_PRINCIPLE = "scientific_principle"
    HISTORICAL_CLAIM = "historical_claim"
    BUSINESS_CLAIM = "business_claim"
    LEGAL_POLICY_CLAIM = "legal_policy_claim"
    ETHICAL_CLAIM = "ethical_claim"
    ANALOGY = "analogy"
    OPINION = "opinion"
    PREDICTION = "prediction"
    INSTRUCTION = "instruction"
    PROCEDURE = "procedure"
    OPEN_QUESTION = "open_question"


class EvidenceType(Enum):
    """Evidence tier classification. Higher tier = stronger evidence."""

    FORMAL_PROOF = "formal_proof"
    RAW_DATASET = "raw_dataset"
    REPRODUCIBLE_CODE = "reproducible_code"
    BENCHMARK_RESULT = "benchmark_result"
    REPLICATED_PEER_REVIEWED_STUDY = "replicated_peer_reviewed_study"
    META_ANALYSIS = "meta_analysis"
    SYSTEMATIC_REVIEW = "systematic_review"
    SINGLE_PEER_REVIEWED_PAPER = "single_peer_reviewed_paper"
    PREPRINT = "preprint"
    EXPERT_LECTURE = "expert_lecture"
    TEXTBOOK = "textbook"
    PROFESSOR_NOTES = "professor_notes"
    BLOG_ARTICLE = "blog_article"
    FORUM_CLAIM = "forum_claim"
    HUMAN_FEEDBACK = "human_feedback"
    LLM_SUMMARY = "llm_summary"
    SIMULATION_RESULT = "simulation_result"
    EXPERIMENT_RESULT = "experiment_result"
    UNKNOWN = "unknown"


class ClaimStatus(Enum):
    """Promotion rung on the knowledge status ladder."""

    OBSERVED = "observed"
    PARSED = "parsed"
    UNDERSTOOD = "understood"
    HYPOTHESIZED = "hypothesized"
    SUPPORTED = "supported"
    TESTED = "tested"
    REPLICATED = "replicated"
    CALIBRATED = "calibrated"
    INSTITUTIONALIZED = "institutionalized"
    CONSTITUTIONALIZED = "constitutionalized"
    DISPUTED = "disputed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class SourceLocation:
    """Where in the source material this claim appears."""

    page: Optional[int] = None
    line: Optional[int] = None
    timestamp: Optional[str] = None  # HH:MM:SS for video/audio
    frame: Optional[int] = None
    slide: Optional[int] = None
    table: Optional[str] = None
    code_file: Optional[str] = None
    code_lines: Optional[Tuple[int, int]] = None
    dataset_row_range: Optional[Tuple[int, int]] = None
    url_fragment: Optional[str] = None


@dataclass
class KnowledgeClaim:
    """The canonical Knowledge Claim model."""

    # Source Tracking (required)
    source_id: str  # Reference to Source Registry entry
    source_medium: str  # text|pdf|book|paper|webpage|video|audio|slides|diagram|code_repo|dataset|simulation|human_feedback
    source_uri: str  # URL, file path, or identifier

    # Claim Content (required)
    claim_text: str  # Raw extracted text from source
    normalized_claim: str  # Standardized, de-duplicate-friendly form
    claim_type: ClaimType  # From enum above
    domain: str  # science|engineering|business|law|history|ethics|etc

    # Extraction Metadata (required)
    extracted_by: str  # Agent or adapter name
    evidence_type: EvidenceType  # Classified automatically or by review

    # Identity
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Source Location
    source_location: SourceLocation = field(default_factory=SourceLocation)
    author_or_speaker: Optional[str] = None

    # Extraction Timestamp
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    extraction_method: str = "unknown"  # text_regex|pdf_parse|ocr_stub|transcript|web_scrape|code_parse|schema_inference

    # Claim Properties (optional)
    subdomain: Optional[str] = None

    # Evidence & Confidence
    confidence: float = 0.5  # 0.0–1.0 initial confidence
    uncertainty: Optional[float] = None  # Epistemic uncertainty, 0.0–1.0

    # Promotion & Status
    status: ClaimStatus = ClaimStatus.OBSERVED
    promotion_level: int = 0  # 0=Observed, 1=Parsed, ..., 9=Constitutionalized

    # Verification & Testing
    verification_required: bool = True
    testability: str = "unknown"  # high|medium|low|untestable
    resolution_criteria: Optional[str] = None  # How to resolve if testable
    horizon: Optional[str] = None  # short|medium|long (for predictions)

    # Relationships
    supporting_sources: List[str] = field(default_factory=list)  # Source IDs
    contradicting_sources: List[str] = field(default_factory=list)  # Source IDs
    linked_prediction_id: Optional[str] = None  # Calibration ledger prediction_id
    linked_memory_ids: List[str] = field(default_factory=list)  # Learning memory IDs
    linked_institution_id: Optional[str] = None  # Institution that reviewed it
    linked_experiment_ids: List[str] = field(default_factory=list)  # Sandbox experiments
    linked_dispute_ids: List[str] = field(default_factory=list)  # Disputes

    # Hashing & Provenance
    content_hash: str = ""  # SHA256(source_content)
    provenance_hash: str = ""  # SHA256(source_id + source_uri + extraction_method + extracted_by)

    # Audit & Control
    risk_level: str = "low"  # low|medium|high (affects promotion speed)
    audit_trace_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Compute hashes and validate basic invariants."""
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.claim_text.encode()
            ).hexdigest()
        if not self.provenance_hash:
            prov_string = (
                f"{self.source_id}:{self.source_uri}:{self.extraction_method}:{self.extracted_by}"
            )
            self.provenance_hash = hashlib.sha256(prov_string.encode()).hexdigest()

    def can_promote_to(
        self, next_status: ClaimStatus
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if promotion to next_status is allowed.

        Returns: (allowed: bool, reason_if_blocked: str|None)
        """
        # Cannot promote without provenance
        if not self.provenance_hash:
            return False, "No provenance hash"

        # No skipping rungs in the standard ladder
        current_rung = self.status.name
        next_rung = next_status.name

        # Special statuses don't follow the ladder
        special_statuses = {"DISPUTED", "REJECTED", "ARCHIVED"}
        if current_rung in special_statuses or next_rung in special_statuses:
            return True, None  # Allow transitions to/from special statuses

        rung_order = [
            "OBSERVED",
            "PARSED",
            "UNDERSTOOD",
            "HYPOTHESIZED",
            "SUPPORTED",
            "TESTED",
            "REPLICATED",
            "CALIBRATED",
            "INSTITUTIONALIZED",
            "CONSTITUTIONALIZED",
        ]

        if current_rung not in rung_order or next_rung not in rung_order:
            return True, None  # Allow unknown statuses

        current_idx = rung_order.index(current_rung)
        next_idx = rung_order.index(next_rung)

        # Can only advance one rung or stay in place
        if next_idx > current_idx + 1:
            return False, f"Cannot skip from {current_rung} to {next_rung}"

        # Lecture claims cannot jump to Institutionalized
        if (
            self.evidence_type == EvidenceType.EXPERT_LECTURE
            and next_status == ClaimStatus.INSTITUTIONALIZED
        ):
            if self.status != ClaimStatus.TESTED:
                return (
                    False,
                    "Lecture claims must be TESTED before INSTITUTIONALIZED",
                )

        # Analogy claims never become institutionalized
        if (
            self.claim_type == ClaimType.ANALOGY
            and next_status
            in [ClaimStatus.CALIBRATED, ClaimStatus.INSTITUTIONALIZED]
        ):
            return (
                False,
                "Analogy claims remain hypothesis; cannot be institutionalized",
            )

        # High-risk requires adversarial review (checked at institutional level)
        # This method only checks structural rules

        return True, None

    def update_status(self, new_status: ClaimStatus, reason: Optional[str] = None) -> bool:
        """
        Attempt to update claim status.

        Returns True if successful, False if blocked.
        """
        allowed, reason_blocked = self.can_promote_to(new_status)
        if not allowed:
            raise ValueError(
                f"Cannot promote {self.claim_id} from {self.status} to {new_status}: {reason_blocked}"
            )

        self.status = new_status
        self.promotion_level = self._compute_promotion_level(new_status)
        self.updated_at = datetime.utcnow()
        return True

    @staticmethod
    def _compute_promotion_level(status: ClaimStatus) -> int:
        """Compute numeric promotion level from status."""
        level_map = {
            ClaimStatus.OBSERVED: 0,
            ClaimStatus.PARSED: 1,
            ClaimStatus.UNDERSTOOD: 2,
            ClaimStatus.HYPOTHESIZED: 3,
            ClaimStatus.SUPPORTED: 4,
            ClaimStatus.TESTED: 5,
            ClaimStatus.REPLICATED: 6,
            ClaimStatus.CALIBRATED: 7,
            ClaimStatus.INSTITUTIONALIZED: 8,
            ClaimStatus.CONSTITUTIONALIZED: 9,
        }
        return level_map.get(status, 0)

    def can_link_prediction(self, prediction_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a prediction ID can be linked to this claim.

        Predictions can only be linked after claim reaches HYPOTHESIZED or higher.
        """
        min_level = self._compute_promotion_level(ClaimStatus.HYPOTHESIZED)
        if self.promotion_level < min_level:
            return (
                False,
                f"Claim must be at least HYPOTHESIZED to link prediction. Currently {self.status}",
            )

        if self.linked_prediction_id is not None:
            return False, "Claim already linked to prediction"

        return True, None

    def link_prediction(self, prediction_id: str) -> bool:
        """Link a calibration ledger prediction to this claim."""
        allowed, reason = self.can_link_prediction(prediction_id)
        if not allowed:
            raise ValueError(f"Cannot link prediction: {reason}")

        self.linked_prediction_id = prediction_id
        self.updated_at = datetime.utcnow()
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "claim_id": self.claim_id,
            "source_id": self.source_id,
            "source_medium": self.source_medium,
            "source_uri": self.source_uri,
            "claim_text": self.claim_text,
            "normalized_claim": self.normalized_claim,
            "claim_type": self.claim_type.value,
            "status": self.status.value,
            "evidence_type": self.evidence_type.value,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "testability": self.testability,
            "resolution_criteria": self.resolution_criteria,
            "provenance_hash": self.provenance_hash,
            "content_hash": self.content_hash,
            "linked_prediction_id": self.linked_prediction_id,
            "linked_institution_id": self.linked_institution_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "promotion_level": self.promotion_level,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "extracted_by": self.extracted_by,
            "extracted_at": self.extracted_at.isoformat(),
            "author_or_speaker": self.author_or_speaker,
            "supporting_sources": self.supporting_sources,
            "contradicting_sources": self.contradicting_sources,
            "linked_memory_ids": self.linked_memory_ids,
            "linked_experiment_ids": self.linked_experiment_ids,
            "linked_dispute_ids": self.linked_dispute_ids,
            "risk_level": self.risk_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeClaim":
        """Deserialize from dictionary."""
        # Convert string enums back to enum types
        data["claim_type"] = ClaimType(data["claim_type"])
        data["status"] = ClaimStatus(data["status"])
        data["evidence_type"] = EvidenceType(data["evidence_type"])

        # Convert ISO timestamps back to datetime
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        data["extracted_at"] = datetime.fromisoformat(data["extracted_at"])

        # Reconstruct SourceLocation if present
        if "source_location" in data and isinstance(data["source_location"], dict):
            data["source_location"] = SourceLocation(**data["source_location"])

        return cls(**data)
