"""Backend runtime adapter contract for future subject benchmark routes."""

from __future__ import annotations

from .base import SubjectInvocation, UnsupportedSubjectAdapter


class BackendRuntimeAdapter(UnsupportedSubjectAdapter):
    adapter_id = "backend-runtime"

    def supports(self, invocation: SubjectInvocation) -> bool:
        return (invocation.subject_root / "backend" / "src" / "routes" / "subject-benchmark.routes.ts").exists()
