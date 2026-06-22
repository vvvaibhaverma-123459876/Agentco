"""
Tests for benchmark registry.
"""
import pytest
from pathlib import Path
from evals.registry.registry import BenchmarkRegistry, get_registry, list_benchmarks


class TestBenchmarkRegistry:
    """Test benchmark registry."""

    def test_registry_loads_benchmarks(self):
        """Registry loads benchmarks from YAML."""
        registry = BenchmarkRegistry()
        benchmarks = registry.list_benchmarks()
        assert len(benchmarks) > 0
        assert 'simpleqa_sample' in benchmarks

    def test_get_benchmark_by_id(self):
        """Get benchmark manifest by ID."""
        registry = BenchmarkRegistry()
        benchmark = registry.get_benchmark('simpleqa_sample')
        assert benchmark is not None
        assert benchmark.benchmark_id == 'simpleqa_sample'
        assert benchmark.name == 'SimpleQA Sample'
        assert benchmark.task_type == 'free_form'

    def test_get_nonexistent_benchmark(self):
        """Nonexistent benchmark returns None."""
        registry = BenchmarkRegistry()
        benchmark = registry.get_benchmark('nonexistent')
        assert benchmark is None

    def test_load_dataset_simpleqa(self):
        """Load SimpleQA dataset."""
        registry = BenchmarkRegistry()
        tasks = registry.load_dataset('file://evals/registry/datasets/simpleqa_sample.jsonl')
        assert len(tasks) == 10
        assert tasks[0]['task_id'] == 'simpleqa_1'
        assert 'question' in tasks[0]
        assert 'expected_output' in tasks[0]

    def test_load_dataset_truthfulqa(self):
        """Load TruthfulQA dataset."""
        registry = BenchmarkRegistry()
        tasks = registry.load_dataset('file://evals/registry/datasets/truthfulqa_sample.jsonl')
        assert len(tasks) == 10
        assert tasks[0]['task_id'] == 'tqa_1'

    def test_load_dataset_halueval(self):
        """Load HaluEval dataset."""
        registry = BenchmarkRegistry()
        tasks = registry.load_dataset('file://evals/registry/datasets/halueval_sample.jsonl')
        assert len(tasks) == 10
        assert tasks[0]['task_id'] == 'hal_1'

    def test_benchmark_manifest_validation(self):
        """Benchmark manifest passes validation."""
        registry = BenchmarkRegistry()
        benchmark = registry.get_benchmark('simpleqa_sample')
        benchmark.validate()  # Should not raise

    def test_global_registry_functions(self):
        """Global registry functions work."""
        benchmarks = list_benchmarks()
        assert len(benchmarks) > 0
        assert 'simpleqa_sample' in benchmarks

    def test_load_nonexistent_dataset_raises(self):
        """Loading nonexistent dataset raises error."""
        registry = BenchmarkRegistry()
        with pytest.raises(FileNotFoundError):
            registry.load_dataset('file://nonexistent.jsonl')

    def test_benchmark_has_scorers(self):
        """Benchmark includes scorer IDs."""
        registry = BenchmarkRegistry()
        benchmark = registry.get_benchmark('simpleqa_sample')
        assert benchmark.scorer_ids is not None
        assert len(benchmark.scorer_ids) > 0
