"""Universal Learning Layer - Learning from any medium with discipline."""

from .knowledge_claim import (
    KnowledgeClaim,
    ClaimType,
    ClaimStatus,
    EvidenceType,
    SourceLocation,
)

from .source_registry import (
    Source,
    SourceMedium,
    AccessLevel,
    SourceFingerprint,
    SourceRegistry,
)

from .adapters import (
    LearningAdapter,
    IngestionArtifact,
    TextAdapter,
    PDFAdapter,
    WebPageAdapter,
    VideoAdapter,
    AudioAdapter,
    CodeRepositoryAdapter,
    DatasetAdapter,
    HumanFeedbackAdapter,
    AdapterRegistry,
)

from .evidence_engine import EvidenceEngine, EvidenceClassification
from .curiosity_engine import CuriosityEngine, CuriositySignal
from .hypothesis_engine import HypothesisEngine, Hypothesis
from .experiment_lab import ExperimentLab, ExperimentResult
from .learning_memory import LearningMemoryService, MemoryRecord
from .cross_domain_synthesis import CrossDomainSynthesisEngine, CrossDomainTransfer
from .learning_institutions import LearningInstitutionService, LearningInstitution
from .learning_governance import LearningGovernanceService, PromotionProposal
from .learning_scorecard import LearningScorecard
from .learning_loop import (
    BoundedLearningLoop,
    LearningCycleTrace,
    TruthMaintenanceSystem,
    JudgmentEngine,
    EvidenceWeightingSystem,
    EpistemicSecurityModule,
    NormativeReasoningEngine,
    VerificationEconomyEngine,
    EpistemicPolity,
)

__all__ = [
    # Phase 2: Knowledge Claims
    "KnowledgeClaim",
    "ClaimType",
    "ClaimStatus",
    "EvidenceType",
    "SourceLocation",

    # Phase 3: Source Registry
    "Source",
    "SourceMedium",
    "AccessLevel",
    "SourceFingerprint",
    "SourceRegistry",

    # Phase 4: Adapters
    "LearningAdapter",
    "IngestionArtifact",
    "TextAdapter",
    "PDFAdapter",
    "WebPageAdapter",
    "VideoAdapter",
    "AudioAdapter",
    "CodeRepositoryAdapter",
    "DatasetAdapter",
    "HumanFeedbackAdapter",
    "AdapterRegistry",

    # Phase 5: Evidence Engine
    "EvidenceEngine",
    "EvidenceClassification",

    # Phase 6: Curiosity Engine
    "CuriosityEngine",
    "CuriositySignal",

    # Phase 7: Hypothesis Engine
    "HypothesisEngine",
    "Hypothesis",

    # Phase 8: Experiment Lab
    "ExperimentLab",
    "ExperimentResult",

    # Phase 9: Learning Memory
    "LearningMemoryService",
    "MemoryRecord",

    # Phase 10: Cross-Domain Synthesis
    "CrossDomainSynthesisEngine",
    "CrossDomainTransfer",

    # Phase 11: Learning Institutions
    "LearningInstitutionService",
    "LearningInstitution",

    # Phase 12: Learning Governance
    "LearningGovernanceService",
    "PromotionProposal",

    # Phase 13: Learning Scorecard
    "LearningScorecard",

    # Phases 14-24: Learning Loop & Resilience
    "BoundedLearningLoop",
    "LearningCycleTrace",
    "TruthMaintenanceSystem",
    "JudgmentEngine",
    "EvidenceWeightingSystem",
    "EpistemicSecurityModule",
    "NormativeReasoningEngine",
    "VerificationEconomyEngine",
    "EpistemicPolity",
]
