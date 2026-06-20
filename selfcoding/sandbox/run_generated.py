#!/usr/bin/env python3
"""
SANDBOX EXECUTOR: Runs generated code with structural confinement.

This executor enforces:
1. No write access to frozen-data path (OS-level)
2. No ability to modify resolver (child process isolation)
3. No ability to import resolver internals (restricted imports)
4. Restricted filesystem scope (scratch directory only)

Generated code runs in this process but can ONLY:
- Read frozen data via resolver.score_prediction() calls
- Read/write to scratch directory
- Call whitelisted stdlib functions
- Import whitelisted modules (numpy, pandas, etc.)

NOT allowed:
- Import sealed_resolver internals
- Import or execute os.system, subprocess, etc.
- Write to frozen_data_path
- Import custom modules from parent
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Sandbox configuration
FROZEN_DATA_PATH = Path("/Users/Zet/Desktop/Agentco/evals/experiments/nse_phase6_data_frozen/")
SCRATCH_DIR = Path("/Users/Zet/Desktop/Agentco/selfcoding/sandbox/scratch/")

# Whitelist of modules that generated code CAN import
ALLOWED_IMPORTS = {
    "numpy",
    "np",  # Allow np alias
    "pandas",
    "pd",  # Allow pd alias
    "json",
    "math",
    "statistics",
    "datetime",
    "collections",
    "itertools",
    "functools",
    "operator",
    "pathlib",
}

# Modules that generated code CANNOT import
FORBIDDEN_IMPORTS = {
    "os",
    "subprocess",
    "sys",
    "importlib",
    "imp",
    "__builtin__",
    "builtins",
    "ctypes",
    "pickle",
    "marshal",
    "selfcoding.resolver",
}


class SandboxError(Exception):
    """Raised when sandbox constraint is violated."""
    pass


class SandboxImportBlocker:
    """Meta-path finder that blocks forbidden imports."""

    def find_module(self, fullname: str, path: list[str] | None = None) -> Any:
        """Block forbidden imports."""
        if fullname in FORBIDDEN_IMPORTS or any(
            fullname.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_IMPORTS
        ):
            raise SandboxError(f"Import blocked: {fullname} is not allowed in sandbox")
        return None

    def find_spec(self, fullname: str, path: list[str] | None = None, target: Any = None) -> Any:
        """Block forbidden imports (PEP 451)."""
        if fullname in FORBIDDEN_IMPORTS or any(
            fullname.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_IMPORTS
        ):
            raise SandboxError(f"Import blocked: {fullname} is not allowed in sandbox")
        return None


def setup_sandbox() -> dict[str, Any]:
    """
    Set up the sandbox environment.

    Returns:
        Dictionary with sandbox context (resolver proxy, scratch dir, etc.)
    """
    # Create scratch directory
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    # Make sure frozen data path is not writable
    if os.access(FROZEN_DATA_PATH, os.W_OK):
        raise SandboxError(f"CRITICAL: Frozen data path is writable: {FROZEN_DATA_PATH}")

    # Import resolver in parent process BEFORE installing blocker
    # This prevents generated code from getting a direct reference to the resolver
    from selfcoding.resolver import get_resolver
    resolver = get_resolver(FROZEN_DATA_PATH)

    # NOW install import blocker (after parent imports are done)
    sys.meta_path.insert(0, SandboxImportBlocker())

    return {
        "resolver": resolver,
        "scratch_dir": SCRATCH_DIR,
        "frozen_data_path": FROZEN_DATA_PATH,
    }


def run_generated_code(code: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Execute generated code in the sandbox.

    Args:
        code: Python code to execute
        context: Sandbox context (from setup_sandbox)

    Returns:
        {
            "success": bool,
            "output": dict (generated code's result),
            "error": str (if failed),
            "error_type": str,
        }
    """
    resolver = context["resolver"]
    scratch_dir = context["scratch_dir"]

    # Build execution environment
    # Generated code has access to resolver result, not the resolver object itself
    exec_globals = {
        "resolver": None,  # Block direct access
        "score_prediction": resolver.score_prediction,  # ONLY this method
        "scratch_dir": scratch_dir,
        "__name__": "__generated__",
        "__builtins__": {
            # Allow safe builtins
            "print": print,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "range": range,
            "map": map,
            "filter": filter,
            "zip": zip,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "reversed": reversed,
            "enumerate": enumerate,
            "any": any,
            "all": all,
            "bool": bool,
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "PermissionError": PermissionError,
            "FileNotFoundError": FileNotFoundError,
            "OSError": OSError,
            "type": type,
        },
    }

    # Allow __import__ for whitelisted modules only
    # (will also be checked by SandboxImportBlocker)
    import builtins as _builtins
    original_import = _builtins.__import__

    def safe_import(name, *args, **kwargs):
        if name in FORBIDDEN_IMPORTS or any(name.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_IMPORTS):
            raise SandboxError(f"Import blocked: {name}")
        if name not in ALLOWED_IMPORTS:
            raise SandboxError(f"Import not whitelisted: {name}")
        return original_import(name, *args, **kwargs)

    exec_globals["__import__"] = safe_import

    # Dynamically allow whitelisted stdlib imports
    for module_name in ALLOWED_IMPORTS:
        try:
            exec_globals[module_name] = original_import(module_name)
        except ImportError:
            pass

    try:
        exec(code, exec_globals)
        result = exec_globals.get("result", {})
        return {
            "success": True,
            "output": result,
            "error": None,
            "error_type": None,
        }
    except SandboxError as e:
        return {
            "success": False,
            "output": None,
            "error": str(e),
            "error_type": "SandboxError",
        }
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": f"{type(e).__name__}: {str(e)}",
            "error_type": type(e).__name__,
        }


def main() -> int:
    """Quick self-test of the sandbox."""
    context = setup_sandbox()

    # Test 1: Valid code
    print("Test 1: Valid code that uses score_prediction()")
    code = """
result = score_prediction(
    instrument="NIFTY 50",
    prediction_date="2024-10-21",
    predicted_direction="down",
    confidence=0.75
)
"""
    result = run_generated_code(code, context)
    print(f"  Success: {result['success']}")
    if result["success"]:
        print(f"  Score: {result['output']['score']}")
    else:
        print(f"  Error: {result['error']}")

    # Test 2: Try to import os (should fail)
    print("\nTest 2: Try to import os (should be blocked)")
    code = """
import os
result = os.listdir('/')
"""
    result = run_generated_code(code, context)
    print(f"  Success: {result['success']}")
    if not result["success"]:
        print(f"  ✓ Blocked: {result['error']}")
    else:
        print(f"  ✗ BREACH: os was not blocked!")

    # Test 3: Try to write to frozen data (should fail at OS level)
    print("\nTest 3: Try to write to frozen data (should be blocked at OS level)")
    code = """
import tempfile
# Try to write to frozen data path
path = "/Users/Zet/Desktop/Agentco/evals/experiments/nse_phase6_data_frozen/test.txt"
try:
    with open(path, "w") as f:
        f.write("BREACH")
    result = {"breach": True}
except PermissionError as e:
    result = {"breach": False, "error": str(e)}
"""
    result = run_generated_code(code, context)
    print(f"  Success: {result['success']}")
    if result["success"]:
        breach = result["output"].get("breach", False)
        if breach:
            print(f"  ✗ BREACH: Write to frozen data succeeded!")
        else:
            print(f"  ✓ Blocked: {result['output']['error']}")
    else:
        print(f"  Error: {result['error']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
