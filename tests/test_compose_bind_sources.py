from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _local_bind_sources(compose_file: str) -> list[Path]:
    data = yaml.safe_load((ROOT / compose_file).read_text())
    sources: list[Path] = []
    for service in data.get("services", {}).values():
        for volume in service.get("volumes", []) or []:
            if isinstance(volume, str):
                source = volume.split(":", 1)[0]
                if source.startswith("./") or source.startswith("../") or source.startswith("/"):
                    sources.append((ROOT / source).resolve() if not source.startswith("/") else Path(source))
            elif isinstance(volume, dict) and volume.get("type") == "bind":
                source = volume.get("source")
                if source:
                    sources.append((ROOT / source).resolve() if not source.startswith("/") else Path(source))
    return sources


def test_local_compose_bind_sources_exist():
    missing = [path for path in _local_bind_sources("docker-compose.yml") if not path.exists()]

    assert missing == []
