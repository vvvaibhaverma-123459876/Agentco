"""Failure-recovery benchmark adapter contract."""

from __future__ import annotations

from .base import SubjectInvocation, UnsupportedSubjectAdapter


class RecoveryAdapter(UnsupportedSubjectAdapter):
    adapter_id = "recovery"

    def supports(self, invocation: SubjectInvocation) -> bool:
        return False
