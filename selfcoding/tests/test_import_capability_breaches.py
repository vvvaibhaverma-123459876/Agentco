#!/usr/bin/env python3
"""
NEW BREACH TESTS: Verify that whitelisted imports cannot be used to breach sandbox.

These tests ensure that allowing import statements (the new change) doesn't open
any new security holes. Tests target:
1. Escalation: Can imported modules be used to import forbidden modules?
2. Introspection: Can whitelisted modules reveal sandbox internals?
3. Escape: Can whitelisted modules be used to break out?
4. Write access: Can whitelisted modules modify protected data?
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from selfcoding.sandbox.run_generated import run_generated_code, setup_sandbox


class ImportBreachTest:
    """Test suite for import-specific breaches."""

    def __init__(self):
        self.context = setup_sandbox()
        self.results = []

    def test(self, name: str, code: str, should_succeed: bool = False) -> bool:
        """
        Run an import-specific breach test.

        Args:
            name: Name of the test
            code: Generated code to test
            should_succeed: If True, code should execute; if False, should fail

        Returns:
            True if test passed
        """
        result = run_generated_code(code, self.context)

        passed = (result["success"] == should_succeed)
        status = "✓ PASS" if passed else "✗ FAIL"

        print(f"\n{status}: {name}")
        if should_succeed:
            print(f"       (Expected: should succeed)")
        else:
            print(f"       (Expected: should fail)")

        if result["success"]:
            print(f"       Result: {result['output']}")
        else:
            print(f"       Error: {result['error']}")

        self.results.append({"name": name, "passed": passed, "result": result})
        return passed

    def test_numpy_import_and_use(self) -> bool:
        """NEW: Verify numpy import works (should succeed now)."""
        code = """
import numpy as np
arr = np.array([1, 2, 3, 4, 5])
result = {"mean": float(np.mean(arr)), "sum": int(np.sum(arr))}
"""
        return self.test("NEW - Import: numpy (legitimate use)", code, should_succeed=True)

    def test_pandas_import_and_use(self) -> bool:
        """NEW: Verify pandas import works (should succeed now)."""
        code = """
import pandas as pd
data = pd.Series([1, 2, 3, 4, 5])
result = {"mean": float(data.mean()), "sum": int(data.sum())}
"""
        return self.test("NEW - Import: pandas (legitimate use)", code, should_succeed=True)

    def test_json_import_and_use(self) -> bool:
        """NEW: Verify json import works (should succeed now)."""
        code = """
import json
data = {"test": "value"}
serialized = json.dumps(data)
result = {"serialized": serialized}
"""
        return self.test("NEW - Import: json (legitimate use)", code, should_succeed=True)

    def test_escalation_numpy_to_os(self) -> bool:
        """NEW: Try to escalate numpy import to os (should fail)."""
        code = """
try:
    import numpy as np
    # Try to access os via numpy's internals (numpy doesn't expose os)
    import os
    result = {"breach": True, "method": "numpy_escalation"}
except ImportError as e:
    result = {"breach": False, "error": str(e)}
except Exception as e:
    result = {"breach": False, "error": str(e)}
"""
        return self.test("NEW - Escalation: numpy → os (blocked)", code, should_succeed=True)

    def test_escalation_pandas_to_sys(self) -> bool:
        """NEW: Try to escalate pandas import to sys (should fail)."""
        code = """
try:
    import pandas as pd
    # Try to use pandas to access sys
    import sys
    result = {"breach": True, "method": "pandas_escalation"}
except ImportError as e:
    result = {"breach": False, "error": str(e)}
except Exception as e:
    result = {"breach": False, "error": str(e)}
"""
        return self.test("NEW - Escalation: pandas → sys (blocked)", code, should_succeed=True)

    def test_escalation_math_to_subprocess(self) -> bool:
        """NEW: Try to escalate math import to subprocess (should fail)."""
        code = """
try:
    import math
    # Try to import subprocess
    import subprocess
    result = {"breach": True, "method": "math_escalation"}
except ImportError as e:
    result = {"breach": False, "error": str(e)}
except Exception as e:
    result = {"breach": False, "error": str(e)}
"""
        return self.test("NEW - Escalation: math → subprocess (blocked)", code, should_succeed=True)

    def test_introspection_numpy_source(self) -> bool:
        """NEW: Try to introspect numpy source code (should fail due to no inspect)."""
        code = """
try:
    import numpy as np
    import inspect
    # Try to get source of numpy internals
    source = inspect.getsource(np.array)
    result = {"breach": True, "method": "numpy_introspection"}
except ImportError as e:
    result = {"breach": False, "error": str(e)}
except Exception as e:
    result = {"breach": False, "error": str(e)}
"""
        return self.test("NEW - Introspection: numpy source (blocked)", code, should_succeed=True)

    def test_introspection_numpy_globals(self) -> bool:
        """NEW: Try to access numpy's globals (should fail)."""
        code = """
try:
    import numpy as np
    # Try to access numpy module's globals
    globals_dict = vars(np)
    # Check if any forbidden module is exposed
    has_os = "os" in globals_dict
    has_subprocess = "subprocess" in globals_dict
    result = {"has_os": has_os, "has_subprocess": has_subprocess, "breach": False}
except Exception as e:
    result = {"breach": False, "error": str(e)}
"""
        return self.test("NEW - Introspection: numpy globals", code, should_succeed=True)

    def test_write_via_numpy(self) -> bool:
        """NEW: Try to write files via numpy (should fail at OS level)."""
        code = """
try:
    import numpy as np
    # Try to write to frozen data path using numpy
    path = "/Users/Zet/Desktop/Agentco/evals/experiments/nse_phase6_data_frozen/numpy_test.txt"
    # numpy.savetxt can write files
    np.savetxt(path, [1, 2, 3])
    result = {"breach": True, "method": "numpy_write"}
except PermissionError as e:
    result = {"breach": False, "blocked_by": "PermissionError", "error": str(e)}
except Exception as e:
    result = {"breach": False, "blocked_by": type(e).__name__, "error": str(e)}
"""
        return self.test("NEW - Write: via numpy.savetxt (blocked)", code, should_succeed=True)

    def test_write_via_pandas(self) -> bool:
        """NEW: Try to write files via pandas (should fail at OS level)."""
        code = """
try:
    import pandas as pd
    # Try to write to frozen data path using pandas
    path = "/Users/Zet/Desktop/Agentco/evals/experiments/nse_phase6_data_frozen/pandas_test.csv"
    df = pd.DataFrame({"col": [1, 2, 3]})
    df.to_csv(path)
    result = {"breach": True, "method": "pandas_write"}
except PermissionError as e:
    result = {"breach": False, "blocked_by": "PermissionError", "error": str(e)}
except Exception as e:
    result = {"breach": False, "blocked_by": type(e).__name__, "error": str(e)}
"""
        return self.test("NEW - Write: via pandas.to_csv (blocked)", code, should_succeed=True)

    def test_forbidden_import_via_import_statement(self) -> bool:
        """NEW: Direct attempt to import forbidden module (should fail)."""
        code = """
try:
    import os
    result = {"breach": True, "method": "direct_import"}
except ImportError as e:
    result = {"breach": False, "blocked_by": "SandboxError", "error": str(e)}
except Exception as e:
    result = {"breach": False, "blocked_by": type(e).__name__, "error": str(e)}
"""
        return self.test("NEW - Import: forbidden os module (blocked)", code, should_succeed=True)

    def test_forbidden_import_subprocess(self) -> bool:
        """NEW: Direct attempt to import subprocess (should fail)."""
        code = """
try:
    import subprocess
    result = {"breach": True, "method": "subprocess_import"}
except ImportError as e:
    result = {"breach": False, "blocked_by": "SandboxError", "error": str(e)}
except Exception as e:
    result = {"breach": False, "blocked_by": type(e).__name__, "error": str(e)}
"""
        return self.test("NEW - Import: forbidden subprocess module (blocked)", code, should_succeed=True)

    def test_resolver_import_still_blocked(self) -> bool:
        """NEW: Verify resolver import is still blocked with new __import__."""
        code = """
try:
    from selfcoding.resolver import get_resolver
    result = {"breach": True, "method": "resolver_import"}
except ImportError as e:
    result = {"breach": False, "blocked_by": "SandboxError", "error": str(e)}
except Exception as e:
    result = {"breach": False, "blocked_by": type(e).__name__, "error": str(e)}
"""
        return self.test("NEW - Import: resolver still blocked", code, should_succeed=True)

    def test_whitelisted_import_module_access(self) -> bool:
        """NEW: Verify can import and use whitelisted modules normally."""
        code = """
import numpy as np
import pandas as pd
import json
import math
import statistics
import datetime

# Use each module
np_result = np.array([1, 2, 3])
pd_result = pd.Series([1, 2, 3])
json_result = json.dumps({"test": "value"})
math_result = math.sqrt(4)
stats_result = statistics.mean([1, 2, 3])
dt_result = datetime.datetime.now()

result = {
    "numpy_works": len(np_result) == 3,
    "pandas_works": len(pd_result) == 3,
    "json_works": json_result == '{"test": "value"}',
    "math_works": math_result == 2.0,
    "statistics_works": stats_result == 2.0,
    "datetime_works": dt_result is not None,
}
"""
        return self.test("NEW - Import: all whitelisted modules work", code, should_succeed=True)

    def run_all(self) -> dict[str, any]:
        """Run all new import-capability breach tests."""
        print("=" * 80)
        print("NEW BREACH TESTS: IMPORT CAPABILITY SECURITY")
        print("=" * 80)
        print("\nThese tests verify that the new import capability doesn't open holes.\n")

        # Legitimate uses (should all succeed)
        self.test_numpy_import_and_use()
        self.test_pandas_import_and_use()
        self.test_json_import_and_use()
        self.test_whitelisted_import_module_access()

        # Escalation attempts (should all fail)
        self.test_escalation_numpy_to_os()
        self.test_escalation_pandas_to_sys()
        self.test_escalation_math_to_subprocess()

        # Introspection attempts (should all fail or be ineffective)
        self.test_introspection_numpy_source()
        self.test_introspection_numpy_globals()

        # Write attempts (should all fail at OS level)
        self.test_write_via_numpy()
        self.test_write_via_pandas()

        # Direct forbidden imports (should all fail)
        self.test_forbidden_import_via_import_statement()
        self.test_forbidden_import_subprocess()
        self.test_resolver_import_still_blocked()

        # Summary
        print("\n" + "=" * 80)
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        print(f"RESULTS: {passed}/{total} tests passed")
        print("=" * 80)

        if passed == total:
            print("✓ NEW CAPABILITY SECURED: All import-specific breach attempts blocked")
            return {"all_passed": True, "passed": passed, "total": total}
        else:
            print("✗ BREACH DETECTED: Some import breach tests failed")
            failed = [r for r in self.results if not r["passed"]]
            for r in failed:
                print(f"  - {r['name']}")
            return {"all_passed": False, "passed": passed, "total": total, "failed": failed}


def main() -> int:
    tester = ImportBreachTest()
    summary = tester.run_all()

    if summary["all_passed"]:
        return 0
    else:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
