from dataclasses import dataclass


@dataclass
class SourceRecord:
    source_uri: str
    source_type: str
    evidence_status: str = "untrusted"


class SourceRegistry:
    def __init__(self):
        self.sources: dict[str, SourceRecord] = {}

    def register(self, source_uri: str, source_type: str) -> SourceRecord:
        record = self.sources.setdefault(source_uri, SourceRecord(source_uri, source_type))
        return record
