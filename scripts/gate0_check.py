#!/usr/bin/env python3
"""GATE 0 repository checks that do not require external services."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "backend" / "src" / "db" / "migrations"
PRODUCT_SURFACES = [
    ROOT / "README.md",
    ROOT / "frontend" / "src",
    ROOT / "backend" / "src",
]
LEGACY_PATTERNS = [
    re.compile(r"autonomous AI company", re.IGNORECASE),
    re.compile(r"fully autonomous", re.IGNORECASE),
    re.compile(r"all 29 agents", re.IGNORECASE),
]


def iter_files(path: Path):
    if path.is_file():
        yield path
        return
    for child in path.rglob("*"):
        if child.is_file() and child.suffix in {".md", ".ts", ".tsx", ".js", ".jsx"}:
            yield child


def check_unique_migration_numbers() -> list[str]:
    seen: dict[str, Path] = {}
    errors: list[str] = []
    for migration in sorted(MIGRATIONS.glob("*.sql")):
        match = re.match(r"^(\d+)_", migration.name)
        if not match:
            errors.append(f"Migration lacks numeric prefix: {migration}")
            continue
        prefix = match.group(1)
        if prefix in seen:
            errors.append(
                f"Duplicate migration prefix {prefix}: {seen[prefix].name} and {migration.name}"
            )
        seen[prefix] = migration
    return errors


def check_product_surfaces() -> list[str]:
    errors: list[str] = []
    for surface in PRODUCT_SURFACES:
        for file_path in iter_files(surface):
            rel = file_path.relative_to(ROOT)
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for pattern in LEGACY_PATTERNS:
                if pattern.search(text):
                    errors.append(f"Legacy present-tense product claim in {rel}: {pattern.pattern}")
    return errors


def main() -> int:
    errors = [*check_unique_migration_numbers(), *check_product_surfaces()]
    if errors:
        print("GATE 0 check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("GATE 0 check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
