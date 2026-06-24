"""
Evaluation Runner — orchestrates benchmark execution and result persistence.

Executes evaluation runs, captures outputs with uncertainty and provenance,
grades trials, and persists results for analysis.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from evals.core.graders import GraderRegistry
from evals.core.schema import (
    BenchmarkManifest,
    EvalRunManifest,
    GradingResult,
    TrialRecord,
)
from evals.registry.registry import BenchmarkRegistry, get_benchmark
from calibration.uncertainty.schema import UncertaintySignal

logger = logging.getLogger(__name__)


class FakeModel:
    """Fake model for testing without external LLM credentials."""

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or 42

    def predict(self, prompt: str, **kwargs) -> tuple[str, UncertaintySignal]:
        """
        Generate fake but deterministic prediction.

        Returns (output, uncertainty_signal)
        """
        # Deterministic "prediction" based on prompt hash
        import hashlib
        prompt_hash = int(hashlib.md5(prompt.encode()).hexdigest(), 16)

        # Simple heuristic: if prompt contains certain keywords, return plausible answer
        lower_prompt = prompt.lower()

        if 'capital of france' in lower_prompt:
            return 'Paris', UncertaintySignal(stated_confidence=0.95)
        if '2 + 2' in lower_prompt or 'two plus two' in lower_prompt:
            return '4', UncertaintySignal(stated_confidence=0.99)
        if 'romeo and juliet' in lower_prompt:
            return 'William Shakespeare', UncertaintySignal(stated_confidence=0.92)

        # Default: random plausible answer
        options = ['Answer A', 'Answer B', 'Answer C', 'Unknown']
        choice_idx = (prompt_hash % len(options))
        confidence = 0.5 + (prompt_hash % 50) / 100.0  # 0.5-1.0
        return options[choice_idx], UncertaintySignal(stated_confidence=min(confidence, 1.0))


class EvaluationRunner:
    """Runs benchmarks and collects trial results."""

    def __init__(
        self,
        benchmark_id: str,
        model_name: str = 'fake',
        model_provider: str = 'fake',
        agent_id: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 1024,
        seed: Optional[int] = None,
        db_connection = None,
    ):
        """
        Initialize evaluation runner.

        Args:
            benchmark_id: Which benchmark to run
            model_name: Model name ('fake' for testing)
            model_provider: Model provider
            agent_id: Optional agent ID
            temperature: Temperature parameter
            top_p: Top-p parameter
            max_tokens: Max tokens to generate
            seed: Random seed
            db_connection: Optional database connection for persistence
        """
        self.benchmark_id = benchmark_id
        self.model_name = model_name
        self.model_provider = model_provider
        self.agent_id = agent_id
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.seed = seed
        self.db_connection = db_connection

        # Load benchmark
        self.registry = BenchmarkRegistry()
        self.benchmark = self.registry.get_benchmark(benchmark_id)
        if not self.benchmark:
            raise ValueError(f"Unknown benchmark: {benchmark_id}")

        # Create run manifest
        self.run_id = f"run_{uuid.uuid4().hex[:12]}"
        self.commit_sha = self._get_commit_sha()
        self.started_at = datetime.now(timezone.utc)
        self.run_manifest = EvalRunManifest(
            run_id=self.run_id,
            benchmark_id=benchmark_id,
            commit_sha=self.commit_sha,
            model_provider=model_provider,
            model_name=model_name,
            agent_id=agent_id,
            agent_version='1.0',
            prompt_version='1.0',
            tool_profile='none',
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed,
            started_at=self.started_at,
            completed_at=None,
            status='pending',
        )

        # Initialize model
        if model_name == 'fake':
            self.model = FakeModel(seed=seed)
        else:
            raise ValueError(f"Model '{model_name}' not yet implemented")

        self.trials: list[TrialRecord] = []

    def run(self, dry_run: bool = False, limit: Optional[int] = None) -> dict:
        """
        Run the evaluation.

        Args:
            dry_run: If True, don't persist to database
            limit: Limit number of trials (for testing)

        Returns:
            Summary dict with run statistics
        """
        logger.info(f"Starting run {self.run_id} on benchmark {self.benchmark_id}")

        # Load dataset
        try:
            tasks = self.registry.load_dataset(self.benchmark.dataset_uri)
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            return {'error': str(e), 'run_id': self.run_id}

        if limit:
            tasks = tasks[:limit]

        # Mark run as running
        self.run_manifest.status = 'running'

        # Execute trials
        for task in tasks:
            trial = self._execute_trial(task)
            self.trials.append(trial)

            if not dry_run:
                self._persist_trial(trial)

        # Mark run as completed
        self.run_manifest.completed_at = datetime.now(timezone.utc)
        self.run_manifest.status = 'completed'

        # Compute summary
        summary = self._compute_summary()
        logger.info(f"Run {self.run_id} completed: {summary}")

        return summary

    def _execute_trial(self, task: dict) -> TrialRecord:
        """Execute a single trial."""
        task_id = task.get('task_id', f'task_{len(self.trials)}')
        input_payload = task

        # Format prompt
        if 'question' in task:
            prompt = task['question']
        else:
            prompt = json.dumps(task)

        # Get model prediction
        try:
            output, uncertainty = self.model.predict(prompt)
        except Exception as e:
            logger.error(f"Model error on {task_id}: {e}")
            output = 'ERROR'
            uncertainty = UncertaintySignal(
                abstained=True,
                abstain_reason='model_error',
            )

        # Get expected output
        expected_output = task.get('expected_output', {})
        if isinstance(expected_output, str):
            expected_output = {'answer': expected_output}

        # Grade
        grader_id = self.benchmark.scorer_ids[0] if self.benchmark.scorer_ids else 'exact_match'
        grader = GraderRegistry.get_grader(grader_id)
        grading_result = grader.grade(output, expected_output)

        # Create trial record
        trial = TrialRecord(
            trial_id=f"trial_{uuid.uuid4().hex[:12]}",
            run_id=self.run_id,
            benchmark_id=self.benchmark_id,
            task_id=task_id,
            input_payload=input_payload,
            raw_output=output,
            parsed_output={'answer': output},
            expected_output=expected_output,
            trace=None,
            tool_calls=[],
            uncertainty=uncertainty,
            grading_result=asdict(grading_result),
            provenance={
                'git_sha': self.commit_sha,
                'model': self.model_name,
                'grader': grader_id,
            },
            created_at=datetime.now(timezone.utc),
        )

        return trial

    def _persist_trial(self, trial: TrialRecord):
        """Persist trial to database."""
        if not self.db_connection:
            logger.debug(f"No DB connection, skipping persistence for {trial.trial_id}")
            return

        try:
            # Insert trial record
            cursor = self.db_connection.cursor()
            trial_data = trial.to_dict()
            cursor.execute("""
                INSERT INTO trial_records (
                    trial_id, run_id, benchmark_id, task_id,
                    input_payload, raw_output, parsed_output, expected_output,
                    trace, tool_calls, uncertainty, grading_result, provenance
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                trial.trial_id,
                trial.run_id,
                trial.benchmark_id,
                trial.task_id,
                json.dumps(trial.input_payload),
                trial.raw_output,
                json.dumps(trial.parsed_output),
                json.dumps(trial.expected_output),
                json.dumps(trial.trace),
                json.dumps(trial.tool_calls),
                json.dumps(trial_data['uncertainty']),
                json.dumps(trial.grading_result),
                json.dumps(trial.provenance),
            ))
            self.db_connection.commit()
        except Exception as e:
            logger.error(f"Failed to persist trial {trial.trial_id}: {e}")

    def _compute_summary(self) -> dict:
        """Compute run summary statistics."""
        if not self.trials:
            return {
                'run_id': self.run_id,
                'benchmark_id': self.benchmark_id,
                'status': 'completed',
                'n_trials': 0,
                'accuracy': 0.0,
            }

        correct = sum(1 for t in self.trials if t.grading_result.get('correctness', False))
        accuracy = correct / len(self.trials) if self.trials else 0.0

        avg_confidence = None
        confidences = [
            t.uncertainty.stated_confidence
            for t in self.trials
            if t.uncertainty and t.uncertainty.stated_confidence is not None
        ]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)

        return {
            'run_id': self.run_id,
            'benchmark_id': self.benchmark_id,
            'model_name': self.model_name,
            'status': self.run_manifest.status,
            'n_trials': len(self.trials),
            'n_correct': correct,
            'accuracy': round(accuracy, 3),
            'avg_confidence': round(avg_confidence, 3) if avg_confidence else None,
            'duration_seconds': (
                (self.run_manifest.completed_at or datetime.now(timezone.utc)) - self.started_at
            ).total_seconds(),
        }

    def _get_commit_sha(self) -> str:
        """Get current git commit SHA."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() or 'unknown'
        except Exception:
            return 'unknown'

    def report(self) -> dict:
        """Generate run report."""
        return {
            'run_manifest': self.run_manifest.to_dict(),
            'benchmark_manifest': self.benchmark.to_dict(),
            'summary': self._compute_summary(),
            'n_trials_persisted': len(self.trials),
        }
