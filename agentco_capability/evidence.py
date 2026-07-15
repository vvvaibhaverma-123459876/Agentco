from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(data: str) -> str:
    return sha256_bytes(data.encode())


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def canonical_file_rows(paths: Iterable[Path]) -> list[dict[str, Any]]:
    return [
        {"path": relative(path), "sha256": file_hash(path), "size_bytes": path.stat().st_size}
        for path in sorted({path.resolve() for path in paths})
        if path.is_file()
    ]


def bundle_hash(paths: Iterable[Path]) -> str:
    return sha256_text(canonical_json(canonical_file_rows(paths)))


def files_under(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file())
    return sorted(files)


def dependency_lock_hash() -> str:
    paths = [
        ROOT / "requirements" / "requirements.lock.txt",
        ROOT / "backend" / "package-lock.json",
        ROOT / "frontend" / "package-lock.json",
    ]
    return bundle_hash(path for path in paths if path.exists())


def environment_contract_hash() -> str:
    contract = {
        "python_major_minor": ".".join(map(str, os.sys.version_info[:2])),
        "provider_secret_source": "environment_or_secret_store",
        "network_default": "disabled_for_protocol_reference",
        "hosted_staging": "blocked_unverified",
        "protocol": "agentco-capability-v1",
    }
    return sha256_text(canonical_json(contract))


def payload_manifest(
    artifact: Path,
    included_files: Iterable[Path],
    *,
    campaign_execution_sha: str,
    workflow_head_sha: str,
    campaign_id: str,
    freeze_attestation_sha: str | None,
    hash_fields: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    rows = [
        {"path": str(path.resolve().relative_to(artifact.resolve())), "sha256": file_hash(path), "size_bytes": path.stat().st_size}
        for path in sorted({path.resolve() for path in included_files})
        if path.is_file()
    ]
    aggregate = sha256_text(canonical_json(rows))
    manifest = {
        "canonicalization_version": "agentco-capability-payload-v2",
        "included_relative_paths": rows,
        "excluded_paths": [
            {"path": "INTERNAL_PAYLOAD_MANIFEST.json", "reason": "contains aggregate payload hash"},
            {"path": "*GENESIS*_MANIFEST.json", "reason": "contains internal payload manifest hash"},
        ],
        "aggregate_payload_hash": aggregate,
        "internal_payload_manifest_hash": aggregate,
        "campaign_execution_sha": campaign_execution_sha,
        "workflow_head_sha": workflow_head_sha,
        "campaign_id": campaign_id,
        "freeze_attestation_sha": freeze_attestation_sha,
        "generation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **hash_fields,
    }
    return manifest, aggregate


def reproduce_payload_hash(manifest: dict[str, Any], artifact: Path) -> str:
    rows = []
    for row in manifest["included_relative_paths"]:
        path = artifact / row["path"]
        rows.append({"path": row["path"], "sha256": file_hash(path), "size_bytes": path.stat().st_size})
    return sha256_text(canonical_json(rows))
