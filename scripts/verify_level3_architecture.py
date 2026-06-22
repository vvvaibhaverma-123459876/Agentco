#!/usr/bin/env python3
"""
Verify LEVEL_3 Architecture Completeness

This script checks that all required services, routes, and CLI scripts exist
for LEVEL_3 autonomy implementation.
"""

import os
import sys
import json

def check_file_exists(path, description):
    """Check if a file exists and report"""
    exists = os.path.isfile(path)
    status = "✓" if exists else "✗"
    print(f"  {status} {description}: {path}")
    return exists

def check_dir_exists(path, description):
    """Check if a directory exists and report"""
    exists = os.path.isdir(path)
    status = "✓" if exists else "✗"
    print(f"  {status} {description}: {path}")
    return exists

def main():
    print("\n" + "="*80)
    print("LEVEL_3 ARCHITECTURE VERIFICATION")
    print("="*80 + "\n")

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_checks = []

    # ===== BACKEND SERVICES =====
    print("📋 Backend Services:")
    services = [
        ("learner.service.ts", "Learner service"),
        ("eval-harness.service.ts", "Evaluation harness service"),
        ("self-modification-validator.service.ts", "Self-modification validator"),
        ("autonomy-orchestrator.service.ts", "Autonomy orchestrator"),
    ]
    for filename, desc in services:
        path = os.path.join(repo_root, "backend/src/services", filename)
        result = check_file_exists(path, desc)
        all_checks.append((desc, result))

    # ===== CLI SCRIPTS =====
    print("\n📋 CLI Scripts:")
    scripts = [
        ("autonomy_smoke.py", "Autonomy smoke test"),
        ("run_level3_autonomy_smoke.py", "LEVEL_3 smoke test"),
        ("run_learner.py", "Learner CLI"),
        ("run_autonomy_eval.py", "Eval harness CLI"),
        ("verify_level3_architecture.py", "Architecture verification"),
    ]
    for filename, desc in scripts:
        path = os.path.join(repo_root, "scripts", filename)
        if filename == "verify_level3_architecture.py":
            result = True  # We're running it now
        else:
            result = os.path.isfile(path)
        status = "✓" if result else "✗"
        print(f"  {status} {desc}: {path}")
        all_checks.append((desc, result))

    # ===== FRONTEND PAGES =====
    print("\n📋 Frontend Pages:")
    frontend_pages = [
        "autonomy/page.tsx",  # Overview
        "autonomy/tasks/page.tsx",
        "autonomy/goals/page.tsx",
        "autonomy/memory/page.tsx",
        "autonomy/evals/page.tsx",
        "autonomy/learner/page.tsx",
        "autonomy/artifacts/page.tsx",
        "autonomy/canary/page.tsx",
        "autonomy/governance/page.tsx",
        "autonomy/observability/page.tsx",
    ]
    frontend_pages_exist = 0
    for page_path in frontend_pages:
        path = os.path.join(repo_root, "frontend/src/app", page_path)
        result = os.path.isfile(path)
        status = "✓" if result else "✗"
        print(f"  {status} {page_path}")
        if result:
            frontend_pages_exist += 1
        all_checks.append((f"Frontend page: {page_path}", result))

    print(f"\n  Frontend Implementation: {frontend_pages_exist}/10 pages ({frontend_pages_exist*10}%)")

    # ===== TESTS =====
    print("\n📋 Integration Tests:")
    tests = [
        ("tests/integration/test_level3_autonomy_loop.py", "LEVEL_3 autonomy loop test"),
    ]
    for filename, desc in tests:
        path = os.path.join(repo_root, filename)
        result = check_file_exists(path, desc)
        all_checks.append((desc, result))

    # ===== MAKEFILE COMMANDS =====
    print("\n📋 Makefile Commands:")
    makefile_path = os.path.join(repo_root, "Makefile")
    with open(makefile_path) as f:
        makefile_content = f.read()

    commands = [
        ("autonomy-level3-smoke", "LEVEL_3 smoke test command"),
        ("autonomy-level3-test", "LEVEL_3 test command"),
    ]
    for cmd, desc in commands:
        result = cmd in makefile_content
        status = "✓" if result else "✗"
        print(f"  {status} {desc}: make {cmd}")
        all_checks.append((desc, result))

    # ===== DATABASE SCHEMA =====
    print("\n📋 Database Schema (migrations 021-035):")
    migrations = [
        "021_observability_traces.sql",
        "022_autonomy_tasks.sql",
        "023_autonomy_episodes.sql",
        "024_perception_infrastructure.sql",
        "025_autonomy_goals.sql",
        "026_autonomy_plans.sql",
        "027_reward_system.sql",
        "028_eval_harness.sql",
        "029_learner_infrastructure.sql",
        "030_self_modification.sql",
        "031_artifact_registry.sql",
        "032_canary_deployment.sql",
        "033_rbac.sql",
        "034_policy_control.sql",
        "035_simulator_infrastructure.sql",
    ]
    migrations_exist = 0
    for migration in migrations:
        path = os.path.join(repo_root, f"backend/src/db/migrations/{migration}")
        result = os.path.isfile(path)
        status = "✓" if result else "✗"
        print(f"  {status} {migration}")
        if result:
            migrations_exist += 1
        all_checks.append((f"Migration: {migration}", result))

    print(f"\n  Migrations: {migrations_exist}/15 ({migrations_exist*100//15}%)")

    # ===== SUMMARY =====
    print("\n" + "="*80)
    passed = sum(1 for _, result in all_checks if result)
    total = len(all_checks)
    percentage = (passed * 100) // total if total > 0 else 0

    print(f"VERIFICATION SUMMARY: {passed}/{total} checks passed ({percentage}%)")
    print("="*80)

    # Detailed results
    if percentage >= 80:
        print("\n✅ LEVEL_3 ARCHITECTURE IS MOSTLY COMPLETE")
        print(f"\n   {passed} of {total} checks passed")
        print("\n   Ready for testing with: make autonomy-level3-smoke")
    elif percentage >= 50:
        print("\n⚠️  LEVEL_3 ARCHITECTURE IS PARTIALLY COMPLETE")
        print(f"\n   {passed} of {total} checks passed")
        print("\n   Missing components:")
        for name, result in all_checks:
            if not result:
                print(f"     - {name}")
    else:
        print("\n❌ LEVEL_3 ARCHITECTURE IS INCOMPLETE")
        print(f"\n   {passed} of {total} checks passed")
        print("\n   Missing components:")
        for name, result in all_checks:
            if not result:
                print(f"     - {name}")

    return 0 if percentage >= 80 else 1

if __name__ == '__main__':
    sys.exit(main())
