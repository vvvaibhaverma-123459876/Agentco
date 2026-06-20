"""
Medium Adapter Interfaces — Convert any medium to KnowledgeClaim objects.

Adapters ingest content from various media (text, PDF, video, code, data)
and extract structured KnowledgeClaim objects with full provenance.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from dataclasses import dataclass

from .knowledge_claim import KnowledgeClaim, ClaimType, EvidenceType, SourceLocation
from .source_registry import Source, SourceMedium, SourceRegistry


@dataclass
class IngestionArtifact:
    """Result of ingesting a source."""

    source: Source  # Registered source
    raw_content: str  # Raw extracted content
    structured_metadata: Dict[str, Any]  # Parsed metadata
    extraction_method: str  # How content was extracted
    confidence: float  # Confidence in extraction (0.0-1.0)


class LearningAdapter(ABC):
    """Base class for adapters that convert media to KnowledgeClaim objects."""

    def __init__(self, source_registry: SourceRegistry):
        """Initialize adapter with registry reference."""
        self.source_registry = source_registry
        self.name = self.__class__.__name__

    @abstractmethod
    def supports(self, source: Source) -> bool:
        """Check if this adapter can handle the source medium."""
        pass

    @abstractmethod
    def ingest(self, source: Source) -> IngestionArtifact:
        """Ingest a source and produce raw artifact."""
        pass

    @abstractmethod
    def extract_claims(self, artifact: IngestionArtifact) -> List[KnowledgeClaim]:
        """Extract Knowledge Claims from ingestion artifact."""
        pass

    def extract_concepts(self, artifact: IngestionArtifact) -> List[Dict[str, Any]]:
        """Extract concepts and relationships (optional)."""
        return []

    def extract_evidence(self, artifact: IngestionArtifact) -> List[Dict[str, Any]]:
        """Extract evidence markers (optional)."""
        return []

    def extract_open_questions(self, artifact: IngestionArtifact) -> List[Dict[str, Any]]:
        """Extract open questions/unknowns (optional)."""
        return []

    def _create_base_claim(
        self,
        source: Source,
        claim_text: str,
        claim_type: ClaimType,
        evidence_type: EvidenceType,
        domain: str,
        source_location: Optional[SourceLocation] = None,
    ) -> KnowledgeClaim:
        """Create a base KnowledgeClaim from common parameters."""
        return KnowledgeClaim(
            source_id=source.source_id,
            source_medium=source.source_medium.value,
            source_uri=source.source_uri,
            claim_text=claim_text,
            normalized_claim=claim_text.lower().strip(),
            claim_type=claim_type,
            domain=domain,
            extracted_by=self.name,
            evidence_type=evidence_type,
            source_location=source_location or SourceLocation(),
        )


class TextAdapter(LearningAdapter):
    """Adapter for plain text sources."""

    def supports(self, source: Source) -> bool:
        """Support text medium."""
        return source.source_medium == SourceMedium.TEXT

    def ingest(self, source: Source) -> IngestionArtifact:
        """Ingest plain text source."""
        # In real implementation, would read from source.source_uri or source.local_path
        # For now, use fixture
        raw_content = source.metadata.get("content", "")

        return IngestionArtifact(
            source=source,
            raw_content=raw_content,
            structured_metadata={"lines": len(raw_content.split("\n"))},
            extraction_method="text_direct",
            confidence=1.0,
        )

    def extract_claims(self, artifact: IngestionArtifact) -> List[KnowledgeClaim]:
        """Extract claims from text by splitting on periods."""
        claims = []

        # Simple heuristic: split on periods and treat as sentences
        sentences = artifact.raw_content.split(".")
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 10:  # Only process non-trivial sentences
                claim = self._create_base_claim(
                    source=artifact.source,
                    claim_text=sentence,
                    claim_type=ClaimType.EMPIRICAL_CLAIM,
                    evidence_type=EvidenceType.BLOG_ARTICLE,
                    domain="general",
                    source_location=SourceLocation(line=i + 1),
                )
                claims.append(claim)

        return claims


class PDFAdapter(LearningAdapter):
    """Adapter for PDF documents."""

    def supports(self, source: Source) -> bool:
        """Support PDF medium."""
        return source.source_medium == SourceMedium.PDF

    def ingest(self, source: Source) -> IngestionArtifact:
        """Ingest PDF source."""
        # In real implementation, would use PyPDF2 or pdfplumber
        # For now, use fixture data
        raw_content = source.metadata.get("content", "")
        pages = raw_content.split("\n---PAGE_BREAK---\n")

        return IngestionArtifact(
            source=source,
            raw_content=raw_content,
            structured_metadata={
                "pages": len(pages),
                "title": source.title or "Unknown",
                "author": source.author or "Unknown",
            },
            extraction_method="pdf_parse_fixture",
            confidence=0.8,  # PDF parsing less reliable than native text
        )

    def extract_claims(self, artifact: IngestionArtifact) -> List[KnowledgeClaim]:
        """Extract claims from PDF with page references."""
        claims = []
        pages = artifact.raw_content.split("\n---PAGE_BREAK---\n")

        for page_num, page_content in enumerate(pages, 1):
            sentences = page_content.split(".")
            for line_num, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if len(sentence) > 10:
                    claim = self._create_base_claim(
                        source=artifact.source,
                        claim_text=sentence,
                        claim_type=ClaimType.EMPIRICAL_CLAIM,
                        evidence_type=EvidenceType.SINGLE_PEER_REVIEWED_PAPER,
                        domain="academic",
                        source_location=SourceLocation(
                            page=page_num,
                            line=line_num + 1,
                        ),
                    )
                    claims.append(claim)

        return claims


class WebPageAdapter(LearningAdapter):
    """Adapter for web pages."""

    def supports(self, source: Source) -> bool:
        """Support webpage medium."""
        return source.source_medium == SourceMedium.WEBPAGE

    def ingest(self, source: Source) -> IngestionArtifact:
        """Ingest web page source."""
        # In real implementation, would use requests + BeautifulSoup
        # For now, use fixture
        raw_content = source.metadata.get("content", "")

        return IngestionArtifact(
            source=source,
            raw_content=raw_content,
            structured_metadata={
                "title": source.title or "Untitled",
                "url": source.source_uri,
            },
            extraction_method="web_scrape_fixture",
            confidence=0.7,  # Web content variable quality
        )

    def extract_claims(self, artifact: IngestionArtifact) -> List[KnowledgeClaim]:
        """Extract claims from web page."""
        claims = []

        # Simple: split on periods
        sentences = artifact.raw_content.split(".")
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 10:
                claim = self._create_base_claim(
                    source=artifact.source,
                    claim_text=sentence,
                    claim_type=ClaimType.OPINION,
                    evidence_type=EvidenceType.BLOG_ARTICLE,
                    domain="web",
                    source_location=SourceLocation(url_fragment=f"#{i}"),
                )
                claims.append(claim)

        return claims


class VideoAdapter(LearningAdapter):
    """Adapter for video lectures and media."""

    def supports(self, source: Source) -> bool:
        """Support video medium."""
        return source.source_medium == SourceMedium.VIDEO

    def ingest(self, source: Source) -> IngestionArtifact:
        """Ingest video source (via transcript fixture)."""
        # In real implementation, would fetch transcript from YouTube, etc.
        # For now, use transcript fixture from metadata
        transcript = source.metadata.get("transcript", "")

        return IngestionArtifact(
            source=source,
            raw_content=transcript,
            structured_metadata={
                "speaker": source.speaker or "Unknown",
                "duration_seconds": source.metadata.get("duration", 0),
                "transcript_confidence": 0.9,
            },
            extraction_method="video_transcript_fixture",
            confidence=0.9,
        )

    def extract_claims(self, artifact: IngestionArtifact) -> List[KnowledgeClaim]:
        """Extract claims from video transcript with timestamps."""
        claims = []

        # Split on sentence boundaries
        sentences = artifact.raw_content.split(".")
        timestamp_step = 60  # Assume 60 seconds per sentence (mock)

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 10:
                timestamp = timestamp_step * i
                minutes = timestamp // 60
                seconds = timestamp % 60

                claim = self._create_base_claim(
                    source=artifact.source,
                    claim_text=sentence,
                    claim_type=ClaimType.SCIENTIFIC_PRINCIPLE,
                    evidence_type=EvidenceType.EXPERT_LECTURE,
                    domain="education",
                    source_location=SourceLocation(
                        timestamp=f"{minutes:02d}:{seconds:02d}"
                    ),
                )
                claims.append(claim)

        return claims


class AudioAdapter(LearningAdapter):
    """Adapter for audio lectures and podcasts."""

    def supports(self, source: Source) -> bool:
        """Support audio medium."""
        return source.source_medium == SourceMedium.AUDIO

    def ingest(self, source: Source) -> IngestionArtifact:
        """Ingest audio source (via transcript fixture)."""
        # In real implementation, would use speech-to-text
        # For now, use transcript fixture
        transcript = source.metadata.get("transcript", "")

        return IngestionArtifact(
            source=source,
            raw_content=transcript,
            structured_metadata={
                "speaker": source.speaker or "Unknown",
                "duration_seconds": source.metadata.get("duration", 0),
            },
            extraction_method="audio_transcript_fixture",
            confidence=0.85,
        )

    def extract_claims(self, artifact: IngestionArtifact) -> List[KnowledgeClaim]:
        """Extract claims from audio transcript."""
        claims = []

        sentences = artifact.raw_content.split(".")
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 10:
                claim = self._create_base_claim(
                    source=artifact.source,
                    claim_text=sentence,
                    claim_type=ClaimType.OPINION,
                    evidence_type=EvidenceType.EXPERT_LECTURE,
                    domain="audio",
                    source_location=SourceLocation(
                        timestamp=f"{i*60//60:02d}:{i*60%60:02d}"
                    ),
                )
                claims.append(claim)

        return claims


class CodeRepositoryAdapter(LearningAdapter):
    """Adapter for code repositories and source code."""

    def supports(self, source: Source) -> bool:
        """Support code repository medium."""
        return source.source_medium == SourceMedium.CODE_REPO

    def ingest(self, source: Source) -> IngestionArtifact:
        """Ingest code repository."""
        # In real implementation, would clone repo and parse
        # For now, use fixture (README content)
        readme_content = source.metadata.get("readme", "")

        return IngestionArtifact(
            source=source,
            raw_content=readme_content,
            structured_metadata={
                "repo_url": source.source_uri,
                "readme_exists": len(readme_content) > 0,
            },
            extraction_method="code_readme_fixture",
            confidence=0.95,
        )

    def extract_claims(self, artifact: IngestionArtifact) -> List[KnowledgeClaim]:
        """Extract claims from README and code documentation."""
        claims = []

        # Extract capability claims from README
        if artifact.raw_content:
            sentences = artifact.raw_content.split(".")
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if len(sentence) > 10:
                    claim = self._create_base_claim(
                        source=artifact.source,
                        claim_text=sentence,
                        claim_type=ClaimType.ENGINEERING_CLAIM,
                        evidence_type=EvidenceType.REPRODUCIBLE_CODE,
                        domain="software",
                        source_location=SourceLocation(code_file="README.md", code_lines=(i, i + 1)),
                    )
                    claims.append(claim)

        return claims


class DatasetAdapter(LearningAdapter):
    """Adapter for datasets."""

    def supports(self, source: Source) -> bool:
        """Support dataset medium."""
        return source.source_medium == SourceMedium.DATASET

    def ingest(self, source: Source) -> IngestionArtifact:
        """Ingest dataset source."""
        # In real implementation, would load and analyze data
        # For now, use schema from metadata
        schema = source.metadata.get("schema", {})
        stats = source.metadata.get("statistics", {})

        return IngestionArtifact(
            source=source,
            raw_content=f"Schema: {schema}\nStats: {stats}",
            structured_metadata={
                "schema": schema,
                "row_count": stats.get("rows", 0),
                "column_count": len(schema),
            },
            extraction_method="dataset_schema_fixture",
            confidence=0.9,
        )

    def extract_claims(self, artifact: IngestionArtifact) -> List[KnowledgeClaim]:
        """Extract structural and statistical claims from dataset."""
        claims = []

        # Extract schema claim
        schema = artifact.structured_metadata.get("schema", {})
        if schema:
            schema_claim = self._create_base_claim(
                source=artifact.source,
                claim_text=f"Dataset has schema: {list(schema.keys())}",
                claim_type=ClaimType.DEFINITION,
                evidence_type=EvidenceType.RAW_DATASET,
                domain="data",
            )
            claims.append(schema_claim)

        # Extract statistical claims
        row_count = artifact.structured_metadata.get("row_count", 0)
        if row_count > 0:
            stat_claim = self._create_base_claim(
                source=artifact.source,
                claim_text=f"Dataset contains {row_count} rows",
                claim_type=ClaimType.EMPIRICAL_CLAIM,
                evidence_type=EvidenceType.RAW_DATASET,
                domain="data",
            )
            claims.append(stat_claim)

        return claims


class HumanFeedbackAdapter(LearningAdapter):
    """Adapter for human feedback and annotations."""

    def supports(self, source: Source) -> bool:
        """Support human feedback medium."""
        return source.source_medium == SourceMedium.HUMAN_FEEDBACK

    def ingest(self, source: Source) -> IngestionArtifact:
        """Ingest human feedback."""
        feedback_text = source.metadata.get("feedback", "")

        return IngestionArtifact(
            source=source,
            raw_content=feedback_text,
            structured_metadata={
                "reviewer": source.author or "Anonymous",
                "feedback_type": source.metadata.get("type", "general"),
            },
            extraction_method="human_feedback_direct",
            confidence=1.0,
        )

    def extract_claims(self, artifact: IngestionArtifact) -> List[KnowledgeClaim]:
        """Extract claims from human feedback."""
        claims = []

        sentences = artifact.raw_content.split(".")
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 10:
                claim = self._create_base_claim(
                    source=artifact.source,
                    claim_text=sentence,
                    claim_type=ClaimType.OPINION,
                    evidence_type=EvidenceType.HUMAN_FEEDBACK,
                    domain="feedback",
                )
                claims.append(claim)

        return claims


class AdapterRegistry:
    """Registry of available adapters."""

    def __init__(self, source_registry: SourceRegistry):
        """Initialize with adapters."""
        self.source_registry = source_registry
        self.adapters: List[LearningAdapter] = [
            TextAdapter(source_registry),
            PDFAdapter(source_registry),
            WebPageAdapter(source_registry),
            VideoAdapter(source_registry),
            AudioAdapter(source_registry),
            CodeRepositoryAdapter(source_registry),
            DatasetAdapter(source_registry),
            HumanFeedbackAdapter(source_registry),
        ]

    def find_adapter(self, source: Source) -> Optional[LearningAdapter]:
        """Find appropriate adapter for source."""
        for adapter in self.adapters:
            if adapter.supports(source):
                return adapter
        return None

    def ingest_and_extract(self, source: Source) -> List[KnowledgeClaim]:
        """Ingest source and extract claims."""
        adapter = self.find_adapter(source)
        if not adapter:
            return []

        artifact = adapter.ingest(source)
        return adapter.extract_claims(artifact)
