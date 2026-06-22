import re

from ingestion.base import IngestedDocument


class ClaimExtractor:
    def extract(self, document: IngestedDocument) -> list[str]:
        sentences = [s.strip() for s in re.split(r"[.!?]\s+", document.content) if s.strip()]
        return [s for s in sentences if len(s.split()) >= 3]
