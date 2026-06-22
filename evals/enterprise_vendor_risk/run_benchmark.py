"""
Vendor risk triage benchmark runner.

Usage:
  python -m evals.enterprise_vendor_risk.run_benchmark \
    --models fake:deterministic,agentco \
    --output results/enterprise_vendor_risk/runs/test.json
"""
import argparse
import json
import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from evals.enterprise_vendor_risk.adapters.fake_adapter import FakeDeterministicAdapter
from evals.enterprise_vendor_risk.adapters.agentco_adapter import AgentcoAdapter


def load_dataset():
    """Load vendor risk cases from JSONL."""
    dataset_path = Path(__file__).parent / 'dataset.jsonl'
    cases = []
    with open(dataset_path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases


def get_adapter(model_id: str):
    """Get adapter for model."""
    if model_id == 'fake:deterministic':
        return FakeDeterministicAdapter()
    elif model_id == 'agentco':
        return AgentcoAdapter()
    else:
        raise ValueError(f"Unsupported model: {model_id}")


def run_benchmark(model_ids: list[str], output_path: str, limit: int = None):
    """Run benchmark on specified models."""
    cases = load_dataset()
    if limit:
        cases = cases[:limit]

    run_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    commit_sha = _get_git_sha()
    dataset_hash = _hash_cases(cases)

    results = {
        'benchmark_id': 'enterprise_vendor_risk_triage',
        'run_id': run_id,
        'created_at': created_at,
        'commit_sha': commit_sha,
        'dataset_hash': dataset_hash,
        'models_requested': model_ids,
        'models_completed': [],
        'models_skipped': [],
        'cases': [],
        'per_model_metrics': {},
    }

    for model_id in model_ids:
        try:
            adapter = get_adapter(model_id)
            print(f"Running {model_id}...")

            results['models_completed'].append(model_id)
            model_results = {'trials': []}

            for case in cases:
                trial = adapter.predict(case)
                model_results['trials'].append(trial.to_dict())

            results['per_model_metrics'][model_id] = model_results

        except Exception as e:
            print(f"Skipped {model_id}: {e}")
            results['models_skipped'].append({'model_id': model_id, 'reason': str(e)})

    results['cases'] = cases

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Results written to {output_path}")
    return results


def _get_git_sha():
    """Get current git commit SHA."""
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=5)
        return result.stdout.strip() or 'unknown'
    except Exception:
        return 'unknown'


def _hash_cases(cases):
    """Hash dataset for reproducibility."""
    import hashlib
    content = json.dumps(cases, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description='Run vendor risk triage benchmark')
    parser.add_argument('--models', type=str, default='fake:deterministic', help='Comma-separated model IDs')
    parser.add_argument('--output', type=str, default='results/enterprise_vendor_risk/runs/benchmark.json')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of cases')
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(',')]
    run_benchmark(models, args.output, limit=args.limit)


if __name__ == '__main__':
    main()
