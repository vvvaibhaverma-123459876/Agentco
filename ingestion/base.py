from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IngestedDocument:
    source_uri: str
    source_type: str
    content: str
    mime_type: str
    extraction_method: str
