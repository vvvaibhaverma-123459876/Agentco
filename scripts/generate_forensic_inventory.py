#!/usr/bin/env python3
"""Generate a tracked-file forensic inventory for audit/remediation work."""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "docs" / "audit" / "FORENSIC_FILE_INVENTORY.json"
OUT_MD = ROOT / "docs" / "audit" / "FORENSIC_FILE_INVENTORY.md"


def git_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def classify(path: str) -> str:
    parts = path.split("/")
    name = parts[-1]
    top = parts[0]

    if top in {"docs"} or path.endswith((".md", ".txt")) and top in {"audit_artifacts", "reports", "results"}:
        return "Documentation"
    if top in {"reports", "results", "outputs", "validation"}:
        return "Generated artifact"
    if top in {"audit_artifacts"}:
        return "Generated artifact"
    if top in {"archive"}:
        return "Deprecated code"
    if top in {"backend"}:
        if "/tests/" in path or path.startswith("backend/tests/"):
            return "Test infrastructure"
        if path.startswith("backend/src/db/migrations/"):
            return "Database migration"
        if name in {"Dockerfile", "package.json", "package-lock.json", "jest.config.ts", "tsconfig.json"}:
            return "Development tooling"
        return "Production runtime code"
    if top in {"frontend", "dashboard"}:
        if name in {"Dockerfile", "package.json", "package-lock.json", "tsconfig.json", "eslint.config.mjs", ".eslintrc.json"}:
            return "Development tooling"
        return "Production runtime code"
    if top in {"runtime", "agents", "autonomy", "civilization", "calibration", "learning", "synthesis", "reserve", "governance", "provenance", "memory_kernel", "self_modification", "ingestion", "foundry", "institutions", "agentco_security"}:
        if "/tests/" in path or name.startswith("test_") or path.endswith(".test.ts"):
            return "Test infrastructure"
        if "/migrations/" in path or name.endswith(".sql"):
            return "Database migration"
        if "/prompts/" in path:
            return "Prompt/template"
        return "Production runtime code"
    if top in {"tests"} or name.startswith("test_"):
        return "Test infrastructure"
    if top in {"scripts"}:
        if name.startswith("test_"):
            return "Test infrastructure"
        return "Development tooling"
    if top in {"infrastructure", ".github"} or name.startswith("docker-compose"):
        return "Deployment infrastructure"
    if top in {"requirements"} or name in {"Makefile", "pytest.ini", "pyproject.toml"}:
        return "Development tooling"
    if top in {"evals", "simulation", "data"}:
        if "/tests/" in path or name.startswith("test_"):
            return "Test infrastructure"
        if top == "data":
            return "Generated artifact"
        return "Experimental code"
    if name in {"LICENSE", ".gitignore", ".python-version"} or name.startswith(".env"):
        return "Development tooling"
    return "Unknown purpose"


def main() -> int:
    files = git_files()
    by_category: dict[str, list[str]] = defaultdict(list)
    by_top = Counter()
    extensions = Counter()
    inventory = []

    for path in files:
        category = classify(path)
        by_category[category].append(path)
        by_top[path.split("/", 1)[0]] += 1
        suffix = Path(path).suffix or "(none)"
        extensions[suffix] += 1
        inventory.append({
            "path": path,
            "category": category,
            "top_level": path.split("/", 1)[0],
            "extension": suffix,
        })

    payload = {
        "generated_by": "scripts/generate_forensic_inventory.py",
        "tracked_file_count": len(files),
        "category_counts": {k: len(v) for k, v in sorted(by_category.items())},
        "top_level_counts": dict(by_top.most_common()),
        "extension_counts": dict(extensions.most_common()),
        "files": inventory,
    }
    json_text = json.dumps(payload, indent=2) + "\n"

    lines = [
        "# Forensic File Inventory",
        "",
        "Machine-derived inventory of tracked files. Generated from `git ls-files`; untracked local caches and dependency directories are intentionally excluded.",
        "",
        f"- Tracked files: `{len(files)}`",
        "",
        "## Category Counts",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    for category, count in sorted(payload["category_counts"].items()):
        lines.append(f"| {category} | {count} |")
    lines.extend(["", "## Top-Level Counts", "", "| Path | Count |", "|---|---:|"])
    for top, count in by_top.most_common():
        lines.append(f"| `{top}` | {count} |")
    lines.extend(["", "## Full File Ledger", "", "| Path | Category |", "|---|---|"])
    for item in inventory:
        lines.append(f"| `{item['path']}` | {item['category']} |")
    md_text = "\n".join(lines) + "\n"
    if "--check" in sys.argv:
        stale = []
        if not OUT_JSON.exists() or OUT_JSON.read_text(encoding="utf-8") != json_text:
            stale.append(str(OUT_JSON.relative_to(ROOT)))
        if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != md_text:
            stale.append(str(OUT_MD.relative_to(ROOT)))
        if stale:
            print(f"forensic inventory stale: {', '.join(stale)}")
            return 2
        print("forensic inventory current")
        return 0
    OUT_JSON.write_text(json_text, encoding="utf-8")
    OUT_MD.write_text(md_text, encoding="utf-8")

    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
