from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_MANIFEST.json"
BINDING = ROOT / "docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_BINDING.json"


def test_binding_uses_distinct_candidate_manifest_and_binding_commits_when_present():
    if not MANIFEST.exists() or not BINDING.exists():
        return
    manifest = json.loads(MANIFEST.read_text())
    binding = json.loads(BINDING.read_text())
    commits = [
        manifest["freeze_candidate_sha"],
        binding["freeze_manifest_commit_sha"],
        subprocess.check_output(["git", "log", "--reverse", "--format=%H", "--", str(BINDING.relative_to(ROOT))], cwd=ROOT, text=True).splitlines()[0],
    ]
    assert len(set(commits)) == 3


def test_binding_references_exact_manifest_blob_when_present():
    if not MANIFEST.exists() or not BINDING.exists():
        return
    binding = json.loads(BINDING.read_text())
    blob = subprocess.check_output(["git", "rev-parse", f"{binding['freeze_manifest_commit_sha']}:{MANIFEST.relative_to(ROOT)}"], cwd=ROOT, text=True).strip()
    assert blob == binding["freeze_manifest_blob_sha"]

