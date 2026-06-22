"""
Tests for evaluation runner and fake model.
"""
import pytest
from evals.core.runner import EvaluationRunner, FakeModel


class TestFakeModel:
    """Test fake model for testing without LLM credentials."""

    def test_fake_model_deterministic(self):
        """Fake model produces deterministic outputs."""
        model = FakeModel(seed=42)
        output1, uncertainty1 = model.predict("What is the capital of France?")
        output2, uncertainty2 = model.predict("What is the capital of France?")
        assert output1 == output2
        assert uncertainty1.stated_confidence == uncertainty2.stated_confidence

    def test_fake_model_paris_prediction(self):
        """Fake model recognizes Paris question."""
        model = FakeModel(seed=42)
        output, uncertainty = model.predict("What is the capital of France?")
        assert output == 'Paris'
        assert uncertainty.stated_confidence > 0.9

    def test_fake_model_math_prediction(self):
        """Fake model recognizes math question."""
        model = FakeModel(seed=42)
        output, uncertainty = model.predict("What is 2 + 2?")
        assert output == '4'
        assert uncertainty.stated_confidence > 0.95

    def test_fake_model_returns_uncertainty(self):
        """Fake model returns uncertainty signal."""
        model = FakeModel()
        output, uncertainty = model.predict("Some question")
        assert output is not None
        assert uncertainty is not None
        assert 0.0 <= uncertainty.stated_confidence <= 1.0


class TestEvaluationRunner:
    """Test evaluation runner."""

    def test_runner_initialization(self):
        """Initialize runner with valid benchmark."""
        runner = EvaluationRunner(
            benchmark_id='simpleqa_sample',
            model_name='fake',
        )
        assert runner.benchmark is not None
        assert runner.model_name == 'fake'
        assert runner.run_id is not None

    def test_runner_invalid_benchmark(self):
        """Invalid benchmark raises error."""
        with pytest.raises(ValueError, match="Unknown benchmark"):
            EvaluationRunner(
                benchmark_id='nonexistent_benchmark',
                model_name='fake',
            )

    def test_runner_smoke_test(self):
        """Run evaluation on sample benchmark."""
        runner = EvaluationRunner(
            benchmark_id='simpleqa_sample',
            model_name='fake',
            seed=42,
        )
        summary = runner.run(dry_run=True, limit=5)

        assert summary['run_id'] == runner.run_id
        assert summary['status'] == 'completed'
        assert summary['n_trials'] == 5
        assert 0.0 <= summary['accuracy'] <= 1.0
        assert summary['avg_confidence'] is not None

    def test_runner_computes_accuracy(self):
        """Runner computes accuracy correctly."""
        runner = EvaluationRunner(
            benchmark_id='simpleqa_sample',
            model_name='fake',
        )
        summary = runner.run(dry_run=True, limit=3)

        # Some trials should be graded
        assert summary['n_trials'] > 0
        assert 'accuracy' in summary

    def test_runner_collects_trials(self):
        """Runner collects trial records."""
        runner = EvaluationRunner(
            benchmark_id='simpleqa_sample',
            model_name='fake',
        )
        runner.run(dry_run=True, limit=2)

        assert len(runner.trials) == 2
        for trial in runner.trials:
            assert trial.trial_id is not None
            assert trial.run_id == runner.run_id
            assert trial.grading_result is not None

    def test_runner_generates_report(self):
        """Runner generates comprehensive report."""
        runner = EvaluationRunner(
            benchmark_id='simpleqa_sample',
            model_name='fake',
        )
        runner.run(dry_run=True, limit=3)
        report = runner.report()

        assert 'run_manifest' in report
        assert 'benchmark_manifest' in report
        assert 'summary' in report
        assert report['n_trials_persisted'] == 3

    def test_runner_with_temperature_and_seed(self):
        """Runner accepts temperature and seed parameters."""
        runner = EvaluationRunner(
            benchmark_id='simpleqa_sample',
            model_name='fake',
            temperature=0.5,
            top_p=0.95,
            seed=123,
        )
        assert runner.temperature == 0.5
        assert runner.top_p == 0.95
        assert runner.seed == 123

    def test_runner_with_agent_id(self):
        """Runner can be associated with an agent."""
        runner = EvaluationRunner(
            benchmark_id='simpleqa_sample',
            model_name='fake',
            agent_id='agent_123',
        )
        assert runner.agent_id == 'agent_123'
        assert runner.run_manifest.agent_id == 'agent_123'
