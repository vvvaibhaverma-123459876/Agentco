from pathlib import Path

from ingestion import IngestionPipeline
from ingestion.adapters import CodeAdapter, TextAdapter, WebAdapter


def test_text_and_web_ingestion_create_untrusted_claims_with_provenance():
    pipeline = IngestionPipeline()
    text_doc = TextAdapter().ingest("Agentco records provenance. Claims start untrusted.")
    html_doc = WebAdapter().ingest("<html><body>External validators resolve claims.</body></html>")

    text_result = pipeline.ingest_document(text_doc)
    web_result = pipeline.ingest_document(html_doc)

    assert text_result["source"].evidence_status == "untrusted"
    assert text_result["claims"][0].evidence_status == "untrusted"
    assert text_result["claims"][0].source_uri == "memory://text"
    assert web_result["audit_event"]["extraction_method"] == "web_adapter"


def test_code_adapter_routes_claims_to_evidence_kernel(tmp_path: Path):
    sample = tmp_path / "sample.py"
    sample.write_text('"""This module preserves provenance."""\nVALUE = 1\n')
    pipeline = IngestionPipeline()

    result = pipeline.ingest_document(CodeAdapter().ingest(str(sample)))

    assert result["claims"]
    assert result["claims"][0].source_type == "code"
    assert result["claims"][0].promotion_status == "unpromoted"
