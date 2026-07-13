import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str) -> dict:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_active_gate_integrity_scanner_blocks_false_success_patterns():
    result = _run("python3.13", "scripts/verify_gate_integrity.py", "--check")
    assert result == {"findings": 0, "success": True}


def test_documented_make_targets_are_defined():
    result = _run("python3.13", "scripts/verify_make_targets.py", "--check")
    assert result == {"missing": 0, "success": True}
