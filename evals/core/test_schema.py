"""
Tests for evaluation core schemas.
"""
import pytest
from datetime import datetime
from evals.core.schema import (
    BenchmarkManifest,
    EvalRunManifest,
    TrialRecord,
    GradingResult,
)
from calibration.uncertainty.schema import UncertaintySignal


class TestBenchmarkManifest:
    """Test benchmark manifest schema."""

    def test_valid_manifest(self):
        """Create valid benchmark manifest."""
        manifest = BenchmarkManifest(
            benchmark_id='simpleqa_v1',
            name='SimpleQA',
            description='Simple QA benchmark',
            task_type='free_form',
            dataset_uri='s3://bucket/simpleqa.jsonl',
            dataset_hash='a' * 64,
            dataset_version='v1',
            split='test',
            scorer_ids=['exact_match', 'semantic_similarity'],
            license='CC-BY-4.0',
            created_at=datetime.now(),
        )
        manifest.validate()  # Should not raise

    def test_invalid_task_type(self):
        """Reject invalid task type."""
        with pytest.raises(ValueError, match="task_type must be one of"):
            BenchmarkManifest(
                benchmark_id='test',
                name='Test',
                description='Test',
                task_type='invalid_task',
                dataset_uri='file://data',
                dataset_hash='a' * 64,
                dataset_version='v1',
                split='test',
                scorer_ids=[],
                license='MIT',
                created_at=datetime.now(),
            ).validate()

    def test_invalid_split(self):
        """Reject invalid split."""
        with pytest.raises(ValueError, match="split must be one of"):
            BenchmarkManifest(
                benchmark_id='test',
                name='Test',
                description='Test',
                task_type='binary_classification',
                dataset_uri='file://data',
                dataset_hash='a' * 64,
                dataset_version='v1',
                split='invalid',
                scorer_ids=[],
                license='MIT',
                created_at=datetime.now(),
            ).validate()

    def test_invalid_dataset_hash(self):
        """Reject invalid dataset hash (must be SHA256 hex)."""
        with pytest.raises(ValueError, match="dataset_hash must be SHA256"):
            BenchmarkManifest(
                benchmark_id='test',
                name='Test',
                description='Test',
                task_type='binary_classification',
                dataset_uri='file://data',
                dataset_hash='tooshort',
                dataset_version='v1',
                split='test',
                scorer_ids=[],
                license='MIT',
                created_at=datetime.now(),
            ).validate()

    def test_manifest_serialization(self):
        """Serialize and deserialize benchmark manifest."""
        now = datetime.now()
        original = BenchmarkManifest(
            benchmark_id='test',
            name='Test',
            description='Test',
            task_type='binary_classification',
            dataset_uri='file://data',
            dataset_hash='a' * 64,
            dataset_version='v1',
            split='test',
            scorer_ids=['exact_match'],
            license='MIT',
            created_at=now,
        )
        data = original.to_dict()
        reconstructed = BenchmarkManifest.from_dict(data)
        assert reconstructed.benchmark_id == original.benchmark_id
        assert reconstructed.created_at == original.created_at

    def test_manifest_hash(self):
        """Manifest hash is deterministic."""
        manifest = BenchmarkManifest(
            benchmark_id='test',
            name='Test',
            description='Test',
            task_type='binary_classification',
            dataset_uri='file://data',
            dataset_hash='a' * 64,
            dataset_version='v1',
            split='test',
            scorer_ids=['exact_match'],
            license='MIT',
            created_at=datetime(2024, 1, 1),
        )
        hash1 = manifest.manifest_hash()
        hash2 = manifest.manifest_hash()
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex


class TestEvalRunManifest:
    """Test evaluation run manifest schema."""

    def test_valid_run(self):
        """Create valid eval run manifest."""
        now = datetime.now()
        run = EvalRunManifest(
            run_id='run_001',
            benchmark_id='simpleqa_v1',
            commit_sha='abc123' + 'd' * 34,
            model_provider='openai',
            model_name='gpt-4',
            agent_id=None,
            agent_version=None,
            prompt_version='v1.0',
            tool_profile='full',
            temperature=0.7,
            top_p=0.9,
            max_tokens=1024,
            seed=42,
            started_at=now,
            completed_at=None,
            status='running',
        )
        run.validate()  # Should not raise

    def test_invalid_status(self):
        """Reject invalid status."""
        now = datetime.now()
        with pytest.raises(ValueError, match="status must be one of"):
            EvalRunManifest(
                run_id='run_001',
                benchmark_id='simpleqa_v1',
                commit_sha='a' * 40,
                model_provider='openai',
                model_name='gpt-4',
                agent_id=None,
                agent_version=None,
                prompt_version='v1.0',
                tool_profile='full',
                temperature=0.7,
                top_p=0.9,
                max_tokens=1024,
                seed=None,
                started_at=now,
                completed_at=None,
                status='invalid_status',
            ).validate()

    def test_invalid_temperature(self):
        """Reject invalid temperature."""
        now = datetime.now()
        with pytest.raises(ValueError, match="temperature must be in"):
            EvalRunManifest(
                run_id='run_001',
                benchmark_id='simpleqa_v1',
                commit_sha='a' * 40,
                model_provider='openai',
                model_name='gpt-4',
                agent_id=None,
                agent_version=None,
                prompt_version='v1.0',
                tool_profile='full',
                temperature=5.0,  # Invalid
                top_p=0.9,
                max_tokens=1024,
                seed=None,
                started_at=now,
                completed_at=None,
                status='running',
            ).validate()

    def test_run_serialization(self):
        """Serialize and deserialize eval run."""
        now = datetime.now()
        original = EvalRunManifest(
            run_id='run_001',
            benchmark_id='simpleqa_v1',
            commit_sha='a' * 40,
            model_provider='openai',
            model_name='gpt-4',
            agent_id='agent_1',
            agent_version='v1.0',
            prompt_version='v1.0',
            tool_profile='full',
            temperature=0.7,
            top_p=0.9,
            max_tokens=1024,
            seed=42,
            started_at=now,
            completed_at=None,
            status='running',
        )
        data = original.to_dict()
        reconstructed = EvalRunManifest.from_dict(data)
        assert reconstructed.run_id == original.run_id
        assert reconstructed.temperature == original.temperature


class TestTrialRecord:
    """Test trial record schema."""

    def test_valid_trial(self):
        """Create valid trial record."""
        now = datetime.now()
        trial = TrialRecord(
            trial_id='trial_001',
            run_id='run_001',
            benchmark_id='simpleqa_v1',
            task_id='task_001',
            input_payload={'question': 'What is 2+2?'},
            raw_output='4',
            parsed_output={'answer': 4},
            expected_output={'answer': 4},
            trace=None,
            tool_calls=[],
            uncertainty=UncertaintySignal(stated_confidence=0.9),
            grading_result={'correctness': True, 'score': 1.0},
            provenance={'git_sha': 'a' * 40},
            created_at=now,
        )
        assert trial.trial_id == 'trial_001'

    def test_trial_serialization(self):
        """Serialize and deserialize trial record."""
        now = datetime.now()
        original = TrialRecord(
            trial_id='trial_001',
            run_id='run_001',
            benchmark_id='simpleqa_v1',
            task_id='task_001',
            input_payload={'question': 'What is 2+2?'},
            raw_output='4',
            parsed_output={'answer': 4},
            expected_output={'answer': 4},
            trace=None,
            tool_calls=[],
            uncertainty=UncertaintySignal(stated_confidence=0.9),
            grading_result={'correctness': True, 'score': 1.0},
            provenance={'git_sha': 'a' * 40},
            created_at=now,
        )
        data = original.to_dict()
        reconstructed = TrialRecord.from_dict(data)
        assert reconstructed.trial_id == original.trial_id
        assert reconstructed.uncertainty is not None
        assert reconstructed.uncertainty.stated_confidence == 0.9


class TestGradingResult:
    """Test grading result schema."""

    def test_basic_grading(self):
        """Create basic grading result."""
        result = GradingResult(
            correctness=True,
            score=1.0,
        )
        assert result.correctness is True

    def test_grading_with_flags(self):
        """Create grading result with flags."""
        result = GradingResult(
            correctness=False,
            score=0.5,
            hallucination_flag=True,
            explanation='Answer contains hallucination',
        )
        assert result.hallucination_flag is True
        assert 'hallucination' in result.explanation.lower()

    def test_grading_serialization(self):
        """Serialize and deserialize grading result."""
        original = GradingResult(
            correctness=True,
            score=0.9,
            grader_version='1.2',
            rubric_version='2.0',
        )
        data = original.to_dict()
        reconstructed = GradingResult.from_dict(data)
        assert reconstructed.score == original.score
        assert reconstructed.grader_version == original.grader_version
