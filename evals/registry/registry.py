"""
Benchmark Registry — load and manage benchmark manifests.

Provides access to benchmark specifications from YAML/JSON configuration files
and sample datasets for evaluation.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

import yaml

from evals.core.schema import BenchmarkManifest

logger = logging.getLogger(__name__)


class BenchmarkRegistry:
    """Registry for loading benchmark manifests."""

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize registry.

        Args:
            registry_path: Path to benchmarks.yaml. Defaults to evals/registry/benchmarks.yaml
        """
        if registry_path is None:
            registry_path = Path(__file__).parent / 'benchmarks.yaml'

        self.registry_path = registry_path
        self._benchmarks: dict[str, dict] = {}
        self._loaded = False
        self._load()

    def _load(self):
        """Load benchmarks from YAML."""
        if not self.registry_path.exists():
            logger.warning(f"Registry file not found: {self.registry_path}")
            self._loaded = True
            return

        with open(self.registry_path) as f:
            data = yaml.safe_load(f)

        benchmarks = data.get('benchmarks', {})
        for benchmark_id, spec in benchmarks.items():
            self._benchmarks[benchmark_id] = spec
        logger.info(f"Loaded {len(self._benchmarks)} benchmarks from {self.registry_path}")
        self._loaded = True

    def get_benchmark(self, benchmark_id: str) -> Optional[BenchmarkManifest]:
        """
        Get benchmark manifest by ID.

        Resolves dataset hash and creates manifest.
        """
        if not self._loaded:
            self._load()

        spec = self._benchmarks.get(benchmark_id)
        if not spec:
            return None

        # Compute dataset hash if not provided
        dataset_hash = spec.get('dataset_hash')
        if not dataset_hash:
            dataset_hash = self._compute_dataset_hash(spec['dataset_uri'])

        from datetime import datetime, timezone
        manifest = BenchmarkManifest(
            benchmark_id=benchmark_id,
            name=spec['name'],
            description=spec['description'],
            task_type=spec['task_type'],
            dataset_uri=spec['dataset_uri'],
            dataset_hash=dataset_hash,
            dataset_version=spec.get('dataset_version', 'v1'),
            split=spec['split'],
            scorer_ids=spec.get('scorer_ids', []),
            license=spec.get('license', 'unknown'),
            created_at=datetime.now(timezone.utc),
            metadata=spec.get('metadata', {}),
        )
        manifest.validate()
        return manifest

    def list_benchmarks(self) -> list[str]:
        """List all registered benchmark IDs."""
        if not self._loaded:
            self._load()
        return list(self._benchmarks.keys())

    def load_dataset(self, dataset_uri: str) -> list[dict]:
        """
        Load dataset from URI.

        Supports file:// URIs pointing to JSONL files.
        """
        if not dataset_uri.startswith('file://'):
            raise ValueError(f"Only file:// URIs supported, got {dataset_uri}")

        file_path = Path(dataset_uri[7:])  # Remove 'file://' prefix
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        tasks = []
        with open(file_path) as f:
            for line in f:
                if line.strip():
                    tasks.append(json.loads(line))
        return tasks

    def _compute_dataset_hash(self, dataset_uri: str) -> str:
        """Compute SHA256 hash of dataset."""
        try:
            tasks = self.load_dataset(dataset_uri)
            canonical = json.dumps(tasks, sort_keys=True)
            return hashlib.sha256(canonical.encode()).hexdigest()
        except Exception as e:
            logger.warning(f"Could not compute dataset hash for {dataset_uri}: {e}")
            return 'x' * 64  # Placeholder


# Global registry instance
_default_registry: Optional[BenchmarkRegistry] = None


def get_registry() -> BenchmarkRegistry:
    """Get global registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = BenchmarkRegistry()
    return _default_registry


def get_benchmark(benchmark_id: str) -> Optional[BenchmarkManifest]:
    """Get benchmark by ID from global registry."""
    return get_registry().get_benchmark(benchmark_id)


def list_benchmarks() -> list[str]:
    """List benchmarks from global registry."""
    return get_registry().list_benchmarks()


def load_benchmark_dataset(benchmark_id: str) -> list[dict]:
    """Load dataset for benchmark."""
    benchmark = get_benchmark(benchmark_id)
    if not benchmark:
        raise ValueError(f"Unknown benchmark: {benchmark_id}")
    return get_registry().load_dataset(benchmark.dataset_uri)
