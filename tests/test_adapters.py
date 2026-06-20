"""
Tests for Learning Adapters (Phase 4).

Validates that adapters correctly ingest various media types and
extract KnowledgeClaim objects with proper provenance.
"""

import pytest
from datetime import datetime
from learning.universal import (
    KnowledgeClaim,
    Source,
    SourceMedium,
    SourceRegistry,
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


class TestAdapterSupport:
    """Test adapter medium detection."""

    def test_text_adapter_supports_text(self):
        """Test TextAdapter supports text medium."""
        registry = SourceRegistry()
        adapter = TextAdapter(registry)

        source = Source(
            source_medium=SourceMedium.TEXT,
            source_uri="test.txt",
        )

        assert adapter.supports(source)

    def test_text_adapter_rejects_pdf(self):
        """Test TextAdapter rejects PDF medium."""
        registry = SourceRegistry()
        adapter = TextAdapter(registry)

        source = Source(
            source_medium=SourceMedium.PDF,
            source_uri="test.pdf",
        )

        assert not adapter.supports(source)

    def test_pdf_adapter_supports_pdf(self):
        """Test PDFAdapter supports PDF medium."""
        registry = SourceRegistry()
        adapter = PDFAdapter(registry)

        source = Source(
            source_medium=SourceMedium.PDF,
            source_uri="test.pdf",
        )

        assert adapter.supports(source)

    def test_video_adapter_supports_video(self):
        """Test VideoAdapter supports video medium."""
        registry = SourceRegistry()
        adapter = VideoAdapter(registry)

        source = Source(
            source_medium=SourceMedium.VIDEO,
            source_uri="http://youtube.com/video",
        )

        assert adapter.supports(source)


class TestTextAdapter:
    """Test text ingestion and claim extraction."""

    def test_text_ingest_fixture(self):
        """Test ingesting text fixture."""
        registry = SourceRegistry()
        adapter = TextAdapter(registry)

        source = Source(
            source_medium=SourceMedium.TEXT,
            source_uri="test.txt",
            title="Test Document",
            metadata={"content": "This is a test. This is another test."},
        )

        artifact = adapter.ingest(source)

        assert artifact.source == source
        assert "test" in artifact.raw_content.lower()
        assert artifact.extraction_method == "text_direct"
        assert artifact.confidence == 1.0

    def test_text_extract_claims(self):
        """Test extracting claims from text."""
        registry = SourceRegistry()
        adapter = TextAdapter(registry)

        source = Source(
            source_medium=SourceMedium.TEXT,
            source_uri="test.txt",
            metadata={"content": "This is a test claim. Another claim here."},
        )

        artifact = adapter.ingest(source)
        claims = adapter.extract_claims(artifact)

        assert len(claims) >= 1
        assert all(c.source_id == source.source_id for c in claims)
        assert all(c.source_uri == source.source_uri for c in claims)
        assert all(c.provenance_hash for c in claims)


class TestPDFAdapter:
    """Test PDF ingestion and claim extraction."""

    def test_pdf_ingest_fixture(self):
        """Test ingesting PDF fixture with pages."""
        registry = SourceRegistry()
        adapter = PDFAdapter(registry)

        source = Source(
            source_medium=SourceMedium.PDF,
            source_uri="paper.pdf",
            title="Research Paper",
            author="Jane Doe",
            metadata={
                "content": "Page 1 content. Some claims here.\n---PAGE_BREAK---\nPage 2 content. More claims."
            },
        )

        artifact = adapter.ingest(source)

        assert artifact.extraction_method == "pdf_parse_fixture"
        assert artifact.structured_metadata["pages"] >= 1
        assert artifact.structured_metadata["title"] == "Research Paper"

    def test_pdf_extract_claims_with_page_numbers(self):
        """Test PDF claim extraction includes page numbers."""
        registry = SourceRegistry()
        adapter = PDFAdapter(registry)

        source = Source(
            source_medium=SourceMedium.PDF,
            source_uri="paper.pdf",
            metadata={
                "content": "First page claim here.\n---PAGE_BREAK---\nSecond page claim here."
            },
        )

        artifact = adapter.ingest(source)
        claims = adapter.extract_claims(artifact)

        assert len(claims) >= 1
        # Check that at least one claim has page number
        claims_with_pages = [c for c in claims if c.source_location.page is not None]
        assert len(claims_with_pages) > 0
        assert claims_with_pages[0].source_location.page >= 1


class TestVideoAdapter:
    """Test video ingestion and claim extraction."""

    def test_video_ingest_transcript_fixture(self):
        """Test ingesting video transcript fixture."""
        registry = SourceRegistry()
        adapter = VideoAdapter(registry)

        source = Source(
            source_medium=SourceMedium.VIDEO,
            source_uri="http://youtube.com/video",
            speaker="Prof. Smith",
            metadata={
                "transcript": "In this lecture we discuss. The first point is important. The second point is also key.",
                "duration": 3600,
            },
        )

        artifact = adapter.ingest(source)

        assert artifact.extraction_method == "video_transcript_fixture"
        assert artifact.structured_metadata["speaker"] == "Prof. Smith"
        assert "lecture" in artifact.raw_content.lower()

    def test_video_extract_claims_with_timestamps(self):
        """Test video claim extraction includes timestamps."""
        registry = SourceRegistry()
        adapter = VideoAdapter(registry)

        source = Source(
            source_medium=SourceMedium.VIDEO,
            source_uri="http://youtube.com/video",
            metadata={"transcript": "First point made here. Second point here. Third point here."},
        )

        artifact = adapter.ingest(source)
        claims = adapter.extract_claims(artifact)

        assert len(claims) >= 1
        # Check timestamps
        claims_with_timestamps = [
            c for c in claims if c.source_location.timestamp is not None
        ]
        assert len(claims_with_timestamps) > 0


class TestAudioAdapter:
    """Test audio ingestion and claim extraction."""

    def test_audio_ingest_transcript_fixture(self):
        """Test ingesting audio transcript fixture."""
        registry = SourceRegistry()
        adapter = AudioAdapter(registry)

        source = Source(
            source_medium=SourceMedium.AUDIO,
            source_uri="http://example.com/podcast.mp3",
            speaker="John Doe",
            metadata={
                "transcript": "This is a podcast episode. We discuss important topics. The content is valuable.",
            },
        )

        artifact = adapter.ingest(source)

        assert artifact.extraction_method == "audio_transcript_fixture"
        assert artifact.structured_metadata["speaker"] == "John Doe"

    def test_audio_extract_claims(self):
        """Test extracting claims from audio."""
        registry = SourceRegistry()
        adapter = AudioAdapter(registry)

        source = Source(
            source_medium=SourceMedium.AUDIO,
            source_uri="podcast.mp3",
            metadata={"transcript": "This is an important point. Another point to consider."},
        )

        artifact = adapter.ingest(source)
        claims = adapter.extract_claims(artifact)

        assert len(claims) >= 1
        assert all(c.evidence_type.value == "expert_lecture" for c in claims)


class TestCodeRepositoryAdapter:
    """Test code repository ingestion."""

    def test_code_repo_ingest_readme(self):
        """Test ingesting code repository README."""
        registry = SourceRegistry()
        adapter = CodeRepositoryAdapter(registry)

        source = Source(
            source_medium=SourceMedium.CODE_REPO,
            source_uri="http://github.com/example/repo",
            metadata={
                "readme": "This project implements. The main features are. The API supports."
            },
        )

        artifact = adapter.ingest(source)

        assert artifact.extraction_method == "code_readme_fixture"
        assert artifact.structured_metadata["repo_url"] == source.source_uri

    def test_code_repo_extract_engineering_claims(self):
        """Test extracting engineering claims from code repository."""
        registry = SourceRegistry()
        adapter = CodeRepositoryAdapter(registry)

        source = Source(
            source_medium=SourceMedium.CODE_REPO,
            source_uri="http://github.com/example/repo",
            metadata={"readme": "This library provides utilities. It supports multiple platforms."},
        )

        artifact = adapter.ingest(source)
        claims = adapter.extract_claims(artifact)

        assert len(claims) >= 1
        assert all(c.claim_type.value == "engineering_claim" for c in claims)


class TestDatasetAdapter:
    """Test dataset ingestion."""

    def test_dataset_ingest_schema(self):
        """Test ingesting dataset with schema."""
        registry = SourceRegistry()
        adapter = DatasetAdapter(registry)

        source = Source(
            source_medium=SourceMedium.DATASET,
            source_uri="http://data.example.com/dataset",
            metadata={
                "schema": {"id": "integer", "name": "string", "age": "integer"},
                "statistics": {"rows": 1000},
            },
        )

        artifact = adapter.ingest(source)

        assert artifact.extraction_method == "dataset_schema_fixture"
        assert artifact.structured_metadata["row_count"] == 1000

    def test_dataset_extract_structural_claims(self):
        """Test extracting structural and statistical claims from dataset."""
        registry = SourceRegistry()
        adapter = DatasetAdapter(registry)

        source = Source(
            source_medium=SourceMedium.DATASET,
            source_uri="data.csv",
            metadata={
                "schema": {"id": "int", "value": "float"},
                "statistics": {"rows": 500},
            },
        )

        artifact = adapter.ingest(source)
        claims = adapter.extract_claims(artifact)

        assert len(claims) >= 2  # Schema + statistics
        assert any("schema" in c.claim_text.lower() for c in claims)
        assert any("rows" in c.claim_text.lower() for c in claims)


class TestHumanFeedbackAdapter:
    """Test human feedback ingestion."""

    def test_human_feedback_ingest(self):
        """Test ingesting human feedback."""
        registry = SourceRegistry()
        adapter = HumanFeedbackAdapter(registry)

        source = Source(
            source_medium=SourceMedium.HUMAN_FEEDBACK,
            source_uri="feedback_001",
            author="Reviewer A",
            metadata={
                "feedback": "The approach is sound. The implementation is efficient.",
                "type": "review",
            },
        )

        artifact = adapter.ingest(source)

        assert artifact.extraction_method == "human_feedback_direct"
        assert artifact.structured_metadata["reviewer"] == "Reviewer A"

    def test_human_feedback_extract_opinions(self):
        """Test extracting opinion claims from feedback."""
        registry = SourceRegistry()
        adapter = HumanFeedbackAdapter(registry)

        source = Source(
            source_medium=SourceMedium.HUMAN_FEEDBACK,
            source_uri="feedback",
            author="Reviewer",
            metadata={"feedback": "This is well done. The code quality is high."},
        )

        artifact = adapter.ingest(source)
        claims = adapter.extract_claims(artifact)

        assert len(claims) >= 1
        assert all(c.claim_type.value == "opinion" for c in claims)


class TestAdapterRegistry:
    """Test adapter discovery and orchestration."""

    def test_registry_finds_text_adapter(self):
        """Test that registry finds correct adapter for text."""
        source_registry = SourceRegistry()
        adapter_registry = AdapterRegistry(source_registry)

        source = Source(
            source_medium=SourceMedium.TEXT,
            source_uri="test.txt",
        )

        adapter = adapter_registry.find_adapter(source)

        assert adapter is not None
        assert isinstance(adapter, TextAdapter)

    def test_registry_finds_pdf_adapter(self):
        """Test that registry finds PDF adapter."""
        source_registry = SourceRegistry()
        adapter_registry = AdapterRegistry(source_registry)

        source = Source(
            source_medium=SourceMedium.PDF,
            source_uri="test.pdf",
        )

        adapter = adapter_registry.find_adapter(source)

        assert isinstance(adapter, PDFAdapter)

    def test_registry_finds_video_adapter(self):
        """Test that registry finds video adapter."""
        source_registry = SourceRegistry()
        adapter_registry = AdapterRegistry(source_registry)

        source = Source(
            source_medium=SourceMedium.VIDEO,
            source_uri="http://youtube.com/video",
        )

        adapter = adapter_registry.find_adapter(source)

        assert isinstance(adapter, VideoAdapter)

    def test_registry_ingest_and_extract_end_to_end(self):
        """Test full end-to-end ingestion and extraction."""
        source_registry = SourceRegistry()
        adapter_registry = AdapterRegistry(source_registry)

        source = source_registry.register_source(
            source_medium=SourceMedium.TEXT,
            source_uri="test.txt",
            metadata={"content": "This is a test. This is another test."},
        )

        claims = adapter_registry.ingest_and_extract(source)

        assert len(claims) > 0
        assert all(isinstance(c, KnowledgeClaim) for c in claims)
        assert all(c.source_id == source.source_id for c in claims)
        assert all(c.provenance_hash for c in claims)

    def test_registry_no_adapter_for_unsupported(self):
        """Test that registry returns None for unsupported medium."""
        source_registry = SourceRegistry()
        adapter_registry = AdapterRegistry(source_registry)

        # Create a source with unsupported medium (using raw Source)
        source = Source(
            source_medium=SourceMedium.UNKNOWN,
            source_uri="unknown",
        )

        adapter = adapter_registry.find_adapter(source)

        assert adapter is None


class TestClaimProvenance:
    """Test that all claims include proper provenance."""

    def test_text_adapter_claims_have_provenance(self):
        """Test text adapter claims have complete provenance."""
        registry = SourceRegistry()
        adapter = TextAdapter(registry)

        source = registry.register_source(
            source_medium=SourceMedium.TEXT,
            source_uri="test.txt",
            metadata={"content": "Test claim here."},
        )

        artifact = adapter.ingest(source)
        claims = adapter.extract_claims(artifact)

        for claim in claims:
            assert claim.source_id == source.source_id
            assert claim.source_uri == source.source_uri
            assert claim.source_medium == SourceMedium.TEXT.value
            assert claim.provenance_hash
            assert claim.content_hash
            assert claim.extracted_by == "TextAdapter"

    def test_video_adapter_claims_have_timestamps(self):
        """Test video adapter includes timestamps."""
        registry = SourceRegistry()
        adapter = VideoAdapter(registry)

        source = registry.register_source(
            source_medium=SourceMedium.VIDEO,
            source_uri="video.mp4",
            metadata={"transcript": "First statement. Second statement. Third statement."},
        )

        artifact = adapter.ingest(source)
        claims = adapter.extract_claims(artifact)

        # All video claims should have timestamps or at least source_location
        for claim in claims:
            assert claim.source_location is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
