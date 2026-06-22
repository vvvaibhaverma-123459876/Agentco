from pathlib import Path

from ingestion.base import IngestedDocument


class CodeAdapter:
    def ingest(self, path: str) -> IngestedDocument:
        p = Path(path)
        return IngestedDocument(p.as_uri(), "code", p.read_text(), "text/x-python", "code_adapter")
