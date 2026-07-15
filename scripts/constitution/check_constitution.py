#!/usr/bin/env python3
"""Architecture Constitution drift checker.

Keeps constitution/ honest against the real repository, forever. Fails (exit 1) on:
  - duplicate invariant IDs, malformed IDs, or invalid tier/status enums
  - invariant with status=enforced but no enforcement entry
  - enforcement path that does not exist in the repo
  - volume header (number/name/tier/epistemic status/doc status) disagreeing with INDEX.md
  - volume missing any TEMPLATE.md section (charter tier: Header + Purpose only)
  - charter-tier volume longer than 120 lines
  - invariants mentioned in a volume but unregistered, or registered but absent
    from their (written) volume
  - INDEX rows marked "written" without a volume file, or volume files without an
    INDEX row

Stdlib + PyYAML only. See constitution/CONVENTIONS.md for the rules being enforced.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONSTITUTION = REPO_ROOT / "constitution"
VOLUMES_DIR = CONSTITUTION / "volumes"
REGISTRY = CONSTITUTION / "invariants.yaml"
INDEX = CONSTITUTION / "INDEX.md"

TIERS = {"constitutional", "statute", "regulation", "article", "charter"}
EPISTEMIC = {"descriptive", "mixed", "prescriptive", "aspirational"}
INV_STATUS = {"enforced", "planned", "aspirational"}
DOC_STATUS = {"not written", "in progress", "written"}
INV_ID = re.compile(r"^V(\d+)-INV-(\d{3})$")
INV_MENTION = re.compile(r"\bV(\d+)-INV-(\d{3})\b")

SECTIONS = [
    "## 1. Header",
    "## 2. Purpose",
    "## 3. Definitions",
    "## 4. Invariants",
    "## 5. Interfaces",
    "## 6. State",
    "## 7. Failure modes and responses",
    "## 8. Verification obligations",
    "## 9. Implementation mapping",
    "## 10. Open questions",
    "## 11. Change log",
]
CHARTER_SECTIONS = SECTIONS[:2]
CHARTER_MAX_LINES = 120

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def parse_index() -> dict[int, dict[str, str]]:
    """Parse the INDEX.md volume table into {vol: {name, tier, epistemic, doc_status}}."""
    rows: dict[int, dict[str, str]] = {}
    if not INDEX.exists():
        err(f"{INDEX.relative_to(REPO_ROOT)} is missing")
        return rows
    for line in INDEX.read_text().splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # Volume rows: | Order | Vol | Name | Tier | Epistemic | Doc status | Primary code |
        if len(cells) != 7 or not cells[0].isdigit() or not cells[1].isdigit():
            continue
        vol = int(cells[1])
        if vol in rows:
            err(f"INDEX.md: duplicate row for volume {vol}")
        rows[vol] = {
            "order": cells[0],
            "name": cells[2],
            "tier": cells[3],
            "epistemic": cells[4],
            "doc_status": cells[5],
        }
        if cells[3] not in TIERS:
            err(f"INDEX.md: volume {vol} has invalid tier '{cells[3]}'")
        if cells[4] not in EPISTEMIC:
            err(f"INDEX.md: volume {vol} has invalid epistemic status '{cells[4]}'")
        if cells[5] not in DOC_STATUS:
            err(f"INDEX.md: volume {vol} has invalid doc status '{cells[5]}'")
    if not rows:
        err("INDEX.md: no volume table rows found")
    return rows


def load_registry() -> list[dict]:
    if not REGISTRY.exists():
        err(f"{REGISTRY.relative_to(REPO_ROOT)} is missing")
        return []
    data = yaml.safe_load(REGISTRY.read_text()) or {}
    entries = data.get("invariants") or []
    if not isinstance(entries, list):
        err("invariants.yaml: 'invariants' must be a list")
        return []
    return entries


def check_registry(entries: list[dict]) -> dict[int, set[str]]:
    """Validate registry entries; return {volume: {ids}} for cross-checks."""
    seen: set[str] = set()
    by_vol: dict[int, set[str]] = {}
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            err(f"invariants.yaml entry #{i + 1}: not a mapping")
            continue
        inv_id = str(entry.get("id", ""))
        m = INV_ID.match(inv_id)
        if not m:
            err(f"invariants.yaml entry #{i + 1}: malformed id '{inv_id}'")
            continue
        if inv_id in seen:
            err(f"invariants.yaml: duplicate invariant id {inv_id}")
        seen.add(inv_id)
        by_vol.setdefault(int(m.group(1)), set()).add(inv_id)
        if not str(entry.get("statement", "")).strip():
            err(f"{inv_id}: missing statement")
        if entry.get("tier") not in TIERS:
            err(f"{inv_id}: invalid tier '{entry.get('tier')}'")
        status = entry.get("status")
        if status not in INV_STATUS:
            err(f"{inv_id}: invalid status '{status}'")
        enforcement = entry.get("enforcement") or []
        if status == "enforced" and not enforcement:
            err(f"{inv_id}: status is 'enforced' but no enforcement entries are listed")
        for ref in enforcement:
            path_part = str(ref).split("::", 1)[0].strip()
            if not (REPO_ROOT / path_part).exists():
                err(f"{inv_id}: enforcement path does not exist: {path_part}")
    return by_vol


def parse_header(text: str, rel: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    header_match = re.search(r"## 1\. Header\n(.*?)(?=\n## )", text, re.S)
    block = header_match.group(1) if header_match else text
    for key in ("Volume", "Name", "Tier", "Epistemic status", "Doc status"):
        m = re.search(rf"^\|\s*{re.escape(key)}\s*\|\s*(.+?)\s*\|", block, re.M)
        if m:
            fields[key] = m.group(1).strip()
        else:
            err(f"{rel}: header is missing the '{key}' row")
    return fields


def check_volumes(index: dict[int, dict[str, str]], registry_by_vol: dict[int, set[str]]) -> int:
    written_vols: set[int] = set()
    count = 0
    if VOLUMES_DIR.exists():
        for path in sorted(VOLUMES_DIR.glob("VOL-*.md")):
            count += 1
            rel = str(path.relative_to(REPO_ROOT))
            fname = re.match(r"VOL-(\d+)-", path.name)
            if not fname:
                err(f"{rel}: filename must match VOL-<NN>-<kebab-name>.md")
                continue
            vol = int(fname.group(1))
            text = path.read_text()
            lines = text.count("\n") + 1
            row = index.get(vol)
            if row is None:
                err(f"{rel}: volume {vol} has no row in INDEX.md")
                continue
            header = parse_header(text, rel)
            if header.get("Volume") not in (str(vol), f"{vol:02d}"):
                err(f"{rel}: header Volume '{header.get('Volume')}' != filename volume {vol}")
            for key, index_key in (("Name", "name"), ("Tier", "tier"),
                                   ("Epistemic status", "epistemic"), ("Doc status", "doc_status")):
                if key in header and header[key] != row[index_key]:
                    err(f"{rel}: header {key} '{header[key]}' disagrees with INDEX.md '{row[index_key]}'")
            tier = row["tier"]
            required = CHARTER_SECTIONS if tier == "charter" else SECTIONS
            pos = -1
            for section in required:
                found = text.find(section + "\n")
                if found < 0:
                    found = text.find(section) if text.rstrip().endswith(section) else -1
                if found < 0:
                    err(f"{rel}: missing required section '{section}'")
                elif found < pos:
                    err(f"{rel}: section '{section}' is out of order")
                else:
                    pos = found
            if tier == "charter" and lines > CHARTER_MAX_LINES:
                err(f"{rel}: charter volume is {lines} lines (max {CHARTER_MAX_LINES})")
            written_vols.add(vol)
            # Invariant cross-check: IDs of THIS volume mentioned in the file
            mentioned = {f"V{m.group(1)}-INV-{m.group(2)}" for m in INV_MENTION.finditer(text)
                         if int(m.group(1)) == vol}
            registered = registry_by_vol.get(vol, set())
            for inv in sorted(mentioned - registered):
                err(f"{rel}: invariant {inv} appears in the volume but is not registered in invariants.yaml")
            for inv in sorted(registered - mentioned):
                err(f"{rel}: invariant {inv} is registered but does not appear in the volume")
    # Registry entries for volumes that have no file at all
    for vol, ids in sorted(registry_by_vol.items()):
        if vol not in written_vols:
            err(f"invariants.yaml: {', '.join(sorted(ids))} registered but volume {vol} has no volume file")
    # INDEX doc-status consistency
    for vol, row in sorted(index.items()):
        if row["doc_status"] == "written" and vol not in written_vols:
            err(f"INDEX.md: volume {vol} is marked 'written' but constitution/volumes/ has no file for it")
        if row["doc_status"] == "not written" and vol in written_vols:
            err(f"INDEX.md: volume {vol} is marked 'not written' but a volume file exists")
    return count


def main() -> int:
    index = parse_index()
    entries = load_registry()
    registry_by_vol = check_registry(entries)
    volume_count = check_volumes(index, registry_by_vol)
    if errors:
        print(f"constitution check FAILED — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        return 1
    enforced = sum(1 for e in entries if e.get("status") == "enforced")
    planned = sum(1 for e in entries if e.get("status") == "planned")
    aspirational = sum(1 for e in entries if e.get("status") == "aspirational")
    written = sum(1 for r in index.values() if r["doc_status"] == "written")
    print(
        f"constitution check OK — {len(index)} volumes indexed, {written} written, "
        f"{volume_count} volume file(s); {len(entries)} invariants "
        f"({enforced} enforced / {planned} planned / {aspirational} aspirational)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
