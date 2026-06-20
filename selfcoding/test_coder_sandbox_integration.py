#!/usr/bin/env python3
"""
Quick integration test: Coder + Sandbox without OpenAI.
Uses fixed BUILD SPEC to verify Qwen code generation and sandbox execution work.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from selfcoding.coder.build_spec import example_build_spec
from selfcoding.coder.qwen_coder import generate_from_spec, CoderError
from selfcoding.sandbox.run_generated import run_generated_code, setup_sandbox


def main() -> int:
    """Test coder + sandbox integration."""
    print("=" * 80)
    print("CODER + SANDBOX INTEGRATION TEST")
    print("=" * 80)
    print()

    # Get example spec (no OpenAI needed)
    spec = example_build_spec()
    print(f"[1/3] Using example BUILD SPEC: {spec.scenario.name}")
    print()

    # Generate code with Qwen
    print("[2/3] Calling Qwen via Ollama...")
    try:
        code = generate_from_spec(spec, verbose=True)
        print()
        print("Generated code:")
        print("-" * 80)
        print(code)
        print("-" * 80)
        print()
    except CoderError as e:
        print(f"❌ Code generation failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

    # Execute in sandbox
    print("[3/3] Executing in sandbox...")
    context = setup_sandbox()

    try:
        result = run_generated_code(code, context)

        if result["success"]:
            print("✓ Execution succeeded")
            print(f"  Result: {result['output']}")
            return 0
        else:
            print(f"❌ Execution failed: {result['error']}")
            return 1

    except Exception as e:
        print(f"❌ Sandbox error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
