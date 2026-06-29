from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .doctor import ROOT, build_report, collect_checks, write_report
from .modes import assert_fixture_fallback_allowed, is_production_like_env


def run_goal(mode: str) -> tuple[int, str]:
    script = ROOT / "scripts" / "verify_agentco_goal_run.py"
    env = os.environ.copy()
    if mode in ("offline_fixture", "ci_smoke"):
        env["AGENTCO_VERIFY_OFFLINE"] = "1"
        cmd = [sys.executable, str(script), "--offline"]
    else:
        cmd = [sys.executable, str(script)]
    proc = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, check=False, timeout=60)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="local_native")
    parser.add_argument(
        "--allow-offline-fallback",
        action="store_true",
        help="Permit non-production best-effort runs to downgrade to offline_fixture when required services are unavailable.",
    )
    args = parser.parse_args(argv)
    run_builds = args.mode not in ("offline_fixture", "ci_smoke")
    report = build_report(args.mode, collect_checks(args.mode, args.mode not in ("offline_fixture", "ci_smoke"), run_builds))
    selected = report["selected_runtime_mode"]

    production_like = args.mode == "production" or is_production_like_env()
    if not report["can_continue"] and production_like:
        report["run_best_effort"] = {
            "selected_runtime_mode": selected,
            "exit_code": 1,
            "completed": False,
            "blocked_reason": "production/staging cannot downgrade to offline_fixture",
        }
        write_report(report)
        print("AgentCo run-best-effort blocked: production/staging cannot downgrade to offline_fixture")
        return 1

    if not report["can_continue"] and args.mode not in ("offline_fixture", "ci_smoke"):
        if not args.allow_offline_fallback:
            report["run_best_effort"] = {
                "selected_runtime_mode": selected,
                "exit_code": 1,
                "completed": False,
                "blocked_reason": "offline fixture fallback requires --allow-offline-fallback",
            }
            write_report(report)
            print("AgentCo run-best-effort blocked: offline fixture fallback requires --allow-offline-fallback")
            return 1
        report = build_report("offline_fixture", collect_checks("offline_fixture", False, False))
        selected = "offline_fixture"
    service_status = {svc["service"]: svc["status"] for svc in report["services"]}
    if selected not in ("offline_fixture", "ci_smoke") and service_status.get("openai_connectivity") != "real":
        if not args.allow_offline_fallback:
            report["disabled_capabilities"].append("live_llm_goal_cycle")
            report["run_best_effort"] = {
                "selected_runtime_mode": selected,
                "exit_code": 1,
                "completed": False,
                "blocked_reason": "live OpenAI unavailable; deterministic fixture goal cycle requires --allow-offline-fallback or explicit offline_fixture mode",
            }
            write_report(report)
            print("AgentCo run-best-effort blocked: live OpenAI unavailable and fixture fallback was not explicitly allowed")
            return 1
        assert_fixture_fallback_allowed("offline_fixture")
        report["requested_mode_before_goal_fallback"] = selected
        report["disabled_capabilities"].append("live_llm_goal_cycle")
        report["fallbacks_used"].append(
            {
                "service": "openai_connectivity",
                "fallback": "deterministic_fixture_llm",
                "status": service_status.get("openai_connectivity", "missing"),
            }
        )
        selected = "offline_fixture"
    code, output = run_goal(selected)
    report["run_best_effort"] = {"selected_runtime_mode": selected, "exit_code": code, "completed": code == 0, "output_tail": output[-1000:]}
    write_report(report)
    print(f"AgentCo run-best-effort selected {selected} completed={code == 0}")
    print(output)
    return 0 if code == 0 and report["can_continue"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
