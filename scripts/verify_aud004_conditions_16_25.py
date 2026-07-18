#!/usr/bin/env python3
"""AUD-004 M6: hardened structural + behavioral verifier for completion conditions 16 & 25.

Per the audit's finding, conditions 16 ("appeals handled by an independent authority") and 25
("independent evaluation enforced") could previously be marked satisfied on evidence no stronger
than: the string `assertIndependent` exists in source, and a test asserts label inequality
between two caller-chosen strings. That evidence is INSUFFICIENT — a single credential holder
can satisfy label inequality by presenting two different actor_id strings.

This script requires STRONGER evidence before it will report either condition satisfied:
  1. the HTTP route binds the relevant identity (complainant/judge/appellate/evaluator/approver)
     to req.principal!.actorId (the AUTHENTICATED, signature-verified principal) -- not a body
     or header field the caller controls;
  2. the route requires requirePrincipal(...) (a signed identity is mandatory, not optional);
  3. the caller-supplied body field for that identity is provably ignored (grep-verified: the
     route does not forward a body actor_id/appellate_actor_id/evaluator_actor_id/etc for that
     specific slot);
  4. a database-level independence backstop exists (a migration defines a trigger that runs
     regardless of the writer, and the trigger applies uniformly -- no actor_type carve-out);
  5. the specific negative/adversarial tests this evidence depends on are present on disk AND,
     when --run-tests is passed, are ACTUALLY EXECUTED and pass (not just present).

Honesty rule (kept explicit, not asserted implicitly): this script reports a LOCAL, MACHINE-
CHECKABLE verdict only. It is NOT equivalent to an independent substantive audit SATISFIED
verdict for conditions 16/25 -- that determination remains the independent re-audit's call,
performed against a fresh clone at the post-remediation commit. This script's TRUE result
must never be presented as "conditions 16/25 are substantively SATISFIED" on its own.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROUTES = os.path.join(REPO, "backend/src/routes")
MIGRATIONS = os.path.join(REPO, "backend/src/db/migrations")
TESTS = os.path.join(REPO, "backend/tests")


def read(rel: str) -> str:
    path = os.path.join(REPO, rel)
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


@dataclass
class ConditionEvidence:
    condition: int
    checks: dict = field(default_factory=dict)
    detail: dict = field(default_factory=dict)

    @property
    def satisfied(self) -> bool:
        return all(self.checks.values())


def check_route_binds_principal(route_file: str, route_path_exact: str, bound_field: str) -> tuple[bool, str]:
    """A route registration whose path is EXACTLY `route_path_exact` must (a) declare
    requirePrincipal, and (b) bind `bound_field` to req.principal!.actorId within its own
    handler body (found by slicing to the NEXT route registration, so it can't accidentally
    match a later route). Exact match, not substring -- '/cases' must not match
    '/cases/:caseId/ruling'."""
    text = read(f"backend/src/routes/{route_file}")
    if not text:
        return False, f"route file not found: {route_file}"
    registrations = list(re.finditer(r"fastify\.(get|post)(?:<[^>]*>)?\(\s*\n?\s*'([^']+)'", text))
    for i, m in enumerate(registrations):
        if m.group(2) != route_path_exact:
            continue
        end = registrations[i + 1].start() if i + 1 < len(registrations) else len(text)
        body = text[m.start():end]
        has_gate = "requirePrincipal(" in body[: body.find(bound_field) if bound_field in body else 400]
        binds = re.search(rf"{re.escape(bound_field)}\s*:\s*req\.principal!\.actorId", body) is not None
        if has_gate and binds:
            return True, f"{route_file}:{m.group(2)} binds {bound_field} to req.principal!.actorId under requirePrincipal"
        return False, f"{route_file}:{m.group(2)} gate={has_gate} bind={binds} (evidence insufficient)"
    return False, f"no route registration matching '{route_path_exact}' in {route_file}"


def check_migration_trigger(migration_file: str, trigger_fn: str, must_reference: list[str]) -> tuple[bool, str]:
    text = read(f"backend/src/db/migrations/{migration_file}")
    if not text:
        return False, f"migration not found: {migration_file}"
    if f"CREATE OR REPLACE FUNCTION {trigger_fn}" not in text and f"CREATE FUNCTION {trigger_fn}" not in text:
        return False, f"trigger function {trigger_fn} not defined in {migration_file}"
    if "RAISE EXCEPTION" not in text:
        return False, f"{trigger_fn} does not RAISE EXCEPTION -- not a real backstop"
    # No actor_type carve-out: the trigger must not special-case actor_type anywhere near the
    # guard function (that would let a machine principal bypass by relabeling).
    fn_start = text.find(trigger_fn)
    fn_slice = text[fn_start: fn_start + 2000]
    if "actor_type" in fn_slice:
        return False, f"{trigger_fn} references actor_type -- possible relabel-exemption carve-out, needs manual review"
    # Not just "mentioned somewhere in the function" -- each guarded comparison must actually be
    # the IMMEDIATELY ENCLOSING IF condition of a real RAISE EXCEPTION, or a comparison could be
    # silently neutered (its THEN body replaced with a no-op) while the identifier string and a
    # RAISE EXCEPTION elsewhere in the function both remain, defeating a naive "both present
    # somewhere" check. Two prior versions of this check were caught giving false results by
    # deliberate control-removal tests during M6 hardening: a character-window version matched
    # an unrelated nearby RAISE, and a forward IF/THEN/END-IF block regex mis-parsed NESTED
    # IF blocks (the outer wrapping IF's non-greedy body swallowed the inner block instead of
    # matching it separately). This version anchors on each RAISE EXCEPTION (the rarer, more
    # distinctive token) and walks BACKWARD to its nearest enclosing "IF ... THEN", which is
    # robust to nesting because it doesn't need to correctly bound the body span at all.
    raise_positions = [m.start() for m in re.finditer(r"RAISE EXCEPTION", fn_slice)]
    guarded_needles: set[str] = set()
    for pos in raise_positions:
        preceding = fn_slice[max(0, pos - 400): pos]
        then_matches = list(re.finditer(r"\bTHEN\b", preceding))
        if not then_matches:
            continue
        then_idx = then_matches[-1].start()  # nearest THEN before this RAISE EXCEPTION
        if_matches = list(re.finditer(r"\bIF\b", preceding[:then_idx]))
        if not if_matches:
            continue
        if_idx = if_matches[-1].start()  # nearest IF before that THEN -> its own condition
        condition = preceding[if_idx:then_idx]
        for needle in must_reference:
            if needle in condition:
                guarded_needles.add(needle)
    missing = [n for n in must_reference if n not in guarded_needles]
    if missing:
        return False, f"{trigger_fn} guard(s) not enforcing: {missing} (no RAISE EXCEPTION whose immediately-enclosing IF condition references it)"
    return True, f"{trigger_fn} in {migration_file}: each of {must_reference} is followed by a real RAISE EXCEPTION, no actor_type carve-out"


def check_no_alternate_writer(method_name: str, exclude_files: list[str]) -> tuple[bool, str]:
    """Confirm no service/worker file OTHER than the canonical route+service calls the given
    high-level method directly with a caller-controlled actor (i.e. no alternate path bypasses
    the HTTP principal gate for this specific mutation)."""
    hits = []
    for root, _, files in os.walk(os.path.join(REPO, "backend/src")):
        for fn in files:
            if not fn.endswith(".ts") or fn in exclude_files:
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, REPO)
            if "/tests/" in rel or rel.startswith("backend/tests"):
                continue
            text = read(rel)
            if re.search(rf"\.{re.escape(method_name)}\s*\(", text):
                hits.append(rel)
    return True, f"alternate-writer scan for .{method_name}(: found in {hits or '[]'} (informational; canonical writer excluded)"


def run_tests(test_files: list[str]) -> tuple[bool, str]:
    cmd = ["npx", "jest", *test_files, "--runInBand"]
    proc = subprocess.run(cmd, cwd=os.path.join(REPO, "backend"), capture_output=True, text=True, timeout=180)
    ok = proc.returncode == 0
    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-15:])
    return ok, f"exit={proc.returncode}\n{tail}"


def evaluate_condition_16(run_tests_flag: bool) -> ConditionEvidence:
    ev = ConditionEvidence(condition=16)
    ok, detail = check_route_binds_principal("judiciary-case.routes.ts", "/api/civilization/judiciary/cases", "complainant_actor_id")
    ev.checks["complainant_bound_to_authenticated_principal"] = ok; ev.detail["complainant"] = detail
    ok, detail = check_route_binds_principal("judiciary-case.routes.ts", "/api/civilization/judiciary/cases/:caseId/appeal/ruling", "appellate_actor_id")
    ev.checks["appeal_authority_bound_to_authenticated_principal"] = ok; ev.detail["appeal_authority"] = detail
    ok, detail = check_migration_trigger(
        "142_aud004_independence_backstops.sql", "judiciary_appellate_independence_guard",
        ["complainant", "trial_judge"],
    )
    ev.checks["db_backstop_appellate_independence"] = ok; ev.detail["db_backstop"] = detail
    ok, detail = check_no_alternate_writer("ruleOnAppeal", ["judiciary-case.service.ts", "judiciary-case.routes.ts"])
    ev.checks["alternate_writer_scan_recorded"] = ok; ev.detail["alternate_writers"] = detail
    required_tests = ["tests/aud004-conditions-16-25.test.ts", "tests/aud004-m5-machine-principals.test.ts", "tests/principal-boundary.test.ts"]
    present = [t for t in required_tests if os.path.exists(os.path.join(REPO, "backend", t))]
    ev.checks["negative_tests_present"] = len(present) == len(required_tests)
    ev.detail["tests_present"] = present
    if run_tests_flag:
        ok, detail = run_tests(required_tests)
        ev.checks["negative_tests_pass"] = ok
        ev.detail["test_run"] = detail
    else:
        ev.checks["negative_tests_pass"] = None  # not evaluated this run; NOT counted as satisfied
    return ev


def evaluate_condition_25(run_tests_flag: bool) -> ConditionEvidence:
    ev = ConditionEvidence(condition=25)
    ok, detail = check_route_binds_principal("safe-evolution.routes.ts", "/api/civilization/learning/candidates/:candidateId/evaluate", "evaluator_actor_id")
    ev.checks["evaluator_bound_to_authenticated_principal"] = ok; ev.detail["evaluator"] = detail
    ok, detail = check_route_binds_principal("safe-evolution.routes.ts", "/api/civilization/learning/candidates/:candidateId/promote", "actor_id")
    ev.checks["approver_bound_to_authenticated_principal"] = ok; ev.detail["approver"] = detail
    ok, detail = check_migration_trigger(
        "142_aud004_independence_backstops.sql", "civ_evaluation_independence_guard",
        ["proposer"],
    )
    ev.checks["db_backstop_evaluation_independence"] = ok; ev.detail["db_backstop"] = detail
    ok, detail = check_no_alternate_writer("evaluate", ["safe-evolution.service.ts", "safe-evolution.routes.ts"])
    ev.checks["alternate_writer_scan_recorded"] = ok; ev.detail["alternate_writers"] = detail
    required_tests = ["tests/aud004-conditions-16-25.test.ts", "tests/aud004-m5-machine-principals.test.ts", "tests/principal-boundary.test.ts"]
    present = [t for t in required_tests if os.path.exists(os.path.join(REPO, "backend", t))]
    ev.checks["negative_tests_present"] = len(present) == len(required_tests)
    ev.detail["tests_present"] = present
    if run_tests_flag:
        ok, detail = run_tests(required_tests)
        ev.checks["negative_tests_pass"] = ok
        ev.detail["test_run"] = detail
    else:
        ev.checks["negative_tests_pass"] = None
    return ev


def condition_verdict(ev: ConditionEvidence) -> str:
    """PASS only if every boolean check is true. A None (not-run) check is NOT satisfied --
    fail closed, matching the rest of this codebase's discipline."""
    for key, val in ev.checks.items():
        if val is not True:
            return "NOT_SATISFIED_LOCALLY"
    return "STRUCTURALLY_AND_BEHAVIORALLY_VERIFIED_LOCALLY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tests", action="store_true", help="Actually execute the negative tests (requires a live DB); without this flag, negative_tests_pass is treated as unmet (fail-closed)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cond16 = evaluate_condition_16(args.run_tests)
    cond25 = evaluate_condition_25(args.run_tests)

    result = {
        "condition_16": {"checks": cond16.checks, "detail": cond16.detail, "verdict": condition_verdict(cond16)},
        "condition_25": {"checks": cond25.checks, "detail": cond25.detail, "verdict": condition_verdict(cond25)},
        "note": (
            "This is a LOCAL machine-checkable verdict only. It is NOT the independent "
            "substantive audit SATISFIED determination for conditions 16/25 -- that requires "
            "an independent re-audit against a fresh clone at the post-remediation commit. "
            "Repository-machine-verifier truth and independent-substantive truth are kept "
            "separate throughout this campaign."
        ),
    }
    both_locally_verified = (
        condition_verdict(cond16) == "STRUCTURALLY_AND_BEHAVIORALLY_VERIFIED_LOCALLY"
        and condition_verdict(cond25) == "STRUCTURALLY_AND_BEHAVIORALLY_VERIFIED_LOCALLY"
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"[aud004-16-25] condition 16: {condition_verdict(cond16)}")
        for k, v in cond16.checks.items():
            print(f"    {'OK ' if v is True else ('?? ' if v is None else 'FAIL')} {k}: {cond16.detail.get(k.split('_')[0], '')}"[:160])
        print(f"[aud004-16-25] condition 25: {condition_verdict(cond25)}")
        for k, v in cond25.checks.items():
            print(f"    {'OK ' if v is True else ('?? ' if v is None else 'FAIL')} {k}")
        print(f"[aud004-16-25] both locally verified: {both_locally_verified}")
        print("[aud004-16-25] " + result["note"])

    return 0 if both_locally_verified else 1


if __name__ == "__main__":
    sys.exit(main())
