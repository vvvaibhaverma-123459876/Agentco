"""Python agent adapter placeholder.

This adapter only reports support when a future immutable subject exposes an
explicit subject benchmark CLI.  It does not synthesize answers.
"""

from __future__ import annotations

from .base import SubjectInvocation, UnsupportedSubjectAdapter


class PythonAgentAdapter(UnsupportedSubjectAdapter):
    adapter_id = "python-agent"

    def supports(self, invocation: SubjectInvocation) -> bool:
        return (invocation.subject_root / "scripts" / "subject_benchmark.py").exists()
