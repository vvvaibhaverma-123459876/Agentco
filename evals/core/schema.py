"""
Evaluation Core Schemas — benchmarks, runs, and trial records.

Defines first-class schemas for reproducible, auditable evaluation pipelines.
All schemas are serializable to JSON and designed for persistent storage.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

from calibration.uncertainty.schema import UncertaintySignal


@dataclass
class BenchmarkManifest:
    """
    Immutable specification of a benchmark/evaluation dataset.

    Fields:
        benchmark_id: Unique identifier (e.g., 'simpleqa_2024_v1')
        name: Human-readable name
        description: Detailed description
        task_type: 'binary_classification' | 'multiple_choice' | 'free_form' | 'agent_task'
        dataset_uri: Location of dataset (file, URL, etc.)
        dataset_hash: SHA256 of dataset for reproducibility
        dataset_version: Version string for lineage tracking
        split: 'train' | 'val' | 'test'
        scorer_ids: List of scoring method IDs used for grading
        license: License of the dataset
        created_at: When manifest was created
        metadata: Custom metadata dict
    """

    benchmark_id: str
    name: str
    description: str
    task_type: str
    dataset_uri: str
    dataset_hash: str
    dataset_version: str
    split: str
    scorer_ids: list[str]
    license: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self):
        """Validate manifest invariants."""
        valid_task_types = {'binary_classification', 'multiple_choice', 'free_form', 'agent_task'}
        if self.task_type not in valid_task_types:
            raise ValueError(f"task_type must be one of {valid_task_types}, got {self.task_type}")

        valid_splits = {'train', 'val', 'test'}
        if self.split not in valid_splits:
            raise ValueError(f"split must be one of {valid_splits}, got {self.split}")

        if not self.benchmark_id:
            raise ValueError("benchmark_id is required")

        if len(self.dataset_hash) != 64:  # SHA256 hex is 64 chars
            raise ValueError(f"dataset_hash must be SHA256 hex (64 chars), got {len(self.dataset_hash)}")

    def manifest_hash(self) -> str:
        """Compute hash of this manifest for reproducibility."""
        data = asdict(self)
        data['created_at'] = data['created_at'].isoformat()
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        data = asdict(self)
        data['created_at'] = data['created_at'].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkManifest:
        """Deserialize from JSON-compatible dict."""
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class EvalRunManifest:
    """
    Specification of an evaluation run: model/agent, hyperparams, environment.

    Fields:
        run_id: Unique run identifier
        benchmark_id: Which benchmark this run evaluates against
        commit_sha: Git commit SHA for reproducibility
        model_provider: 'openai' | 'anthropic' | 'local' | 'fake'
        model_name: Model name (e.g., 'gpt-4', 'claude-opus')
        agent_id: If using an agent (optional)
        agent_version: Agent version string
        prompt_version: Prompt/system version
        tool_profile: Tool-use profile (e.g., 'full', 'read-only', 'none')
        temperature: Temperature parameter
        top_p: Top-p sampling parameter
        max_tokens: Max generation tokens
        seed: Random seed for reproducibility
        started_at: When run started
        completed_at: When run completed (null if ongoing)
        status: 'pending' | 'running' | 'completed' | 'failed'
        metadata: Custom metadata dict
    """

    run_id: str
    benchmark_id: str
    commit_sha: str
    model_provider: str
    model_name: str
    agent_id: Optional[str]
    agent_version: Optional[str]
    prompt_version: str
    tool_profile: str
    temperature: float
    top_p: float
    max_tokens: int
    seed: Optional[int]
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self):
        """Validate run manifest invariants."""
        valid_statuses = {'pending', 'running', 'completed', 'failed'}
        if self.status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got {self.status}")

        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(f"temperature must be in [0, 2], got {self.temperature}")

        if not (0.0 <= self.top_p <= 1.0):
            raise ValueError(f"top_p must be in [0, 1], got {self.top_p}")

        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be >= 1, got {self.max_tokens}")

        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must be >= started_at")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        data = asdict(self)
        data['started_at'] = data['started_at'].isoformat()
        if data['completed_at']:
            data['completed_at'] = data['completed_at'].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalRunManifest:
        """Deserialize from JSON-compatible dict."""
        if isinstance(data['started_at'], str):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if isinstance(data.get('completed_at'), str):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class TrialRecord:
    """
    Single trial execution within an eval run.

    Fields:
        trial_id: Unique trial identifier
        run_id: Parent run ID
        benchmark_id: Parent benchmark ID
        task_id: Task identifier within benchmark
        input_payload: Raw input to model/agent
        raw_output: Raw response from model/agent
        parsed_output: Structured output (if parsing succeeded)
        expected_output: Ground truth/reference
        trace: Execution trace (tool calls, reasoning steps, etc.)
        tool_calls: List of tool calls made
        uncertainty: UncertaintySignal for this trial
        grading_result: Result from grader
        provenance: Provenance information (env, code version, etc.)
        created_at: When trial was recorded
    """

    trial_id: str
    run_id: str
    benchmark_id: str
    task_id: str
    input_payload: dict[str, Any]
    raw_output: str
    parsed_output: Optional[dict[str, Any]]
    expected_output: dict[str, Any]
    trace: Optional[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    uncertainty: Optional[UncertaintySignal]
    grading_result: dict[str, Any]
    provenance: dict[str, Any]
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        data = asdict(self)
        data['created_at'] = data['created_at'].isoformat()
        if self.uncertainty:
            data['uncertainty'] = self.uncertainty.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrialRecord:
        """Deserialize from JSON-compatible dict."""
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('uncertainty'), dict):
            data['uncertainty'] = UncertaintySignal.from_dict(data['uncertainty'])
        return cls(**data)


@dataclass
class GradingResult:
    """
    Result of grading a trial against expected output.

    Fields:
        correctness: True if answer is correct
        score: Numeric score (0-1 or other range depending on grader)
        hallucination_flag: True if hallucination detected
        policy_violation_flag: True if policy violation detected
        tool_error_flag: True if tool execution error occurred
        explanation: Human-readable explanation
        grader_version: Version of grader used
        rubric_version: Version of rubric used
    """

    correctness: bool
    score: float
    hallucination_flag: bool = False
    policy_violation_flag: bool = False
    tool_error_flag: bool = False
    explanation: str = ""
    grader_version: str = "1.0"
    rubric_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GradingResult:
        """Deserialize from JSON-compatible dict."""
        return cls(**data)
