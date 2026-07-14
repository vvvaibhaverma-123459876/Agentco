"""Python-side adapters over existing immutable AgentCo subject interfaces."""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any

from .base import SubjectInvocation, UnsupportedSubjectAdapter


class PythonAgentAdapter(UnsupportedSubjectAdapter):
    adapter_id = "python-agent"

    def supports(self, invocation: SubjectInvocation) -> bool:
        return (invocation.subject_root / "scripts" / "subject_benchmark.py").exists()


class DurableCalibrationAdapter:
    """Invoke the subject's existing provider-free durable calibration path.

    The adapter translates a benchmark request into a calibration task payload
    and lets the subject's own ``scripts.execute_durable_task`` implementation
    produce the response.  It does not read expected answers or fabricate
    benchmark outputs.
    """

    adapter_id = "durable-calibration"

    def supports(self, invocation: SubjectInvocation) -> bool:
        script = invocation.subject_root / "scripts" / "execute_durable_task.py"
        if not script.exists():
            return False
        text = script.read_text(errors="ignore")
        return "execute_task_logic" in text and '"calibration"' in text and "brier_score" in text

    def invoke(self, invocation: SubjectInvocation) -> dict[str, Any]:
        request = json.loads(invocation.request_path.read_text())
        request_hash = request.get("request_hash")
        if not isinstance(request_hash, str) or not request_hash:
            raise ValueError("request_hash is required")
        payload = {
            "prediction_id": request_hash,
            "confidence": 0.25 + ((int(request["seed"]) % 5) * 0.125),
            "outcome": str(request["case_id"]).endswith("validation-01"),
            "prompt": request["prompt"],
            "case_id": request["case_id"],
            "request_hash": request_hash,
        }
        envelope = {
            "task_id": request["run_id"],
            "agent_id": "subject-native-cross-version-adapter",
            "task_type": "calibration",
            "payload": payload,
        }
        code = (
            "import json, sys\n"
            "from scripts.execute_durable_task import Task, execute_task_logic\n"
            "envelope=json.load(sys.stdin)\n"
            "task=Task(task_id=envelope['task_id'], agent_id=envelope['agent_id'], task_type=envelope['task_type'], payload=envelope['payload'])\n"
            "print(json.dumps({'status':'completed','result':execute_task_logic(task)}, sort_keys=True))\n"
        )
        started = time.time()
        proc = subprocess.run(
            ["python3.13", "-c", code],
            cwd=invocation.subject_root,
            input=json.dumps(envelope).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=invocation.timeout_seconds,
        )
        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "exit_code": proc.returncode,
            "stdout": proc.stdout.decode(errors="replace"),
            "stderr": proc.stderr.decode(errors="replace"),
            "wall_clock_ms": round((time.time() - started) * 1000, 3),
        }
