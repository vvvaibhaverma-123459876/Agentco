"""Data-analysis benchmark adapter contract."""

from __future__ import annotations

from .base import SubjectInvocation, UnsupportedSubjectAdapter


class DataAnalysisAdapter(UnsupportedSubjectAdapter):
    adapter_id = "data-analysis"

    def supports(self, invocation: SubjectInvocation) -> bool:
        return False
