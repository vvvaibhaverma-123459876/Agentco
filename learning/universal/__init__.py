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
]
