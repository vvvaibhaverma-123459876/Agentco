"""Memory benchmark adapter contract."""

from __future__ import annotations

from .base import SubjectInvocation, UnsupportedSubjectAdapter


class MemoryAdapter(UnsupportedSubjectAdapter):
    adapter_id = "memory"

    def supports(self, invocation: SubjectInvocation) -> bool:
        return False
