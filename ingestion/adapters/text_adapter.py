from ingestion.base import IngestedDocument


class TextAdapter:
    def ingest(self, text: str, source_uri: str = "memory://text") -> IngestedDocument:
        return IngestedDocument(source_uri, "text", text, "text/plain", "text_adapter")
