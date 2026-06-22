import re

from ingestion.base import IngestedDocument


class WebAdapter:
    def ingest(self, html: str, source_uri: str = "file://fixture.html") -> IngestedDocument:
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return IngestedDocument(source_uri, "web", text, "text/html", "web_adapter")
