#!/usr/bin/env python3
"""AUD-006: migration naming/ordering governance.

The migration runner (backend/src/db/migrate.ts) applies every *.sql file in
backend/src/db/migrations/ in plain lexical filename order -- there is no other
ordering signal. Two files sharing the same numeric sequence prefix have their
relative execution order decided by alphabetical comparison of the rest of the
filename, not by design. If such a pair ever had a real dependency on each
other, that dependency's correctness would depend on which contributor's
filename happened to sort first -- entirely by accident.

This repo already has five such collisions (051, 058, 059, 129, 140) and one
filename that breaks the numeric-prefix convention outright
(052b_institutions.sql, a letter suffix used to insert between 052 and 053
without a renumbering cascade). Each was read in full and checked for real
cross-file references (shared table/column/type/function/role names) before
being grandfathered here; none had any -- see docs/audit/MIGRATION_GOVERNANCE.md
for the investigation. They are grandfathered by EXACT FILENAME, not by number
or by pattern, so a future collision cannot silently pass just because it
resembles one of these.

Enforces, for every migration file not in the grandfather lists:
  - filename matches ^\\d{3}_[a-z0-9_]+\\.sql$ exactly
  - its 3-digit sequence number is not shared with any other non-grandfathered
    file

Also fails if a grandfathered filename is missing from the directory (renamed
or deleted) -- silent drift out of a documented exception defeats the point of
documenting it.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "backend" / "src" / "db" / "migrations"

FILENAME_PATTERN = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")

# Pre-existing duplicate-numbered pairs, grandfathered by exact filename after
# investigation confirmed zero real cross-file dependency for each (see
# docs/audit/MIGRATION_GOVERNANCE.md). Do not add to this dict to silence a
# NEW collision -- rename the new file to an unused number instead. Adding an
# entry here is only for a pre-existing, already-applied, already-investigated
# pair.
GRANDFATHERED_DUPLICATE_NUMBERS: dict[str, set[str]] = {
    "051": {"051_fix_fk_constraints.sql", "051_team_activations.sql"},
    "058": {"058_adaptive_strategy.sql", "058_bounded_learning.sql"},
    "059": {"059_calibration_framework.sql", "059_governance_reputation_integration.sql"},
    "129": {"129_civilization_kernel.sql", "129_longitudinal_mission_evidence.sql"},
    "140": {"140_civilization_os.sql", "140_governed_capability_runtime.sql"},
}

# Pre-existing filename that breaks the numeric-prefix convention outright.
# Grandfathered as a named, one-off exception -- NOT a sanctioned convention;
# new migrations must not use a letter suffix (see docs/audit/MIGRATION_GOVERNANCE.md).
GRANDFATHERED_NONCONFORMING_FILENAMES: set[str] = {"052b_institutions.sql"}


def verify(migrations_dir: Path | None = None) -> list[str]:
    directory = migrations_dir or MIGRATIONS_DIR
    findings: list[str] = []
    files = sorted(f.name for f in directory.glob("*.sql"))
    present = set(files)
    # The 3-digit prefixes actually represented in the scanned directory. Used to scope the
    # "grandfathered file missing" check to entries relevant to THIS directory -- a synthetic
    # (e.g. test) directory that legitimately doesn't include migration 051 at all is not
    # "missing" the 051 pair; it's simply out of scope for that check.
    prefixes_present = {name[:3] for name in files}

    by_number: dict[str, list[str]] = {}
    for filename in files:
        if filename in GRANDFATHERED_NONCONFORMING_FILENAMES:
            continue
        if not FILENAME_PATTERN.match(filename):
            findings.append(f"NONCONFORMING_FILENAME:{filename}")
            continue
        number = filename[:3]
        by_number.setdefault(number, []).append(filename)

    for number, names in sorted(by_number.items()):
        if len(names) <= 1:
            continue
        grandfathered = GRANDFATHERED_DUPLICATE_NUMBERS.get(number)
        if grandfathered is not None and set(names) == grandfathered:
            continue
        findings.append(f"DUPLICATE_SEQUENCE_NUMBER:{number}:{','.join(sorted(names))}")

    for number, names in GRANDFATHERED_DUPLICATE_NUMBERS.items():
        if number not in prefixes_present:
            continue
        missing = names - present
        if missing:
            findings.append(f"GRANDFATHERED_FILE_MISSING:{number}:{','.join(sorted(missing))}")
    for name in GRANDFATHERED_NONCONFORMING_FILENAMES:
        if name[:3] not in prefixes_present or name in present:
            continue
        findings.append(f"GRANDFATHERED_FILE_MISSING:nonconforming:{name}")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="kept for Makefile convention consistency; verification always runs")
    parser.add_argument("--migrations-dir")
    args = parser.parse_args()
    findings = verify(Path(args.migrations_dir) if args.migrations_dir else None)
    print(json.dumps({"success": not findings, "findings": findings}, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
