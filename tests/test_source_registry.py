"""
Tests for Source Registry (Phase 3).

Validates source registration, fingerprinting, derivation tracking,
and independence checks for resolution.
"""

import pytest
from datetime import datetime
from learning.universal.source_registry import (
    Source,
    SourceMedium,
    AccessLevel,
    SourceFingerprint,
    SourceRegistry,
)


class TestSourceRegistryBasics:
    """Test basic source registration."""

    def test_register_source(self):
        """Test registering a new source."""
        registry = SourceRegistry()

        source = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper.pdf",
            title="Important Paper",
            author="Jane Doe",
        )

        assert source.source_id
        assert source.source_medium == SourceMedium.PAPER
        assert source.source_uri == "http://example.com/paper.pdf"
        assert source.title == "Important Paper"
        assert source.author == "Jane Doe"

    def test_register_duplicate_returns_existing(self):
        """Test that registering same URI returns existing source."""
        registry = SourceRegistry()

        source1 = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper.pdf",
            title="Paper",
        )

        source2 = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper.pdf",
            title="Different Title",  # Should be ignored
        )

        assert source1.source_id == source2.source_id
        assert source2.title == "Paper"  # Original title preserved

    def test_get_source_by_id(self):
        """Test retrieving source by ID."""
        registry = SourceRegistry()

        source = registry.register_source(
            source_medium=SourceMedium.WEBPAGE,
            source_uri="http://example.com",
        )

        retrieved = registry.get_source(source.source_id)
        assert retrieved is not None
        assert retrieved.source_id == source.source_id

    def test_get_source_by_uri(self):
        """Test retrieving source by URI."""
        registry = SourceRegistry()

        source = registry.register_source(
            source_medium=SourceMedium.WEBPAGE,
            source_uri="http://example.com/page",
        )

        retrieved = registry.get_source_by_uri("http://example.com/page")
        assert retrieved is not None
        assert retrieved.source_id == source.source_id

    def test_get_nonexistent_source(self):
        """Test that nonexistent sources return None."""
        registry = SourceRegistry()

        assert registry.get_source("nonexistent_id") is None
        assert registry.get_source_by_uri("http://nonexistent.com") is None


class TestCanonicalURI:
    """Test URI canonicalization."""

    def test_canonicalize_removes_trailing_slash(self):
        """Test that trailing slashes are removed."""
        registry = SourceRegistry()

        canonical1 = registry.canonicalize_source_uri("http://example.com/")
        canonical2 = registry.canonicalize_source_uri("http://example.com")

        assert canonical1 == canonical2
        assert not canonical1.endswith("/")

    def test_canonicalize_removes_query_params(self):
        """Test that query parameters are removed."""
        registry = SourceRegistry()

        canonical = registry.canonicalize_source_uri(
            "http://example.com/page?tracking=123&utm_source=test"
        )

        assert canonical == "http://example.com/page"
        assert "?" not in canonical

    def test_canonicalize_removes_fragments(self):
        """Test that URL fragments are removed."""
        registry = SourceRegistry()

        canonical = registry.canonicalize_source_uri(
            "http://example.com/page#section-2"
        )

        assert canonical == "http://example.com/page"
        assert "#" not in canonical

    def test_canonicalize_same_source_with_tracking(self):
        """Test that sources with tracking params are detected as same."""
        registry = SourceRegistry()

        uri_with_tracking = "http://example.com/article?utm_source=twitter&utm_medium=social"
        uri_without_tracking = "http://example.com/article"

        canonical_with = registry.canonicalize_source_uri(uri_with_tracking)
        canonical_without = registry.canonicalize_source_uri(uri_without_tracking)

        assert canonical_with == canonical_without


class TestSourceFingerprinting:
    """Test source fingerprinting for equivalence detection."""

    def test_fingerprint_deterministic(self):
        """Test that fingerprints are deterministic."""
        registry = SourceRegistry()

        fp1 = registry.compute_source_fingerprint(
            source_uri="http://example.com/paper",
            content="This is the paper content",
            title="Paper",
            author="John",
        )

        fp2 = registry.compute_source_fingerprint(
            source_uri="http://example.com/paper",
            content="This is the paper content",
            title="Paper",
            author="John",
        )

        assert fp1.combined_fingerprint == fp2.combined_fingerprint

    def test_fingerprint_changes_with_content(self):
        """Test that fingerprint changes when content changes."""
        registry = SourceRegistry()

        fp1 = registry.compute_source_fingerprint(
            source_uri="http://example.com/paper",
            content="Content A",
        )

        fp2 = registry.compute_source_fingerprint(
            source_uri="http://example.com/paper",
            content="Content B",
        )

        assert fp1.combined_fingerprint != fp2.combined_fingerprint

    def test_fingerprint_matches(self):
        """Test fingerprint matching logic."""
        registry = SourceRegistry()

        fp1 = registry.compute_source_fingerprint(
            source_uri="http://example.com/paper",
            content="Same content",
        )

        fp2 = registry.compute_source_fingerprint(
            source_uri="http://example.com/paper",
            content="Same content",
        )

        assert fp1.matches(fp2)

    def test_fingerprint_no_match_different_content(self):
        """Test that different content produces non-matching fingerprints."""
        registry = SourceRegistry()

        fp1 = registry.compute_source_fingerprint(
            source_uri="http://example.com/paper",
            content="Content A",
        )

        fp2 = registry.compute_source_fingerprint(
            source_uri="http://example.com/paper",
            content="Content B",
        )

        assert not fp1.matches(fp2)


class TestSourceDerivation:
    """Test tracking source derivation and parent-child relationships."""

    def test_link_derived_source(self):
        """Test linking a derived source to its parent."""
        registry = SourceRegistry()

        parent = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/original",
            title="Original Paper",
        )

        derived = registry.register_source(
            source_medium=SourceMedium.PDF,
            source_uri="http://example.com/cached_copy",
            title="Cached Copy",
        )

        success = registry.link_derived_source(parent.source_id, derived.source_id)

        assert success

        # Check relationships
        parent_updated = registry.get_source(parent.source_id)
        derived_updated = registry.get_source(derived.source_id)

        assert derived.source_id in parent_updated.derived_from_source_ids
        assert parent.source_id in derived_updated.parent_source_ids

    def test_derived_source_not_independent(self):
        """Test that derived sources cannot be used for independent resolution."""
        registry = SourceRegistry()

        parent = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper",
        )

        derived = registry.register_source(
            source_medium=SourceMedium.PDF,
            source_uri="http://example.com/copy",
        )

        registry.link_derived_source(parent.source_id, derived.source_id)

        # Derived source cannot be used for independent resolution of the same claim
        derived_updated = registry.get_source(derived.source_id)
        can_use = derived_updated.can_be_used_for_independence(parent.source_id)

        assert not can_use

    def test_same_source_cannot_be_independent(self):
        """Test that same source cannot be used twice for independent resolution."""
        registry = SourceRegistry()

        source = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper",
        )

        # Source cannot be used for independent resolution of itself
        can_use = source.can_be_used_for_independence(source.source_id)

        assert not can_use

    def test_detect_derived_source(self):
        """Test detection of derived source relationship."""
        registry = SourceRegistry()

        parent = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper",
        )

        derived = registry.register_source(
            source_medium=SourceMedium.PDF,
            source_uri="http://example.com/copy",
        )

        registry.link_derived_source(parent.source_id, derived.source_id)

        # Detect relationship
        is_derived, reason = registry.detect_derived_source(
            parent.source_id, derived.source_id
        )

        assert is_derived
        assert reason is not None


class TestSampleDetection:
    """Test detection of equivalent sources."""

    def test_detect_same_source_by_id(self):
        """Test that same source ID is detected."""
        registry = SourceRegistry()

        source = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper",
        )

        is_same, reason = registry.detect_same_source(source.source_id, source.source_id)

        assert is_same
        assert reason == "Same source ID"

    def test_detect_same_canonical_uri(self):
        """Test detecting same source via canonical URI."""
        registry = SourceRegistry()

        source_a = registry.register_source(
            source_medium=SourceMedium.WEBPAGE,
            source_uri="http://example.com/article",
        )

        source_a.canonical_uri = "http://example.com/article"

        # Register another source with same canonical
        source_b = registry.register_source(
            source_medium=SourceMedium.WEBPAGE,
            source_uri="http://different-mirror.com/article",
        )

        source_b.canonical_uri = "http://example.com/article"

        is_same, reason = registry.detect_same_source(source_a.source_id, source_b.source_id)

        assert is_same
        assert "canonical" in reason.lower()

    def test_detect_different_sources(self):
        """Test that different sources are not marked as same."""
        registry = SourceRegistry()

        source_a = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper_a",
        )

        source_b = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper_b",
        )

        is_same, reason = registry.detect_same_source(source_a.source_id, source_b.source_id)

        assert not is_same


class TestSameLaunchCanonical:
    """Test canonical source detection."""

    def test_detect_same_canonical_source_with_tracking(self):
        """Test that sources with tracking params are detected as canonical same."""
        registry = SourceRegistry()

        uri_with_tracking = "http://example.com/article?utm_source=twitter"
        uri_without_tracking = "http://example.com/article"

        is_same = registry.detect_same_canonical_source(uri_with_tracking, uri_without_tracking)

        assert is_same

    def test_detect_different_canonical_sources(self):
        """Test that different articles are detected as different."""
        registry = SourceRegistry()

        is_same = registry.detect_same_canonical_source(
            "http://example.com/article_1",
            "http://example.com/article_2",
        )

        assert not is_same


class TestSerialization:
    """Test source serialization."""

    def test_source_to_dict_and_back(self):
        """Test source serialization round-trip."""
        source = Source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper",
            title="Test Paper",
            author="Test Author",
            access_level=AccessLevel.ACADEMIC,
        )

        data = source.to_dict()
        restored = Source.from_dict(data)

        assert restored.source_id == source.source_id
        assert restored.source_medium == source.source_medium
        assert restored.source_uri == source.source_uri
        assert restored.title == source.title
        assert restored.author == source.author
        assert restored.access_level == source.access_level

    def test_serialization_preserves_enums(self):
        """Test that enums are preserved through serialization."""
        source = Source(
            source_medium=SourceMedium.VIDEO,
            source_uri="http://youtube.com/video",
            access_level=AccessLevel.PUBLIC,
        )

        data = source.to_dict()
        restored = Source.from_dict(data)

        assert restored.source_medium == SourceMedium.VIDEO
        assert restored.access_level == AccessLevel.PUBLIC
        assert isinstance(restored.source_medium, SourceMedium)
        assert isinstance(restored.access_level, AccessLevel)


class TestProvenance:
    """Test provenance export."""

    def test_export_source_provenance(self):
        """Test exporting full provenance for a source."""
        registry = SourceRegistry()

        source = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/paper",
            title="Research Paper",
            author="John Doe",
        )

        provenance = registry.export_source_provenance(source.source_id)

        assert provenance["source_id"] == source.source_id
        assert provenance["source_uri"] == "http://example.com/paper"
        assert provenance["title"] == "Research Paper"
        assert provenance["author"] == "John Doe"
        assert "content_hash" in provenance
        assert "provenance_hash" in provenance

    def test_export_nonexistent_source_provenance(self):
        """Test that exporting nonexistent source returns empty dict."""
        registry = SourceRegistry()

        provenance = registry.export_source_provenance("nonexistent")

        assert provenance == {}


class TestIndependenceChecks:
    """Test independence checking for resolution."""

    def test_independence_direct_derivation_blocks_reuse(self):
        """Test that direct derivation blocks independence."""
        registry = SourceRegistry()

        # Create direct relationship: A -> B
        source_a = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/a",
        )

        source_b = registry.register_source(
            source_medium=SourceMedium.PDF,
            source_uri="http://example.com/b",
        )

        registry.link_derived_source(source_a.source_id, source_b.source_id)

        # B cannot be used for independent resolution of A (direct derivation)
        source_b_updated = registry.get_source(source_b.source_id)
        can_use = source_b_updated.can_be_used_for_independence(source_a.source_id)

        assert not can_use

    def test_unrelated_sources_can_be_independent(self):
        """Test that unrelated sources can be used for independent resolution."""
        registry = SourceRegistry()

        source_a = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/a",
        )

        source_b = registry.register_source(
            source_medium=SourceMedium.PAPER,
            source_uri="http://example.com/b",
        )

        # B can be used for independent resolution of A
        can_use = source_b.can_be_used_for_independence(source_a.source_id)

        assert can_use


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
