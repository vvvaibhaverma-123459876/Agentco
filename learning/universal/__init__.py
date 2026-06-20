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

__all__ = [
    "KnowledgeClaim",
    "ClaimType",
    "ClaimStatus",
    "EvidenceType",
    "SourceLocation",
    "Source",
    "SourceMedium",
    "AccessLevel",
    "SourceFingerprint",
    "SourceRegistry",
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
]
