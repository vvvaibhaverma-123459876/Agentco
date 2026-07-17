"""Governance benchmark adapter contract."""

from __future__ import annotations

from .base import SubjectInvocation, UnsupportedSubjectAdapter


class GovernanceAdapter(UnsupportedSubjectAdapter):
    adapter_id = "governance"

    def supports(self, invocation: SubjectInvocation) -> bool:
        return False
