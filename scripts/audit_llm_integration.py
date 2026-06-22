#!/usr/bin/env python3
"""
Comprehensive LLM Integration Audit

Checks which components actually call the LLM vs. use fixtures/mocks.
Identifies any hardcoded provider dependencies.
"""

import sys
import subprocess
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

class LLMIntegrationAudit:
    """Audit which layers actually use LLM."""

    def __init__(self):
        self.results = defaultdict(lambda: {
            "uses_llm": False,
            "provider": None,
            "method": None,
            "evidence": [],
            "limitations": []
        })

    def audit_component(self, name, module_path, description):
        """Audit a single component."""
        print(f"\n[AUDIT] {name}")
        print(f"  Module: {module_path}")
        print(f"  Purpose: {description}")

        try:
            # Try to import and check for LLM usage
            result = self._check_llm_usage(module_path)
            self.results[name] = result

            if result['uses_llm']:
                print(f"  ✅ Uses real LLM")
                print(f"     Provider: {result['provider']}")
                print(f"     Method: {result['method']}")
                for evidence in result['evidence']:
                    print(f"     Evidence: {evidence}")
            else:
                print(f"  ⚠️  Does NOT use real LLM")
                if result['evidence']:
                    for evidence in result['evidence']:
                        print(f"     {evidence}")
                if result['limitations']:
                    for limit in result['limitations']:
                        print(f"     Limitation: {limit}")

        except Exception as e:
            print(f"  ❌ Error checking: {str(e)[:80]}")
            self.results[name]['error'] = str(e)

    def _check_llm_usage(self, module_path):
        """Check if module actually uses LLM."""
        try:
            module = __import__(module_path, fromlist=[''])
            result = {
                "uses_llm": False,
                "provider": None,
                "method": None,
                "evidence": [],
                "limitations": []
            }

            # Check for common LLM call patterns
            source_file = module.__file__
            if source_file:
                with open(source_file) as f:
                    content = f.read()

                    # Check for OpenAI usage
                    if 'openai' in content.lower():
                        result['uses_llm'] = True
                        result['provider'] = 'OpenAI'
                        result['evidence'].append("Contains 'openai' references")

                    # Check for LLM calls
                    if 'ChatCompletion' in content or 'completion' in content.lower():
                        result['uses_llm'] = True
                        result['evidence'].append("Contains completion/generation calls")

                    # Check for provider config usage
                    if 'provider_config' in content or 'get_model' in content:
                        result['uses_llm'] = True
                        result['evidence'].append("Uses provider configuration")
                        result['provider'] = 'Configurable'

                    # Check for hardcoded models
                    if 'gpt-4' in content or 'claude-' in content:
                        result['evidence'].append("Contains hardcoded model references")
                        if not result['uses_llm']:
                            result['limitations'].append("May have hardcoded provider dependencies")

                    # Check for fixture/mock usage
                    if 'fixture' in content.lower() or 'mock' in content.lower():
                        if not result['uses_llm']:
                            result['limitations'].append("Uses fixtures/mocks instead of real LLM")

            return result

        except Exception as e:
            return {
                "uses_llm": False,
                "error": str(e),
                "evidence": [],
                "limitations": []
            }

    def print_summary(self):
        """Print audit summary."""
        print("\n" + "="*100)
        print("LLM INTEGRATION AUDIT SUMMARY")
        print("="*100)

        using_llm = sum(1 for r in self.results.values() if r.get('uses_llm'))
        not_using_llm = len(self.results) - using_llm

        print(f"\n📊 COMPONENTS USING REAL LLM: {using_llm}/{len(self.results)}")
        print("-" * 100)

        for name, result in self.results.items():
            if result.get('uses_llm'):
                print(f"  ✅ {name}")
                if result.get('provider'):
                    print(f"     → {result['provider']}")

        if not_using_llm > 0:
            print(f"\n⚠️  COMPONENTS NOT USING REAL LLM: {not_using_llm}/{len(self.results)}")
            print("-" * 100)

            for name, result in self.results.items():
                if not result.get('uses_llm') and not result.get('error'):
                    print(f"  ⚠️  {name}")
                    for limitation in result.get('limitations', []):
                        print(f"     → {limitation}")

        print(f"\n🎯 VERDICT")
        print("-" * 100)

        if using_llm == len(self.results):
            print(f"  ✅ ALL COMPONENTS USE REAL LLM")
            print(f"     Agentco is fully OpenAI-integrated")
        elif using_llm >= len(self.results) * 0.8:
            print(f"  ✨ MOSTLY REAL LLM ({using_llm}/{len(self.results)})")
            print(f"     {not_using_llm} components use fixtures or mocks")
        elif using_llm > 0:
            print(f"  ⚠️  PARTIAL LLM INTEGRATION ({using_llm}/{len(self.results)})")
            print(f"     {not_using_llm} components don't use real LLM")
        else:
            print(f"  ❌ NO REAL LLM USAGE")
            print(f"     All components use fixtures")

        print("\n" + "="*100 + "\n")


def main():
    """Run comprehensive audit."""

    print("\n" + "="*100)
    print("🔍 COMPREHENSIVE LLM INTEGRATION AUDIT")
    print("="*100)

    audit = LLMIntegrationAudit()

    # Core systems
    audit.audit_component(
        "Learning Loop",
        "learning.cycle",
        "Autonomous learning with claim generation"
    )

    audit.audit_component(
        "Evidence Kernel",
        "calibration.evidence",
        "Evidence collection and validation"
    )

    audit.audit_component(
        "Ingestion Pipeline",
        "ingestion.pipeline",
        "Document ingestion and claim extraction"
    )

    audit.audit_component(
        "RAG System",
        "ingestion.rag",
        "Retrieval-augmented generation"
    )

    audit.audit_component(
        "Model Foundry",
        "foundry",
        "Model training and fine-tuning"
    )

    audit.audit_component(
        "Validation Suite",
        "validation",
        "External validation and benchmarking"
    )

    audit.audit_component(
        "Trust Calculator",
        "calibration.trust",
        "Trust scoring and calibration"
    )

    audit.audit_component(
        "Uncertainty Stack",
        "calibration.uncertainty",
        "Confidence and uncertainty quantification"
    )

    audit.audit_component(
        "Memory Kernel",
        "memory_kernel",
        "Experience storage and retrieval"
    )

    audit.audit_component(
        "Governance",
        "institutions.society",
        "Institutional decision-making"
    )

    audit.audit_component(
        "World Simulation",
        "simulation.world_lab",
        "Scenario testing and validation"
    )

    audit.audit_component(
        "Civilization Framework",
        "civilization",
        "Multi-agent coordination"
    )

    # Print summary
    audit.print_summary()

    return audit.results


if __name__ == "__main__":
    results = main()

    # Count real vs fixture usage
    real_llm = sum(1 for r in results.values() if r.get('uses_llm'))
    total = len(results)

    print(f"\n📈 SUMMARY: {real_llm}/{total} components use real LLM")
    print(f"   Rate: {real_llm/total*100:.0f}%")

    sys.exit(0 if real_llm == total else 1)
