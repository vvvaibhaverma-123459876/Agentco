"""
Comprehensive CLI for Agentco trustworthiness benchmarking.
Commands: list-benchmarks, run, report, replay, leaderboard
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

from evals.enterprise_vendor_risk.run_benchmark import run_benchmark, load_dataset
from evals.enterprise_vendor_risk.leaderboard import generate_leaderboard
from evals.enterprise_vendor_risk.report import TrustworthinessReport, ModelMetrics
from evals.enterprise_vendor_risk.score import VendorRiskScorer
from evals.enterprise_vendor_risk.provenance import ProvenanceReplayer


def cmd_list_benchmarks(args):
    """List available benchmarks."""
    benchmarks = [
        {
            "benchmark_id": "enterprise_vendor_risk",
            "name": "Enterprise Vendor Risk Triage",
            "description": "High-stakes vendor onboarding decisions with compliance, evidence, and policy constraints",
            "n_cases": 15,
            "task_type": "agent_task",
        }
    ]

    if args.format == "json":
        print(json.dumps(benchmarks, indent=2))
    else:  # table
        print(f"\n{'ID':<25} {'Name':<40} {'Cases':>6}")
        print("-" * 75)
        for b in benchmarks:
            print(f"{b['benchmark_id']:<25} {b['name']:<40} {b['n_cases']:>6}")
        print()


def cmd_run(args):
    """Run a benchmark."""
    print(f"\n🚀 Running benchmark: {args.benchmark_id}")
    print(f"   Models: {args.models}")
    if args.limit:
        print(f"   Limit: {args.limit} cases")

    results = run_benchmark(
        benchmark_id=args.benchmark_id,
        models=args.models.split(","),
        output_path=args.output,
        limit=args.limit,
    )

    print(f"✅ Results saved to: {args.output}")
    return results


def cmd_report(args):
    """Generate trustworthiness report."""
    if not Path(args.input).exists():
        print(f"❌ Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input) as f:
        results = json.load(f)

    scorer = VendorRiskScorer()
    cases = load_dataset()
    per_model = scorer.aggregate_scores(results, cases)

    # Build report
    report = TrustworthinessReport(
        run_id=results.get("run_id", "unknown"),
        benchmark_id=results.get("benchmark_id", "enterprise_vendor_risk"),
        created_at=datetime.utcnow(),
        commit_sha=results.get("commit_sha", "unknown"),
        dataset_hash=results.get("dataset_hash", "unknown"),
        baseline_model_id=args.baseline,
    )

    for model_id, metrics in per_model.items():
        model_metrics = ModelMetrics(
            model_id=model_id,
            **metrics,
        )
        report.add_model(model_metrics)

    report.analyze_red_flags()
    report.analyze_green_flags()
    report.generate_recommendations()

    # Output
    if args.format == "json":
        output = report.to_json(indent=True)
        if args.output:
            Path(args.output).write_text(output)
            print(f"✅ Report saved to: {args.output}")
        else:
            print(output)
    else:  # markdown
        output = report.to_markdown()
        if args.output:
            Path(args.output).write_text(output)
            print(f"✅ Report saved to: {args.output}")
        else:
            print(output)


def cmd_replay(args):
    """Replay a trial's execution trace."""
    traces_file = Path(args.traces_file)
    if not traces_file.exists():
        print(f"❌ Traces file not found: {args.traces_file}", file=sys.stderr)
        sys.exit(1)

    replayer = ProvenanceReplayer.load_traces(str(traces_file))
    replayer.print_trace(args.trial_id, verbose=args.verbose)


def cmd_leaderboard(args):
    """Generate leaderboard from benchmark results."""
    if not Path(args.input).exists():
        print(f"❌ Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    generate_leaderboard(
        args.input,
        output_json=args.output_json or "latest.json",
        output_md=args.output_md or "latest.md",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Agentco Trustworthiness Benchmark CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available benchmarks
  agentco-eval list-benchmarks

  # Run benchmark with fake model
  agentco-eval run --benchmark enterprise_vendor_risk --models fake:deterministic

  # Run with multiple models
  agentco-eval run --models openai:gpt-4.1,anthropic:claude-3-7-sonnet

  # Generate trustworthiness report
  agentco-eval report --input results.json --format markdown --output report.md

  # Replay execution trace
  agentco-eval replay --trial-id abc123 --traces-file traces.json --verbose

  # Generate leaderboard
  agentco-eval leaderboard --input results.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # list-benchmarks
    list_cmd = subparsers.add_parser("list-benchmarks", help="List available benchmarks")
    list_cmd.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format",
    )

    # run
    run_cmd = subparsers.add_parser("run", help="Run a benchmark")
    run_cmd.add_argument(
        "--benchmark",
        dest="benchmark_id",
        default="enterprise_vendor_risk",
        help="Benchmark ID",
    )
    run_cmd.add_argument(
        "--models",
        required=True,
        help="Comma-separated model IDs (e.g., fake:deterministic,openai:gpt-4.1)",
    )
    run_cmd.add_argument(
        "--output",
        default=None,
        help="Output JSON file (default: results/enterprise_vendor_risk/runs/benchmark_<ts>.json)",
    )
    run_cmd.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of cases to run",
    )

    # report
    report_cmd = subparsers.add_parser("report", help="Generate trustworthiness report")
    report_cmd.add_argument(
        "--input",
        required=True,
        help="Input benchmark results JSON",
    )
    report_cmd.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Report format",
    )
    report_cmd.add_argument(
        "--output",
        default=None,
        help="Output file (default: stdout)",
    )
    report_cmd.add_argument(
        "--baseline",
        default=None,
        help="Baseline model ID for comparison",
    )

    # replay
    replay_cmd = subparsers.add_parser("replay", help="Replay trial execution trace")
    replay_cmd.add_argument(
        "--trial-id",
        required=True,
        help="Trial ID to replay",
    )
    replay_cmd.add_argument(
        "--traces-file",
        default="traces.json",
        help="Traces JSON file",
    )
    replay_cmd.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed input/output",
    )

    # leaderboard
    lb_cmd = subparsers.add_parser("leaderboard", help="Generate leaderboard")
    lb_cmd.add_argument(
        "--input",
        required=True,
        help="Input benchmark results JSON",
    )
    lb_cmd.add_argument(
        "--output-json",
        default=None,
        help="Output JSON file",
    )
    lb_cmd.add_argument(
        "--output-md",
        default=None,
        help="Output Markdown file",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "list-benchmarks":
            cmd_list_benchmarks(args)
        elif args.command == "run":
            cmd_run(args)
        elif args.command == "report":
            cmd_report(args)
        elif args.command == "replay":
            cmd_replay(args)
        elif args.command == "leaderboard":
            cmd_leaderboard(args)
        else:
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
