from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V4_FREEZE.json"


def test_freeze_attestation_has_individual_file_inventory_when_present():
    if not FREEZE.exists():
        return
    data = json.loads(FREEZE.read_text())
    assert data["freeze_schema_version"] == "governed-capability-genesis-v4-freeze-v1"
    assert data["freeze_attestation_content_hash"]
    assert data["freeze_attestation_logical_hash"]
    assert len(data["frozen_files"]) >= 20
    assert all("path" in item and "blob_sha_at_candidate" in item and "sha256_at_candidate" in item for item in data["frozen_files"])


def test_candidate_content_hashing_is_independent_of_working_tree_when_present():
    if not FREEZE.exists():
        return
    data = json.loads(FREEZE.read_text())
    entry = data["frozen_files"][0]
    raw = subprocess.check_output(["git", "show", f"{data['freeze_candidate_sha']}:{entry['path']}"], cwd=ROOT)
    import hashlib

    assert hashlib.sha256(raw).hexdigest() == entry["sha256_at_candidate"]
