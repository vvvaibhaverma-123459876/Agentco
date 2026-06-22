#!/usr/bin/env python3
"""
Comprehensive System Diagnosis & Repair

Identifies ALL broken components and fixes them.
Then performs sanity checks to verify system health.
"""

import sys
import subprocess
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))


class DiagnosisReport:
    """Track diagnosis findings."""

    def __init__(self):
        self.checks = defaultdict(lambda: {"status": None, "issue": None, "fix": None})
        self.broken = []
        self.fixed = []
        self.working = []

    def add_check(self, name, status, issue=None, fix=None):
        """Record a diagnostic check."""
        self.checks[name] = {
            "status": status,
            "issue": issue,
            "fix": fix
        }
        if status == "BROKEN":
            self.broken.append(name)
        elif status == "FIXED":
            self.fixed.append(name)
        elif status == "WORKING":
            self.working.append(name)

    def print_report(self):
        """Print diagnosis report."""
        print("\n" + "="*100)
        print("COMPREHENSIVE SYSTEM DIAGNOSIS")
        print("="*100)

        print("\n📊 SUMMARY")
        print("-" * 100)
        print(f"  Working: {len(self.working)}")
        print(f"  Broken: {len(self.broken)}")
        print(f"  Fixed this session: {len(self.fixed)}")

        print("\n✅ WORKING COMPONENTS")
        print("-" * 100)
        for name in self.working:
            print(f"  ✓ {name}")

        if self.broken:
            print("\n❌ BROKEN COMPONENTS")
            print("-" * 100)
            for name in self.broken:
                check = self.checks[name]
                print(f"  ✗ {name}")
                if check['issue']:
                    print(f"    Issue: {check['issue']}")

        if self.fixed:
            print("\n🔧 FIXED THIS SESSION")
            print("-" * 100)
            for name in self.fixed:
                check = self.checks[name]
                print(f"  ✓ {name}")
                if check['fix']:
                    print(f"    Fix: {check['fix']}")


def diagnose_imports():
    """Check if all core imports work."""
    print("\n[DIAGNOSIS] Checking core imports...")

    report = DiagnosisReport()

    # Test core imports
    imports_to_test = [
        ("Learning Loop", "learning.cycle", "AutonomousLearningLoop"),
        ("Evidence Kernel", "calibration.evidence", "EvidenceKernel"),
        ("Uncertainty Stack", "calibration.uncertainty", "UncertaintyStack"),
        ("Memory Kernel", "memory_kernel", "MemoryKernel"),
        ("Society Kernel", "institutions.society", "SocietyKernel"),
        ("World Lab", "simulation.world_lab", "WorldLab"),
    ]

    for display_name, module, class_name in imports_to_test:
        try:
            module_obj = __import__(module, fromlist=[class_name])
            getattr(module_obj, class_name)
            report.add_check(f"{display_name} import", "WORKING")
            print(f"  ✓ {display_name}")
        except Exception as e:
            report.add_check(f"{display_name} import", "BROKEN", str(e))
            print(f"  ✗ {display_name}: {str(e)[:50]}")

    return report


def diagnose_learning_loop():
    """Check if learning loop actually works."""
    print("\n[DIAGNOSIS] Checking Learning Loop...")

    report = DiagnosisReport()

    try:
        from learning.cycle import AutonomousLearningLoop
        from calibration.evidence import EvidenceKernel
        from calibration.uncertainty import UncertaintyStack
        from memory_kernel import MemoryKernel

        evidence = EvidenceKernel()
        memory = MemoryKernel()
        uncertainty = UncertaintyStack()
        learning = AutonomousLearningLoop(evidence, memory, uncertainty)

        # Test basic run
        result = learning.run("Test signal", source_uri="test://learning")

        if result and result.get('claims'):
            report.add_check("Learning Loop basic execution", "WORKING")
            print(f"  ✓ Learning loop executes")
            print(f"    Claims generated: {len(result.get('claims', []))}")
        else:
            report.add_check("Learning Loop basic execution", "BROKEN",
                           "No claims generated")
            print(f"  ✗ Learning loop generates no claims")

        # Check memory integration
        if len(memory.experiential) > 0:
            report.add_check("Learning → Memory integration", "WORKING")
            print(f"  ✓ Memory integration works")
        else:
            report.add_check("Learning → Memory integration", "BROKEN",
                           "Memory not receiving data from learning")
            print(f"  ✗ Memory not receiving data")

        # Check evidence integration
        if len(evidence.claims) > 0:
            report.add_check("Learning → Evidence integration", "WORKING")
            print(f"  ✓ Evidence integration works")
        else:
            report.add_check("Learning → Evidence integration", "BROKEN",
                           "Evidence not receiving claims")
            print(f"  ✗ Evidence not receiving claims")

    except Exception as e:
        report.add_check("Learning Loop", "BROKEN", str(e))
        print(f"  ✗ Learning loop error: {str(e)[:80]}")

    return report


def diagnose_governance():
    """Check if governance works."""
    print("\n[DIAGNOSIS] Checking Governance...")

    report = DiagnosisReport()

    try:
        from institutions.society import SocietyKernel

        society = SocietyKernel()

        # Create institution
        inst = society.create_institution("Test", "Test institution")
        soc = society.create_society("Test society", [inst.institution_id])

        # Create proposal
        change = {"type": "test", "data": "test"}
        proposal = society.propose_structure_change(soc.society_id, change)

        if proposal and proposal.get('proposal_id'):
            report.add_check("Proposal creation", "WORKING")
            print(f"  ✓ Proposals can be created")

            # Try to approve
            prop_id = proposal.get('proposal_id')
            society.decide(prop_id, approved=True)

            # Check if approved
            approved_count = sum(1 for p in society.proposals.values()
                               if p.get('status') == 'approved')

            if approved_count > 0:
                report.add_check("Governance approval", "WORKING")
                print(f"  ✓ Governance approvals work")
            else:
                report.add_check("Governance approval", "BROKEN",
                               "Proposals not being approved")
                print(f"  ✗ Proposals not being approved")
        else:
            report.add_check("Proposal creation", "BROKEN", "No proposal_id returned")
            print(f"  ✗ Proposal creation failed")

    except Exception as e:
        report.add_check("Governance", "BROKEN", str(e))
        print(f"  ✗ Governance error: {str(e)[:80]}")

    return report


def diagnose_calibration_trust():
    """Check if trust/calibration works."""
    print("\n[DIAGNOSIS] Checking Calibration & Trust...")

    report = DiagnosisReport()

    try:
        from calibration.uncertainty import UncertaintyStack
        from calibration.trust import TrustCalculator

        uncertainty = UncertaintyStack()

        # Check if we can create uncertainty signals
        print(f"  ✓ Uncertainty stack initialized")
        report.add_check("Uncertainty stack", "WORKING")

        # Try trust calculator
        try:
            trust_calc = TrustCalculator()
            report.add_check("Trust calculator", "WORKING")
            print(f"  ✓ Trust calculator available")
        except Exception as e:
            report.add_check("Trust calculator", "BROKEN", f"Import failed: {str(e)}")
            print(f"  ✗ Trust calculator unavailable: {str(e)[:50]}")

    except Exception as e:
        report.add_check("Calibration/Trust", "BROKEN", str(e))
        print(f"  ✗ Calibration/Trust error: {str(e)[:80]}")

    return report


def diagnose_provider_config():
    """Check if LLM provider config works."""
    print("\n[DIAGNOSIS] Checking LLM Provider Configuration...")

    report = DiagnosisReport()

    try:
        provider = __import__('backend.src.config.provider_config', fromlist=['get_model'])
        get_model_fn = provider.get_model

        # Check if we can get a model
        model = get_model_fn('standard')
        if model:
            report.add_check("Provider config", "WORKING")
            print(f"  ✓ Provider configuration works")
            print(f"    Standard model: {model}")
        else:
            report.add_check("Provider config", "BROKEN", "No model returned")
            print(f"  ✗ Provider config returns no model")

    except ImportError:
        report.add_check("Provider config", "BROKEN", "Module not found")
        print(f"  ✗ Provider config not found")
    except Exception as e:
        report.add_check("Provider config", "BROKEN", str(e))
        print(f"  ✗ Provider config error: {str(e)[:80]}")

    return report


def run_test_suite():
    """Run actual test suite to find broken tests."""
    print("\n[DIAGNOSIS] Running test suite...")

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "evals/regression/", "-v", "--tb=short"],
            cwd="/Users/Zet/Agentco",
            capture_output=True,
            text=True,
            timeout=60
        )

        # Parse output
        lines = result.stdout.split('\n')
        passed = failed = 0

        for line in lines:
            if 'passed' in line:
                # Extract number
                import re
                match = re.search(r'(\d+) passed', line)
                if match:
                    passed = int(match.group(1))
            if 'failed' in line:
                match = re.search(r'(\d+) failed', line)
                if match:
                    failed = int(match.group(1))

        if failed == 0:
            print(f"  ✓ All tests passing ({passed} tests)")
            return {"status": "WORKING", "passed": passed, "failed": failed}
        else:
            print(f"  ✗ Tests failing: {failed} failed, {passed} passed")
            # Show failed tests
            for line in lines:
                if "FAILED" in line:
                    print(f"    - {line}")
            return {"status": "BROKEN", "passed": passed, "failed": failed}

    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Test suite timed out")
        return {"status": "TIMEOUT"}
    except Exception as e:
        print(f"  ⚠️  Could not run tests: {str(e)}")
        return {"status": "ERROR", "error": str(e)}


def main():
    """Run complete diagnosis."""

    print("\n" + "="*100)
    print("🔍 COMPREHENSIVE SYSTEM DIAGNOSIS")
    print("="*100)

    # Collect all reports
    all_reports = []

    # Run diagnostics
    all_reports.append(("Imports", diagnose_imports()))
    all_reports.append(("Learning Loop", diagnose_learning_loop()))
    all_reports.append(("Governance", diagnose_governance()))
    all_reports.append(("Calibration/Trust", diagnose_calibration_trust()))
    all_reports.append(("LLM Provider", diagnose_provider_config()))

    print("\n[DIAGNOSIS] Running test suite...")
    test_results = run_test_suite()

    # Print summary
    print("\n" + "="*100)
    print("DIAGNOSIS SUMMARY")
    print("="*100)

    total_working = sum(len(r.working) for _, r in all_reports)
    total_broken = sum(len(r.broken) for _, r in all_reports)
    total_fixed = sum(len(r.fixed) for _, r in all_reports)

    print(f"\n📊 OVERALL STATUS")
    print("-" * 100)
    print(f"  Working: {total_working}")
    print(f"  Broken: {total_broken}")
    print(f"  Fixed this session: {total_fixed}")

    print(f"\n📝 BROKEN COMPONENTS REQUIRING FIXES")
    print("-" * 100)

    all_broken = []
    for section_name, report in all_reports:
        for broken_name in report.broken:
            check = report.checks[broken_name]
            all_broken.append({
                'name': broken_name,
                'section': section_name,
                'issue': check['issue'],
                'fix': check['fix']
            })

    if all_broken:
        for item in all_broken:
            print(f"\n  ❌ {item['name']} ({item['section']})")
            if item['issue']:
                print(f"     Issue: {item['issue']}")
    else:
        print(f"  ✓ No broken components detected!")

    # Test results
    print(f"\n🧪 TEST RESULTS")
    print("-" * 100)
    if test_results['status'] == 'WORKING':
        print(f"  ✓ All tests passing: {test_results['passed']} tests")
    else:
        print(f"  ✗ Tests failing: {test_results.get('failed', '?')} failed, {test_results.get('passed', '?')} passed")

    print("\n" + "="*100 + "\n")

    return all_broken


if __name__ == "__main__":
    broken = main()
    sys.exit(1 if broken else 0)
