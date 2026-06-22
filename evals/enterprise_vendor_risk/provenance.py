"""
Provenance capture and replay for benchmark execution.
Enables debugging and validation of trial execution.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
import json
import hashlib


@dataclass
class ExecutionTrace:
    """Complete execution trace for a single trial."""
    trial_id: str
    task_id: str
    model_id: str
    timestamp: datetime

    # Input snapshot
    task_input: dict[str, Any]
    model_config: dict[str, Any]

    # Execution steps
    steps: list[dict[str, Any]] = field(default_factory=list)

    # Output snapshot
    model_output: Optional[str] = None
    parsed_output: Optional[dict[str, Any]] = None

    # Errors/warnings
    errors: list[str] = field(default_factory=list)

    # Performance
    total_latency_ms: float = 0.0
    step_timings: dict[str, float] = field(default_factory=dict)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(self, step_name: str, input_data: dict, output_data: dict, latency_ms: float = 0.0):
        """Record an execution step."""
        self.steps.append({
            'step': step_name,
            'timestamp': datetime.now(datetime.now().astimezone().tzinfo).isoformat(),
            'input': input_data,
            'output': output_data,
            'latency_ms': latency_ms,
        })
        if step_name in self.step_timings:
            self.step_timings[step_name] += latency_ms
        else:
            self.step_timings[step_name] = latency_ms

    def add_error(self, error_msg: str):
        """Record an error."""
        self.errors.append(error_msg)

    def trace_hash(self) -> str:
        """Compute hash of execution trace for integrity checking."""
        canonical = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        data = asdict(self)
        data['timestamp'] = data['timestamp'].isoformat()
        return data

    def to_json(self, indent: bool = True) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2 if indent else None, default=str)


class ProvenanceRecorder:
    """Records execution traces during benchmark runs."""

    def __init__(self):
        self.traces: dict[str, ExecutionTrace] = {}

    def start_trace(self, trial_id: str, task_id: str, model_id: str,
                   task_input: dict, model_config: dict) -> ExecutionTrace:
        """Start recording a new trace."""
        trace = ExecutionTrace(
            trial_id=trial_id,
            task_id=task_id,
            model_id=model_id,
            timestamp=datetime.utcnow(),
            task_input=task_input,
            model_config=model_config,
        )
        self.traces[trial_id] = trace
        return trace

    def record_step(self, trial_id: str, step_name: str, input_data: dict,
                   output_data: dict, latency_ms: float = 0.0):
        """Record a step in an ongoing trace."""
        if trial_id in self.traces:
            self.traces[trial_id].add_step(step_name, input_data, output_data, latency_ms)

    def record_error(self, trial_id: str, error_msg: str):
        """Record an error in an ongoing trace."""
        if trial_id in self.traces:
            self.traces[trial_id].add_error(error_msg)

    def finish_trace(self, trial_id: str, model_output: str, parsed_output: dict,
                    total_latency_ms: float):
        """Finalize a trace."""
        if trial_id in self.traces:
            self.traces[trial_id].model_output = model_output
            self.traces[trial_id].parsed_output = parsed_output
            self.traces[trial_id].total_latency_ms = total_latency_ms

    def export_trace(self, trial_id: str) -> Optional[dict[str, Any]]:
        """Export a single trace."""
        if trial_id in self.traces:
            return self.traces[trial_id].to_dict()
        return None

    def export_all_traces(self) -> dict[str, dict[str, Any]]:
        """Export all traces."""
        return {
            trial_id: trace.to_dict()
            for trial_id, trace in self.traces.items()
        }

    def save_traces(self, filepath: str):
        """Save all traces to JSON file."""
        data = {
            'exported_at': datetime.utcnow().isoformat(),
            'n_traces': len(self.traces),
            'traces': self.export_all_traces(),
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)


class ProvenanceReplayer:
    """Replays execution traces for debugging and validation."""

    def __init__(self, traces: dict[str, dict[str, Any]]):
        self.traces = traces

    @staticmethod
    def load_traces(filepath: str) -> 'ProvenanceReplayer':
        """Load traces from JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return ProvenanceReplayer(data.get('traces', {}))

    def get_trace(self, trial_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a single trace."""
        return self.traces.get(trial_id)

    def replay_steps(self, trial_id: str) -> list[dict[str, Any]]:
        """Replay execution steps for a trial."""
        trace = self.get_trace(trial_id)
        if not trace:
            return []
        return trace.get('steps', [])

    def validate_integrity(self, trial_id: str, expected_hash: str) -> bool:
        """Validate trace integrity against expected hash."""
        trace = self.get_trace(trial_id)
        if not trace:
            return False

        canonical = json.dumps(trace, sort_keys=True, default=str)
        computed_hash = hashlib.sha256(canonical.encode()).hexdigest()
        return computed_hash == expected_hash

    def print_trace(self, trial_id: str, verbose: bool = False):
        """Pretty-print a trace."""
        trace = self.get_trace(trial_id)
        if not trace:
            print(f"Trace {trial_id} not found")
            return

        print(f"\n{'='*80}")
        print(f"Trial: {trace['trial_id'][:8]}…  Model: {trace['model_id']}")
        print(f"Task: {trace['task_id']}  Timestamp: {trace['timestamp']}")
        print(f"Total Latency: {trace['total_latency_ms']:.0f}ms")
        print(f"{'='*80}\n")

        if verbose:
            print("Input:")
            print(json.dumps(trace['task_input'], indent=2, default=str)[:500])
            print("\n")

        print("Execution Steps:")
        for i, step in enumerate(trace['steps'], 1):
            print(f"  {i}. {step['step']} ({step['latency_ms']:.0f}ms)")

        print("\nOutput:")
        if trace['parsed_output']:
            print(json.dumps(trace['parsed_output'], indent=2, default=str)[:500])

        if trace['errors']:
            print("\nErrors:")
            for err in trace['errors']:
                print(f"  - {err}")

        print()
