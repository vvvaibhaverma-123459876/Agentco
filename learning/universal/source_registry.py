"""
Universal Source Registry — Central registry for all ingested sources.

Every source used in learning (text, PDF, paper, website, video, etc.)
must be registered with full provenance tracking.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class SourceMedium(Enum):
    """Types of source media that can be learned from."""

    TEXT = "text"
    PDF = "pdf"
    BOOK = "book"
    PAPER = "paper"
    WEBPAGE = "webpage"
    VIDEO = "video"
    AUDIO = "audio"
    SLIDES = "slides"
    DIAGRAM = "diagram"
    CODE_REPO = "code_repo"
    DATASET = "dataset"
    SIMULATION = "simulation"
    HUMAN_FEEDBACK = "human_feedback"
    BENCHMARK = "benchmark"
    EXPERIMENT = "experiment"
    UNKNOWN = "unknown"


class AccessLevel(Enum):
    """Access requirements for source."""

    PUBLIC = "public"
    ACADEMIC = "academic"
    SUBSCRIPTION = "subscription"
    PROPRIETARY = "proprietary"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


@dataclass
class SourceFingerprint:
    """Fingerprint to detect equivalent sources."""

    # Canonical identifier
    canonical_uri: str

    # Content-based fingerprint
    content_hash: str  # SHA256 of primary content

    # Metadata-based fingerprint
    metadata_hash: str  # SHA256 of title + author + publication_date

    # Access point fingerprint
    uri_hash: str  # SHA256 of normalized URI(s)

    # Combined fingerprint
    combined_fingerprint: str  # SHA256 of all above

    def matches(self, other: "SourceFingerprint") -> bool:
        """Check if two fingerprints refer to the same source."""
        # Same source if combined fingerprints match (most reliable)
        if self.combined_fingerprint == other.combined_fingerprint:
            return True

        # Same source if content hashes match (exact duplicate)
        if self.content_hash and other.content_hash:
            if self.content_hash == other.content_hash:
                return True

        return False


@dataclass
class Source:
    """A source of learned knowledge."""

    # Type & Location (required)
    source_medium: SourceMedium  # Type of media
    source_uri: str  # Primary URI (URL, file path, or identifier)

    # Identity
    source_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Location & Path (optional)
    local_path: Optional[str] = None  # Local cached copy if applicable

    # Metadata (optional)
    title: Optional[str] = None
    author: Optional[str] = None
    speaker: Optional[str] = None
    publisher: Optional[str] = None
    institution: Optional[str] = None
    publication_date: Optional[datetime] = None

    # Ingestion Tracking
    ingestion_date: datetime = field(default_factory=datetime.utcnow)
    ingestion_agent: str = "unknown"

    # Access & Licensing
    access_level: AccessLevel = AccessLevel.UNKNOWN
    license_info: Optional[str] = None

    # Content Hash
    content_hash: str = ""  # SHA256 of source content if available

    # Provenance
    provenance_hash: str = ""  # SHA256 of source tracking data
    source_fingerprint: Optional[SourceFingerprint] = None

    # Derivation Tracking
    parent_source_ids: List[str] = field(default_factory=list)  # Sources this derives from
    derived_from_source_ids: List[str] = field(
        default_factory=list
    )  # Sources derived from this one
    canonical_uri: str = ""  # If this is derivative, what's the canonical version?

    # Classification
    domain: Optional[str] = None
    trust_tier: str = "unknown"  # low|medium|high|verified (how trustworthy?)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Audit
    audit_trace_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Compute hashes and validate."""
        if not self.provenance_hash:
            prov_string = f"{self.source_id}:{self.source_uri}:{self.source_medium.value}"
            self.provenance_hash = hashlib.sha256(prov_string.encode()).hexdigest()

    def is_derivative(self) -> bool:
        """Check if this source is derived from another."""
        return len(self.parent_source_ids) > 0

    def can_be_used_for_independence(self, original_source_id: str) -> bool:
        """
        Check if this source can be used for independent resolution.

        Returns False if:
        - This source is derived from the original
        - This source has circular dependency with original
        - This source is the same as original
        """
        # Cannot use same source twice
        if self.source_id == original_source_id:
            return False

        # Cannot use if derived from original
        if original_source_id in self.parent_source_ids:
            return False

        # Cannot use if original is in our derivation chain
        if original_source_id in self._get_all_ancestors():
            return False

        return True

    def _get_all_ancestors(self) -> Set[str]:
        """Get all sources in the ancestry chain."""
        ancestors: Set[str] = set(self.parent_source_ids)
        # Note: In real implementation, would recursively fetch parent sources
        # For now, just return direct parents
        return ancestors

    def add_derived_source(self, derived_source_id: str) -> None:
        """Record that another source is derived from this one."""
        if derived_source_id not in self.derived_from_source_ids:
            self.derived_from_source_ids.append(derived_source_id)
            self.updated_at = datetime.utcnow()

    def add_parent_source(self, parent_source_id: str) -> None:
        """Record parent source in derivation chain."""
        if parent_source_id not in self.parent_source_ids:
            self.parent_source_ids.append(parent_source_id)
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_id": self.source_id,
            "source_medium": self.source_medium.value,
            "source_uri": self.source_uri,
            "local_path": self.local_path,
            "title": self.title,
            "author": self.author,
            "speaker": self.speaker,
            "publisher": self.publisher,
            "institution": self.institution,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "ingestion_date": self.ingestion_date.isoformat(),
            "access_level": self.access_level.value,
            "license_info": self.license_info,
            "content_hash": self.content_hash,
            "provenance_hash": self.provenance_hash,
            "parent_source_ids": self.parent_source_ids,
            "derived_from_source_ids": self.derived_from_source_ids,
            "canonical_uri": self.canonical_uri,
            "domain": self.domain,
            "trust_tier": self.trust_tier,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Source":
        """Deserialize from dictionary."""
        data["source_medium"] = SourceMedium(data["source_medium"])
        data["access_level"] = AccessLevel(data["access_level"])

        # Convert ISO timestamps
        if data.get("publication_date"):
            data["publication_date"] = datetime.fromisoformat(data["publication_date"])
        if data.get("ingestion_date"):
            data["ingestion_date"] = datetime.fromisoformat(data["ingestion_date"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return cls(**data)


class SourceRegistry:
    """Central registry for all learned sources."""

    def __init__(self):
        """Initialize empty registry."""
        self.sources: Dict[str, Source] = {}
        self.uri_to_source_id: Dict[str, str] = {}  # URI index
        self.fingerprint_to_source_ids: Dict[str, List[str]] = {}  # Fingerprint index

    def register_source(
        self,
        source_medium: SourceMedium,
        source_uri: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        content_hash: Optional[str] = None,
        **kwargs,
    ) -> Source:
        """
        Register a new source or return existing if already registered.

        Returns: Source object (new or existing)
        """
        # Check if source already registered by URI
        existing_id = self.uri_to_source_id.get(source_uri)
        if existing_id and existing_id in self.sources:
            return self.sources[existing_id]

        # Create new source
        source = Source(
            source_medium=source_medium,
            source_uri=source_uri,
            title=title,
            author=author,
            content_hash=content_hash or "",
            **kwargs,
        )

        # Store in registry
        self.sources[source.source_id] = source
        self.uri_to_source_id[source_uri] = source.source_id

        # Index by fingerprint if available
        if source.source_fingerprint:
            fp_key = source.source_fingerprint.combined_fingerprint
            if fp_key not in self.fingerprint_to_source_ids:
                self.fingerprint_to_source_ids[fp_key] = []
            self.fingerprint_to_source_ids[fp_key].append(source.source_id)

        return source

    def get_source(self, source_id: str) -> Optional[Source]:
        """Retrieve a source by ID."""
        return self.sources.get(source_id)

    def get_source_by_uri(self, source_uri: str) -> Optional[Source]:
        """Retrieve a source by URI."""
        source_id = self.uri_to_source_id.get(source_uri)
        if source_id:
            return self.sources.get(source_id)
        return None

    def canonicalize_source_uri(self, source_uri: str) -> str:
        """
        Get the canonical URI for a source.

        Handles URL normalization, shorteners, redirects, etc.
        """
        # Basic normalization
        canonical = source_uri.strip()

        # Remove trailing slashes from URLs
        if canonical.startswith("http"):
            canonical = canonical.rstrip("/")

        # Remove query parameters (except for data URIs)
        if "?" in canonical and not canonical.startswith("data:"):
            canonical = canonical.split("?")[0]

        # Remove fragment identifiers
        if "#" in canonical and not canonical.startswith("data:"):
            canonical = canonical.split("#")[0]

        return canonical

    def compute_source_fingerprint(
        self, source_uri: str, content: Optional[str] = None, title: Optional[str] = None, author: Optional[str] = None, publication_date: Optional[datetime] = None
    ) -> SourceFingerprint:
        """
        Compute a fingerprint for source equivalence detection.

        Returns a SourceFingerprint with multiple hashing strategies.
        """
        canonical_uri = self.canonicalize_source_uri(source_uri)

        # Content hash
        content_hash = (
            hashlib.sha256(content.encode()).hexdigest() if content else ""
        )

        # Metadata hash
        metadata_string = f"{title or ''}:{author or ''}:{publication_date or ''}"
        metadata_hash = hashlib.sha256(metadata_string.encode()).hexdigest()

        # URI hash
        uri_hash = hashlib.sha256(canonical_uri.encode()).hexdigest()

        # Combined fingerprint
        combined_string = f"{content_hash}:{metadata_hash}:{uri_hash}"
        combined_fingerprint = hashlib.sha256(combined_string.encode()).hexdigest()

        return SourceFingerprint(
            canonical_uri=canonical_uri,
            content_hash=content_hash,
            metadata_hash=metadata_hash,
            uri_hash=uri_hash,
            combined_fingerprint=combined_fingerprint,
        )

    def detect_same_source(
        self,
        source_id_a: str,
        source_id_b: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if two sources are the same.

        Returns: (is_same: bool, reason: str|None)
        """
        source_a = self.get_source(source_id_a)
        source_b = self.get_source(source_id_b)

        if not source_a or not source_b:
            return False, "One or both sources not found"

        if source_a.source_id == source_b.source_id:
            return True, "Same source ID"

        # Check canonical URIs
        if source_a.canonical_uri and source_b.canonical_uri:
            if source_a.canonical_uri == source_b.canonical_uri:
                return True, "Same canonical URI"

        # Check fingerprints
        if source_a.source_fingerprint and source_b.source_fingerprint:
            if source_a.source_fingerprint.matches(source_b.source_fingerprint):
                return True, "Fingerprints match"

        # Check content hashes
        if source_a.content_hash and source_b.content_hash:
            if source_a.content_hash == source_b.content_hash:
                return True, "Content hashes match"

        return False, None

    def detect_same_canonical_source(
        self,
        uri_a: str,
        uri_b: str,
    ) -> bool:
        """
        Check if two URIs refer to the same canonical source.

        Handles URL normalization, tracking parameters, etc.
        """
        canonical_a = self.canonicalize_source_uri(uri_a)
        canonical_b = self.canonicalize_source_uri(uri_b)
        return canonical_a == canonical_b

    def detect_derived_source(
        self,
        source_a_id: str,
        source_b_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if source B is derived from source A.

        Returns: (is_derived: bool, relationship: str|None)
        """
        source_a = self.get_source(source_a_id)
        source_b = self.get_source(source_b_id)

        if not source_a or not source_b:
            return False, None

        # Check if B explicitly lists A as parent
        if source_a_id in source_b.parent_source_ids:
            return True, "Explicit parent relationship"

        # Check if A lists B as derived
        if source_b_id in source_a.derived_from_source_ids:
            return True, "Explicit derivation relationship"

        # Could add heuristic detection here (similar titles, time-ordered, etc.)

        return False, None

    def link_derived_source(
        self,
        parent_source_id: str,
        derived_source_id: str,
    ) -> bool:
        """
        Record that a source is derived from another.

        Establishes the parent-child relationship in derivation chain.
        """
        parent = self.get_source(parent_source_id)
        derived = self.get_source(derived_source_id)

        if not parent or not derived:
            return False

        parent.add_derived_source(derived_source_id)
        derived.add_parent_source(parent_source_id)

        return True

    def export_source_provenance(self, source_id: str) -> Dict[str, Any]:
        """
        Export full provenance chain for a source.

        Includes: canonical URI, content hash, derivation chain, metadata
        """
        source = self.get_source(source_id)
        if not source:
            return {}

        return {
            "source_id": source.source_id,
            "source_uri": source.source_uri,
            "canonical_uri": source.canonical_uri,
            "source_medium": source.source_medium.value,
            "content_hash": source.content_hash,
            "provenance_hash": source.provenance_hash,
            "parent_source_ids": source.parent_source_ids,
            "derived_from_source_ids": source.derived_from_source_ids,
            "title": source.title,
            "author": source.author,
            "publication_date": source.publication_date.isoformat() if source.publication_date else None,
            "ingestion_date": source.ingestion_date.isoformat(),
            "access_level": source.access_level.value,
            "trust_tier": source.trust_tier,
        }
