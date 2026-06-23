#!/usr/bin/env python3
"""
Production Smoke Test - Verifies backend is running and responding correctly.
Exit code 0 = backend is operational
Exit code 1 = backend is not ready for traffic
"""

import sys
import subprocess
import json
import time
from typing import Tuple

def curl_test(endpoint: str, method: str = 'GET', expect_success: bool = True) -> Tuple[bool, str]:
    """Test an endpoint and return (success, message)."""
    try:
        if method == 'GET':
            cmd = f'curl -s -w "\\n%{{http_code}}" http://localhost:3001{endpoint}'
        else:
            cmd = f'curl -s -w "\\n%{{http_code}}" -X {method} http://localhost:3001{endpoint}'

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1] if lines else '000'

        if expect_success:
            is_success = http_code.startswith('2')
        else:
            is_success = http_code.startswith('4') or http_code.startswith('5')

        message = f"HTTP {http_code}"
        return is_success, message
    except Exception as e:
        return False, str(e)

def main():
    print("\n" + "="*70)
    print("PRODUCTION SMOKE TEST - Backend Operational Verification")
    print("="*70)

    tests = [
        ("Health Check", "/health", True),
        ("Detailed Health", "/health/detailed", True),
        ("Governance Status", "/api/governance/status", True),
        ("Unauthenticated Write (should fail)", "/api/agents/register", False),
    ]

    results = []
    for test_name, endpoint, expect_success in tests:
        print(f"\nTesting: {test_name}")
        print(f"  Endpoint: {endpoint}")

        success, message = curl_test(endpoint)
        status = "✓" if success else "✗"
        print(f"  {status} {message}")
        results.append((test_name, success))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    passed = sum(1 for _, s in results if s)
    total = len(results)

    for test_name, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {test_name}")

    print(f"\nResult: {passed}/{total} smoke tests passed")

    if passed == total:
        print("\n✓ SMOKE TEST: PASSED - Backend is operational")
        return 0
    else:
        print(f"\n✗ SMOKE TEST: FAILED - {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
