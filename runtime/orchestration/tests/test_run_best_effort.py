import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_run_best_effort_offline_fixture_exits_successfully():
    proc = subprocess.run(
        [sys.executable, "-m", "runtime.orchestration.run_best_effort", "--mode", "offline_fixture"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((ROOT / "reports/system_run/latest/doctor_report.json").read_text())
    assert report["selected_runtime_mode"] == "offline_fixture"
    assert report["run_best_effort"]["completed"] is True
