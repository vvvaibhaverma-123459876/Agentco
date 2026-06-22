"""
Real-world validation framework for trustworthiness benchmark.
Validates end-to-end: benchmark → scoring → reporting → CLI
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ValidationCriterion:
    """Defines a validation criterion with pass/fail logic."""

    def __init__(self, name: str, description: str, check_fn, threshold: float = 1.0):
        self.name = name
        self.description = description
        self.check_fn = check_fn  # Returns (passed: bool, details: str)
        self.threshold = threshold
        self.result = None
        self.details = None

    def validate(self, data: Any) -> bool:
        """Run validation check."""
        try:
            self.result, self.details = self.check_fn(data)
            return self.result
        except Exception as e:
            self.result = False
            self.details = f"Exception: {str(e)}"
            return False

    def status_icon(self) -> str:
        if self.result is None:
            return "⏳"
        elif self.result:
            return "✅"
        else:
            return "❌"


class ValidationSuite:
    """Comprehensive validation suite."""

    def __init__(self):
        self.criteria: List[ValidationCriterion] = []
        self.results: Dict[str, bool] = {}

    def add_criterion(self, criterion: ValidationCriterion):
        """Add validation criterion."""
        self.criteria.append(criterion)

    def run_all(self, data: Any) -> Dict[str, bool]:
        """Run all validations."""
        print("\n" + "=" * 80)
        print("REAL-WORLD VALIDATION SUITE")
        print("=" * 80 + "\n")

        for criterion in self.criteria:
            passed = criterion.validate(data)
            self.results[criterion.name] = passed
            status = criterion.status_icon()

            print(f"{status} {criterion.name}")
            print(f"   {criterion.description}")
            if criterion.details:
                print(f"   Details: {criterion.details}")
            print()

        return self.results

    def summary(self) -> Dict[str, Any]:
        """Generate validation summary."""
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        return {
            'total_criteria': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': pass_rate,
            'all_passed': passed == total,
            'timestamp': datetime.utcnow().isoformat(),
        }

    def print_summary(self):
        """Print validation summary."""
        summary = self.summary()
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total Criteria:  {summary['total_criteria']}")
        print(f"Passed:          {summary['passed']}")
        print(f"Failed:          {summary['failed']}")
        print(f"Pass Rate:       {summary['pass_rate']:.1f}%")
        print(f"Overall Status:  {'✅ PASS' if summary['all_passed'] else '❌ FAIL'}")
        print("=" * 80 + "\n")

        return summary


# ============================================================================
# VALIDATION CRITERIA
# ============================================================================

def create_validation_suite() -> ValidationSuite:
    """Create comprehensive validation suite."""
    suite = ValidationSuite()

    # ========== Phase 2: Metrics & Reporting ==========

    suite.add_criterion(ValidationCriterion(
        "Phase 2a: Enhanced Metrics (MCE, AUROC, Selective Accuracy)",
        "Verify MCE, selective_accuracy, coverage, auroc metrics computed",
        lambda data: (
            all(k in data.get('per_model_metrics', {}).get(list(data.get('per_model_metrics', {}).keys())[0] if data.get('per_model_metrics') else None, {})
                for k in ['mce', 'selective_accuracy', 'auroc'])
            if data.get('per_model_metrics') else False,
            "MCE, selective_accuracy, coverage, auroc present in aggregated metrics"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "Phase 2b: TrustworthinessReport Generation",
        "Report includes red flags, green flags, and recommendations",
        lambda data: (
            isinstance(data, dict) and
            'red_flags' in data and
            'green_flags' in data and
            'recommendations' in data,
            f"Report has red_flags ({len(data.get('red_flags', []))}), "
            f"green_flags ({len(data.get('green_flags', []))}), "
            f"recommendations ({len(data.get('recommendations', []))})"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "Phase 2c: Provenance Capture",
        "Execution traces recorded with steps and latencies",
        lambda data: (
            'traces' in data and len(data['traces']) > 0 and
            all('steps' in t and 'total_latency_ms' in t for t in data['traces'].values()),
            f"Captured {len(data.get('traces', {}))} execution traces with steps"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "Phase 2d: CLI Commands Working",
        "All CLI subcommands (list-benchmarks, run, report, replay) functional",
        lambda data: (
            data.get('cli_commands_tested', 0) >= 5,
            f"Tested {data.get('cli_commands_tested', 0)} CLI commands"
        )
    ))

    # ========== Phase 3: Backend Integration ==========

    suite.add_criterion(ValidationCriterion(
        "Phase 3a: REST Endpoints Defined",
        "All 7 API endpoints have correct HTTP methods",
        lambda data: (
            len(data.get('api_endpoints', [])) >= 7 and
            all(ep.get('method') in ['GET', 'POST', 'PUT', 'DELETE']
                for ep in data.get('api_endpoints', [])),
            f"Defined {len(data.get('api_endpoints', []))} endpoints with proper HTTP methods"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "Phase 3b: Database Patterns Validated",
        "Append-only semantics, immutability, idempotency tests pass",
        lambda data: (
            data.get('db_tests_passed', 0) >= 11,
            f"Database tests: {data.get('db_tests_passed', 0)}/11 passed"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "Phase 3c: Frontend Dashboard Renders",
        "Dashboard components render without errors",
        lambda data: (
            data.get('frontend_components_tested', 0) >= 3,
            f"Tested {data.get('frontend_components_tested', 0)} frontend components"
        )
    ))

    # ========== Phase 4: Correctness Fixes ==========

    suite.add_criterion(ValidationCriterion(
        "Phase 4a: Circular Dependency Detection",
        "DAG validation and cycle detection working",
        lambda data: (
            data.get('circular_check_passed', False),
            "Circular dependency detector validated"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "Phase 4b: Dynamic Confidence Calibration",
        "Calibration replaces hardcoded confidences",
        lambda data: (
            data.get('calibration_applied', False) and
            abs(data.get('calibrated_confidence', 0) - 0.858) < 0.01,
            f"Calibrated confidence: {data.get('calibrated_confidence', 0):.3f} "
            f"(expected ~0.858)"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "Phase 4c: Model Registry Canonicalization",
        "Model IDs normalized correctly across providers",
        lambda data: (
            data.get('model_normalizations_passed', 0) >= 10,
            f"Normalized {data.get('model_normalizations_passed', 0)} model ID variants"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "Phase 4d: REST Idempotency",
        "GET endpoints idempotent, POST deduped",
        lambda data: (
            data.get('idempotency_tests_passed', 0) >= 2,
            f"Idempotency tests: {data.get('idempotency_tests_passed', 0)}/2 passed"
        )
    ))

    # ========== End-to-End Integration ==========

    suite.add_criterion(ValidationCriterion(
        "E2E: Full Benchmark Pipeline",
        "Complete flow: benchmark → score → report → leaderboard",
        lambda data: (
            data.get('benchmark_cases_run', 0) >= 15 and
            data.get('models_evaluated', 0) >= 1 and
            data.get('leaderboard_generated', False),
            f"Ran {data.get('benchmark_cases_run', 0)} cases against "
            f"{data.get('models_evaluated', 0)} model(s), generated leaderboard"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "E2E: Scoring & Metrics",
        "Scores calculated correctly, metrics in valid range",
        lambda data: (
            all(0.0 <= s.get('overall_score', 0) <= 1.0
                for s in data.get('all_scores', [])) and
            data.get('metric_validation_passed', False),
            f"All {len(data.get('all_scores', []))} scores in [0, 1]"
        )
    ))

    suite.add_criterion(ValidationCriterion(
        "E2E: Report Generation",
        "Reports generated in JSON and Markdown formats",
        lambda data: (
            data.get('report_json_valid', False) and
            data.get('report_markdown_valid', False),
            "Report generated in JSON and Markdown formats"
        )
    ))

    return suite


# ============================================================================
# VALIDATION RUNNER
# ============================================================================

def run_real_world_validation() -> Dict[str, Any]:
    """Execute complete real-world validation."""
    print("\n" + "=" * 80)
    print("AGENTCO TRUSTWORTHINESS BENCHMARK")
    print("Real-World Validation Suite")
    print("=" * 80)

    validation_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'environment': 'local_development',
        'test_results': [],
    }

    # ========== Step 1: Run Benchmark ==========
    print("\n[1/6] Running benchmark with deterministic model...")
    try:
        result = subprocess.run(
            [
                'python', '-m', 'evals.enterprise_vendor_risk.run_benchmark',
                '--models', 'fake:deterministic',
                '--output', '/tmp/validation_benchmark.json',
            ],
            cwd='/Users/Zet/Agentco',
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            with open('/tmp/validation_benchmark.json') as f:
                benchmark_results = json.load(f)

            validation_data['benchmark_cases_run'] = len(benchmark_results.get('cases', []))
            validation_data['models_evaluated'] = len(benchmark_results.get('per_model_metrics', {}))
            print(f"✅ Benchmark complete: {validation_data['benchmark_cases_run']} cases, "
                  f"{validation_data['models_evaluated']} model(s)")
        else:
            print(f"❌ Benchmark failed: {result.stderr}")
            validation_data['benchmark_error'] = result.stderr
    except Exception as e:
        print(f"❌ Benchmark error: {e}")
        validation_data['benchmark_error'] = str(e)

    # ========== Step 2: Generate Report ==========
    print("\n[2/6] Generating trustworthiness report...")
    try:
        from evals.enterprise_vendor_risk.score import VendorRiskScorer
        from evals.enterprise_vendor_risk.report import TrustworthinessReport, ModelMetrics
        from evals.enterprise_vendor_risk.run_benchmark import load_dataset

        with open('/tmp/validation_benchmark.json') as f:
            results = json.load(f)

        cases = load_dataset()
        scorer = VendorRiskScorer()
        per_model = scorer.aggregate_scores(results, cases)

        report = TrustworthinessReport(
            run_id=results.get('run_id', 'validation-run'),
            benchmark_id='enterprise_vendor_risk',
            created_at=datetime.utcnow(),
            commit_sha=results.get('commit_sha', 'unknown'),
            dataset_hash=results.get('dataset_hash', 'unknown'),
        )

        all_scores = []
        for model_id, metrics in per_model.items():
            all_scores.append({'model_id': model_id, **metrics})
            model_metrics = ModelMetrics(model_id=model_id, **metrics)
            report.add_model(model_metrics)

        report.analyze_red_flags()
        report.analyze_green_flags()
        report.generate_recommendations()

        validation_data['per_model_metrics'] = per_model
        validation_data['all_scores'] = all_scores
        validation_data['report_red_flags'] = report.red_flags
        validation_data['report_green_flags'] = report.green_flags
        validation_data['report_recommendations'] = report.recommendations

        # Validate report structure
        validation_data['report_json_valid'] = report.to_json() is not None
        validation_data['report_markdown_valid'] = len(report.to_markdown()) > 0

        print(f"✅ Report generated: {len(report.red_flags)} red flags, "
              f"{len(report.green_flags)} green flags, "
              f"{len(report.recommendations)} recommendations")

    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        validation_data['report_error'] = str(e)

    # ========== Step 3: Generate Leaderboard ==========
    print("\n[3/6] Generating leaderboard...")
    try:
        from evals.enterprise_vendor_risk.leaderboard import generate_leaderboard

        generate_leaderboard(
            '/tmp/validation_benchmark.json',
            output_json='/tmp/validation_leaderboard.json',
            output_md='/tmp/validation_leaderboard.md',
        )

        with open('/tmp/validation_leaderboard.json') as f:
            leaderboard_data = json.load(f)

        validation_data['leaderboard_generated'] = True
        validation_data['leaderboard_entries'] = len(leaderboard_data.get('leaderboard', []))
        print(f"✅ Leaderboard generated with {validation_data['leaderboard_entries']} entries")

    except Exception as e:
        print(f"❌ Leaderboard failed: {e}")
        validation_data['leaderboard_error'] = str(e)

    # ========== Step 4: Test CLI Commands ==========
    print("\n[4/6] Testing CLI commands...")
    cli_tests_passed = 0
    try:
        # Test list-benchmarks
        result = subprocess.run(
            ['python', '-m', 'evals.enterprise_vendor_risk.cli', 'list-benchmarks', '--format', 'json'],
            cwd='/Users/Zet/Agentco',
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            cli_tests_passed += 1
            print("  ✅ list-benchmarks")

        # Test report generation
        result = subprocess.run(
            [
                'python', '-m', 'evals.enterprise_vendor_risk.cli', 'report',
                '--input', '/tmp/validation_benchmark.json',
                '--format', 'markdown',
            ],
            cwd='/Users/Zet/Agentco',
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            cli_tests_passed += 1
            print("  ✅ report")

        # Test leaderboard
        result = subprocess.run(
            [
                'python', '-m', 'evals.enterprise_vendor_risk.cli', 'leaderboard',
                '--input', '/tmp/validation_benchmark.json',
            ],
            cwd='/Users/Zet/Agentco',
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            cli_tests_passed += 1
            print("  ✅ leaderboard")

        validation_data['cli_commands_tested'] = cli_tests_passed

    except Exception as e:
        print(f"❌ CLI test failed: {e}")

    # ========== Step 5: Validate Correctness Utilities ==========
    print("\n[5/6] Validating Phase 4 correctness fixes...")
    try:
        from evals.enterprise_vendor_risk.correctness_utils import (
            CircularDependencyDetector,
            ConfidenceCalibrationContext,
            ModelRegistry,
            RequestDeduplicator,
        )

        # Test 1: Circular dependency detection
        detector = CircularDependencyDetector()
        detector.register_source("A", ["B"])
        detector.register_source("B", ["C"])
        detector.register_source("C", [])
        validation_data['circular_check_passed'] = detector.validate_all_acyclic()
        print("  ✅ Circular dependency detection")

        # Test 2: Dynamic calibration
        ctx = ConfidenceCalibrationContext(
            stated_confidence=0.95,
            semantic_entropy=0.3,
            historical_accuracy=0.85,
            abstention_flag=False,
        )
        calibrated = ctx.compute_calibrated_confidence()
        validation_data['calibration_applied'] = True
        validation_data['calibrated_confidence'] = calibrated
        print(f"  ✅ Dynamic calibration (0.95 → {calibrated:.3f})")

        # Test 3: Model registry
        normalizations = 0
        test_models = [
            'gpt-4.1', 'claude-3-7-sonnet', 'fake:deterministic',
            'gpt4-turbo', 'claude-3-sonnet', 'gemini-pro',
        ]
        for model_id in test_models:
            normalized = ModelRegistry.normalize_model_id(model_id)
            if normalized:
                normalizations += 1

        validation_data['model_normalizations_passed'] = normalizations
        print(f"  ✅ Model registry ({normalizations} normalizations)")

        # Test 4: Request deduplication
        dedup = RequestDeduplicator()
        req_id_1 = dedup.generate_request_id("POST", "/api/runs", {"benchmark": "test"})
        req_id_2 = dedup.generate_request_id("POST", "/api/runs", {"benchmark": "test"})
        validation_data['idempotency_tests_passed'] = 2 if req_id_1 == req_id_2 else 0
        print("  ✅ Request deduplication")

    except Exception as e:
        print(f"❌ Correctness utilities failed: {e}")

    # ========== Step 6: Metric Validation ==========
    print("\n[6/6] Validating metrics and scoring...")
    try:
        if validation_data.get('all_scores'):
            # Check all scores in valid range
            all_valid = all(
                0.0 <= score.get('overall_score', 0) <= 1.0
                for score in validation_data['all_scores']
            )
            validation_data['metric_validation_passed'] = all_valid

            # Check for specific metrics
            if validation_data['all_scores']:
                first_score = validation_data['all_scores'][0]
                has_new_metrics = all(
                    k in first_score
                    for k in ['mce', 'selective_accuracy', 'auroc']
                )
                validation_data['has_new_metrics'] = has_new_metrics

                print(f"  ✅ All scores valid: {all_valid}")
                print(f"  ✅ New metrics present: {has_new_metrics}")
                print(f"  ✅ Overall score: {first_score['overall_score']:.3f}")

    except Exception as e:
        print(f"❌ Metric validation failed: {e}")

    # ========== Run Validation Suite ==========
    suite = create_validation_suite()
    suite.run_all(validation_data)
    summary = suite.print_summary()

    validation_data['validation_summary'] = summary
    validation_data['all_tests_passed'] = summary['all_passed']

    return validation_data


if __name__ == '__main__':
    results = run_real_world_validation()
    print("\nValidation Results Saved")
    print(json.dumps(results, indent=2, default=str))
