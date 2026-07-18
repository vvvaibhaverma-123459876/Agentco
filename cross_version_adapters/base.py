"""Adapter contracts for cross-version subject-native evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class SubjectInvocation:
    subject_root: Path
    request_path: Path
    timeout_seconds: float


class SubjectAdapter(Protocol):
    adapter_id: str

    def supports(self, invocation: SubjectInvocation) -> bool:
        """Return true only when a subject-native interface is available."""

    def invoke(self, invocation: SubjectInvocation) -> dict[str, Any]:
        """Invoke the subject-native interface and return normalized evidence."""


class UnsupportedSubjectAdapter:
    adapter_id = "unsupported"

    def supports(self, invocation: SubjectInvocation) -> bool:
        return True

    def invoke(self, invocation: SubjectInvocation) -> dict[str, Any]:
        return {
            "status": "unsupported",
            "reason": "subject does not expose subject-benchmark-v1",
            "request_path": str(invocation.request_path),
        }
