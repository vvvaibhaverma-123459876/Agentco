"""Run the safest available AgentCo smoke cycle."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .doctor import REPORT_DIR, build_report, collect_checks, write_report


ROOT = Path(__file__).resolve().parents[2]


def run_goal(selected_mode: str) -> tuple[int, str]:
    script = ROOT / "scripts" / "verify_agentco_goal_run.py"
    env = os.environ.copy()
    if selected_mode in ("offline_fixture", "ci_smoke"):
        env["AGENTCO_VERIFY_OFFLINE"] = "1"
        cmd = [sys.executable, str(script), "--offline"]
    else:
        cmd = [sys.executable, str(script)]
    proc = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, check=False, timeout=60)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="local_native")
    args = parser.parse_args(argv)
    run_builds = args.mode not in ("offline_fixture", "ci_smoke")
    checks = collect_checks(args.mode, live_openai=args.mode not in ("offline_fixture", "ci_smoke"), run_builds=run_builds)
    report = build_report(args.mode, checks)
    selected = report["selected_runtime_mode"]
    if not report["can_continue"] and args.mode not in ("offline_fixture", "ci_smoke"):
        # Best-effort is allowed to fall back to offline_fixture when critical
        # local services are absent, but the report must state that DB/LLM are not real.
        checks = collect_checks("offline_fixture", live_openai=False, run_builds=False)
        report = build_report("offline_fixture", checks)
        selected = report["selected_runtime_mode"]
    code, output = run_goal(selected)
    report["run_best_effort"] = {
        "selected_runtime_mode": selected,
        "exit_code": code,
        "output_tail": output[-1000:],
        "completed": code == 0,
    }
    write_report(report)
    print(f"AgentCo run-best-effort selected {selected} completed={code == 0}")
    print(output)
    return 0 if code == 0 and report["can_continue"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
