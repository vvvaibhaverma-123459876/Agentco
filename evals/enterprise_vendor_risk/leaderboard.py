"""
Generate leaderboard from benchmark results.
"""
import argparse
import json
from pathlib import Path

from evals.enterprise_vendor_risk.score import VendorRiskScorer


def generate_leaderboard(input_path: str, output_json: str = None, output_md: str = None):
    """Generate leaderboard from results JSON."""
    with open(input_path) as f:
        results = json.load(f)

    cases = results.get('cases', [])
    scorer = VendorRiskScorer()
    per_model = scorer.aggregate_scores(results, cases)

    # Sort by overall score
    leaderboard = sorted(
        [(model_id, metrics) for model_id, metrics in per_model.items()],
        key=lambda x: x[1].get('overall_score', 0),
        reverse=True
    )

    leaderboard_data = {
        'run_id': results.get('run_id'),
        'created_at': results.get('created_at'),
        'commit_sha': results.get('commit_sha'),
        'dataset_hash': results.get('dataset_hash'),
        'leaderboard': [
            {
                'rank': i + 1,
                'model_id': model_id,
                **metrics,
            }
            for i, (model_id, metrics) in enumerate(leaderboard)
        ],
    }

    # Write JSON
    if output_json:
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, 'w') as f:
            json.dump(leaderboard_data, f, indent=2)
        print(f"Leaderboard JSON: {output_json}")

    # Write Markdown
    if output_md:
        md_content = _generate_markdown(leaderboard_data)
        Path(output_md).parent.mkdir(parents=True, exist_ok=True)
        with open(output_md, 'w') as f:
            f.write(md_content)
        print(f"Leaderboard Markdown: {output_md}")

    return leaderboard_data


def _generate_markdown(data: dict) -> str:
    """Generate Markdown leaderboard."""
    md = f"""# Vendor Risk Triage Benchmark - Leaderboard

**Run ID:** {data['run_id']}
**Created:** {data['created_at']}
**Commit:** {data['commit_sha'][:8]}
**Dataset Hash:** {data['dataset_hash'][:16]}...

Note: This committed result is a deterministic smoke run unless external provider results are present with completed status, provider model id, timestamp, dataset hash, and commit SHA.

## Results

| Rank | Model | Overall Score | Decision Accuracy | Risk Level Accuracy | Policy Compliance | Hallucination Rate | Evidence F1 | Escalation Accuracy |
|------|-------|---|---|---|---|---|---|---|
"""

    for entry in data['leaderboard']:
        md += (
            f"| {entry['rank']} | {entry['model_id']} | "
            f"{entry.get('overall_score', 0):.3f} | "
            f"{entry.get('decision_accuracy', 0):.1%} | "
            f"{entry.get('risk_level_accuracy', 0):.1%} | "
            f"{entry.get('policy_compliance', 0):.1%} | "
            f"{entry.get('hallucination_rate', 0):.1%} | "
            f"{entry.get('evidence_f1', 0):.3f} | "
            f"{entry.get('escalation_accuracy', 0):.1%} |\n"
        )

    md += """
## Scoring Formula

```
trustworthiness_score =
  0.25 * decision_accuracy
+ 0.15 * risk_level_accuracy
+ 0.15 * evidence_f1
+ 0.15 * policy_compliance
+ 0.10 * (1 - hallucination_rate)
+ 0.10 * calibration_accuracy
+ 0.10 * escalation_accuracy
```

## Interpretation

- **Overall Score**: Composite trustworthiness metric (0-1, higher better)
- **Decision Accuracy**: Approval/rejection/escalation correctness
- **Risk Level Accuracy**: Correct severity assessment
- **Policy Compliance**: No violations of stated policies
- **Hallucination Rate**: Unsupported or false claims (0-1, lower better)
- **Evidence F1**: Precision and recall of cited evidence
- **Escalation Accuracy**: Correct escalation decisions
"""

    return md


def main():
    parser = argparse.ArgumentParser(description='Generate vendor risk benchmark leaderboard')
    parser.add_argument('--input', type=str, required=True, help='Input results JSON')
    parser.add_argument('--output-json', type=str, help='Output leaderboard JSON')
    parser.add_argument('--output-md', type=str, help='Output leaderboard Markdown')
    args = parser.parse_args()

    if not args.output_json and not args.output_md:
        args.output_json = 'results/enterprise_vendor_risk/latest.json'
        args.output_md = 'results/enterprise_vendor_risk/latest.md'

    generate_leaderboard(args.input, args.output_json, args.output_md)


if __name__ == '__main__':
    main()
