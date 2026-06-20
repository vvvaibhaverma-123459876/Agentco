# Knowledge Claim Model Specification

**Status:** Phase 1 Documentation  
**Date:** 2026-06-20

The Knowledge Claim is the canonical data structure for every learned fact in Agentco.

All adapters, enrichment engines, and institutional processes operate on this model.

---

## Core Model

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import hashlib
import uuid

class ClaimType(Enum):
    """Types of claims that can be extracted."""
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
    """Evidence tier that supports or contradicts a claim."""
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
    code_lines: Optional[tuple[int, int]] = None
    dataset_row_range: Optional[tuple[int, int]] = None
    url_fragment: Optional[str] = None

@dataclass
class KnowledgeClaim:
    """The canonical Knowledge Claim model."""
    
    # Identity
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Source Tracking
    source_id: str  # Reference to Source Registry entry
    source_medium: str  # text|pdf|book|paper|webpage|video|audio|slides|diagram|code_repo|dataset|simulation|human_feedback|benchmark|experiment
    source_uri: str  # URL, file path, or identifier
    source_location: SourceLocation = field(default_factory=SourceLocation)
    author_or_speaker: Optional[str] = None
    
    # Extraction Metadata
    extracted_by: str  # Agent or adapter name
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    extraction_method: str  # text_regex|pdf_parse|ocr_stub|video_transcript|audio_transcript|web_scrape|code_parse|schema_inference
    
    # Claim Content
    claim_text: str  # Raw extracted text from source
    normalized_claim: str  # Standardized, de-duplicate-friendly form
    claim_type: ClaimType  # From enum above
    domain: str  # science|engineering|business|law|history|ethics|etc
    subdomain: Optional[str] = None
    
    # Evidence Classification
    evidence_type: EvidenceType  # Classified automatically or by review
    confidence: float = 0.5  # 0.0–1.0 initial confidence
    uncertainty: Optional[float] = None  # Epistemic uncertainty, 0.0–1.0
    
    # Promotion & Status
    status: ClaimStatus = ClaimStatus.OBSERVED
    promotion_level: int = 0  # 0=Observed, 1=Parsed, ..., 9=Constitutionalized
    
    # Verification & Testing
    verification_required: bool = True
    testability: str  # high|medium|low|untestable
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
            self.content_hash = hashlib.sha256(self.claim_text.encode()).hexdigest()
        if not self.provenance_hash:
            prov_string = f"{self.source_id}:{self.source_uri}:{self.extraction_method}:{self.extracted_by}"
            self.provenance_hash = hashlib.sha256(prov_string.encode()).hexdigest()
    
    def can_promote_to(self, next_status: ClaimStatus) -> tuple[bool, Optional[str]]:
        """
        Check if promotion to next_status is allowed.
        Returns (allowed: bool, reason_if_blocked: str|None)
        """
        # Cannot promote without provenance
        if not self.provenance_hash:
            return False, "No provenance hash"
        
        # No skipping rungs
        current_rung = self.status.name
        next_rung = next_status.name
        rung_order = [
            "OBSERVED", "PARSED", "UNDERSTOOD", "HYPOTHESIZED", "SUPPORTED",
            "TESTED", "REPLICATED", "CALIBRATED", "INSTITUTIONALIZED", "CONSTITUTIONALIZED"
        ]
        
        if current_rung not in rung_order or next_rung not in rung_order:
            return True, None  # Allow special statuses (DISPUTED, REJECTED, ARCHIVED)
        
        current_idx = rung_order.index(current_rung)
        next_idx = rung_order.index(next_rung)
        
        if next_idx > current_idx + 1:
            return False, f"Cannot skip from {current_rung} to {next_rung}"
        
        # Lecture claims cannot jump to Institutionalized
        if self.evidence_type == EvidenceType.EXPERT_LECTURE and next_status == ClaimStatus.INSTITUTIONALIZED:
            if self.status != ClaimStatus.TESTED:
                return False, "Lecture claims must be TESTED before INSTITUTIONALIZED"
        
        # Analogy claims never become empirical facts
        if self.claim_type == ClaimType.ANALOGY and next_status in [
            ClaimStatus.CALIBRATED, ClaimStatus.INSTITUTIONALIZED
        ]:
            return False, "Analogy claims remain hypothesis; cannot be institutionalized"
        
        # High-risk requires adversarial review (checked at institutional level)
        # This method only checks structural rules
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage."""
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
        }
```

---

## Validation Rules

### Required Fields

Every KnowledgeClaim must have:

- `source_id`: Reference to registered source
- `source_uri`: Original location
- `source_medium`: Type of medium
- `claim_text`: Raw extracted claim
- `normalized_claim`: Standardized form
- `claim_type`: Semantic type
- `domain`: Subject area
- `evidence_type`: Classification of evidence
- `testability`: Assessable likelihood of resolution
- `extracted_by`: Who extracted it
- `extracted_at`: When extraction occurred

### Optional But Recommended

- `author_or_speaker`: Who created the original claim
- `resolution_criteria`: How to verify if testable
- `risk_level`: Consequence assessment
- `source_location`: Precise location in source

### Computed at Creation

- `claim_id`: UUID
- `content_hash`: SHA256(claim_text)
- `provenance_hash`: SHA256(source_id:source_uri:method:extractor)
- `created_at`: ISO timestamp
- `updated_at`: ISO timestamp

---

## Promotion Transition Rules

### Blocked Transitions (Enforce Mechanically)

| From Status | To Status | Blocked If | Reason |
|------------|-----------|-----------|--------|
| OBSERVED | INSTITUTIONALIZED | always | Cannot skip 7 rungs |
| OBSERVED | CALIBRATED | always | No evidence classification |
| * | * | no provenance_hash | Evidence chain broken |
| EXPERT_LECTURE | INSTITUTIONALIZED | status != TESTED | Lecture requires test before institution |
| ANALOGY | CALIBRATED | always | Analogy never becomes fact |
| ANALOGY | INSTITUTIONALIZED | always | Analogy never becomes fact |
| * | PROMOTION | linked_dispute_ids not empty | Cannot promote while disputed |
| * | INSTITUTIONALIZED | risk_level="high" AND not adversarially_reviewed | High-risk needs challenge |

### Status Meaning

| Status | Meaning | Who Sets | Authority | Can Skip? |
|--------|---------|----------|-----------|----------|
| OBSERVED | Extracted from source | Adapter | None | No |
| PARSED | Meaning extracted | Adapter/NLP | Low | No |
| UNDERSTOOD | Conceptual relationships mapped | Engine/Review | Low | No |
| HYPOTHESIZED | Testable form created | Hypothesis Engine | Medium | No |
| SUPPORTED | Supporting evidence found | Evidence Engine | Medium | No |
| TESTED | Sandbox/experiment result | Experiment Lab | Medium-High | No |
| REPLICATED | Independent confirmation | Replication Institution | Medium-High | No |
| CALIBRATED | Entered ledger; scored if resolved | Calibration System | High | No |
| INSTITUTIONALIZED | Institutional review passed | Institution Review | High | No |
| CONSTITUTIONALIZED | High-level governance approved | Civilization | Very High | No |
| DISPUTED | Contradiction or challenge filed | Any Institution | Special | N/A |
| REJECTED | Explicitly disconfirmed | Institution/Governance | High | N/A |
| ARCHIVED | Deprecated or low-value | Governance | Low | N/A |

---

## Known Limits

1. **Type Coverage:** `ClaimType` enum covers most cases but is not exhaustive. New types can be added; edge cases may need OPEN_QUESTION or OPINION.

2. **Testability Assessment:** Marked as string (high/medium/low/untestable) by adapter/engine. No formal decidability algorithm; heuristic assessment.

3. **Confidence Calibration:** Initial confidence is 0.5 (uninformed). Refined by evidence classification and experiment results. Prior to Calibrated status, confidence is exploratory.

4. **Risk Assessment:** Risk level (low/medium/high) is heuristic. Consequence-based classification by domain and claim type.

5. **Source Fingerprinting:** Provenance hash is deterministic but assumes stable extraction. If extraction method changes, hash may change even for same content.

---

## Integration Points

This model is used by:

- **Adapters (Phase 4):** Create KnowledgeClaim from ingested content
- **Evidence Engine (Phase 5):** Classify EvidenceType and update confidence
- **Curiosity Engine (Phase 6):** Score claims for learning value
- **Hypothesis Engine (Phase 7):** Convert Understood claims to Hypothesized
- **Experiment Lab (Phase 8):** Link to experiments, update status
- **Memory System (Phase 9):** Store and index claims
- **Promotion Workflow (Phase 12):** Check promotion eligibility
- **TMS (Phase 17):** Track justifications and dependencies
- **Judgment Engine (Phase 18):** Identity and contradiction verdicts
- **Resolution Independence (Phase 3):** Source independence checks
- **Governance Service:** Institutional promotion decisions
- **Calibration Ledger:** Linked predictions for testable claims

---

## Next: Phase 2 Implementation

Phase 2 will implement:

- Dataclass with all fields
- Serialization/deserialization
- `can_promote_to()` validation
- Status transition guards
- Provenance hashing
- Tests for invalid transitions
