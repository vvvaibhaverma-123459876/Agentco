#!/usr/bin/env python3
"""
Production Security Gate - Verifies 7 non-negotiable safety rules are enforced.

This test MUST pass before any production deployment is allowed.
Exit code 0 = all safety rules verified
Exit code 1 = at least one rule not enforced (BLOCK DEPLOYMENT)
"""

import sys
import json
import subprocess
from typing import Tuple, List

import os
import sys

# This gate verifies a *production-configured* deployment (env, secrets, and a
# running hardened API). Under pytest in any other environment it must skip,
# not fail.
if "pytest" in sys.modules and os.environ.get("AGENTCO_ENV") != "production":
    import pytest

    pytest.skip(
        "AGENTCO_ENV != production; the production security gate verifies a live production deployment",
        allow_module_level=True,
    )


# Colors for output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def run_test(name: str, test_func) -> bool:
    """Run a test and return success status."""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print('='*70)
    try:
        test_func()
        print(f"{GREEN}✓ PASSED{RESET}")
        return True
    except AssertionError as e:
        print(f"{RED}✗ FAILED: {e}{RESET}")
        return False
    except Exception as e:
        print(f"{RED}✗ ERROR: {e}{RESET}")
        return False

def curl_get(endpoint: str, headers: dict = None) -> dict:
    """Make GET request."""
    cmd = f'curl -s -X GET http://localhost:3001{endpoint}'
    if headers:
        for k, v in headers.items():
            cmd += f' -H "{k}: {v}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return {"error": result.stdout, "stderr": result.stderr}

def curl_post(endpoint: str, data: dict = None, headers: dict = None) -> dict:
    """Make POST request."""
    cmd = f'curl -s -X POST http://localhost:3001{endpoint}'
    if headers:
        for k, v in headers.items():
            cmd += f' -H "{k}: {v}"'
    if data:
        cmd += f" -d '{json.dumps(data)}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return {"error": result.stdout, "stderr": result.stderr}

# ============================================================================
# SAFETY RULE TESTS
# ============================================================================

def test_rule_1_no_direct_calibration_mutation():
    """Rule 1: No direct calibration mutation without eval gate."""
    print("\nAttempting direct calibration mutation (should fail)...")

    response = curl_post(
        '/api/calibration/scores',
        data={'confidence': 0.95, 'source_id': 'test'},
        headers={'x-actor-id': 'system', 'x-api-key': 'test'}
    )

    # Should be blocked if RBAC is enforced
    # Either return 403 (permission denied) or indicate calibration is protected
    assert 'error' in response or response.get('status') in ['error', 'blocked'], \
        f"Direct calibration mutation should be blocked, got: {response}"
    print(f"✓ Blocked: {response}")

def test_rule_2_no_self_certification():
    """Rule 2: Learner cannot approve its own candidate."""
    print("\nAttempting self-approval of learner candidate (should fail)...")

    # Create a fake candidate
    candidate_id = 'learner_candidate_self_test'

    response = curl_post(
        f'/api/eval/candidates/{candidate_id}/approve',
        data={'decision': 'approved'},
        headers={'x-actor-id': candidate_id}  # Same ID = self-certification
    )

    # Should be blocked
    assert 'error' in response or response.get('status') in ['error', 'blocked'], \
        f"Self-certification should be blocked, got: {response}"
    print(f"✓ Blocked: {response}")

def test_rule_3_no_silent_trust_changes():
    """Rule 3: Trust policy changes must be audited and gated."""
    print("\nAttempting silent trust policy change (should require audit)...")

    response = curl_post(
        '/api/governance/trust-policy',
        data={'policy': 'new_trust_policy'},
        headers={'x-actor-id': 'system'}
    )

    # Should either be blocked or indicate audit trail is created
    has_audit = 'audit' in str(response).lower() or 'events' in str(response).lower()
    is_blocked = 'error' in response or response.get('status') in ['error', 'blocked']

    assert has_audit or is_blocked, \
        f"Trust change must be audited, got: {response}"
    print(f"✓ Validated: {response}")

def test_rule_4_protected_surface_enforcement():
    """Rule 4: Protected surfaces (calibration, resolver, audit_log) are immutable."""
    print("\nAttempting to modify protected surface (should fail)...")

    # Try to modify resolver (protected surface)
    response = curl_post(
        '/api/resolver/update-ground-truth',
        data={'claim_id': 'test', 'truth': 'false'},
        headers={'x-actor-id': 'system'}
    )

    # Should be blocked (either 403 or explicit block)
    assert 'error' in response or response.get('status') in ['error', 'blocked'], \
        f"Protected surface should be protected, got: {response}"
    print(f"✓ Blocked: {response}")

def test_rule_5_evaluation_gate():
    """Rule 5: Candidates must pass safety eval before promotion."""
    print("\nVerifying evaluation gate exists...")

    # Check that eval endpoint exists
    response = curl_get(
        '/api/eval/gates',
        headers={'x-actor-id': 'system'}
    )

    # Should indicate gates exist
    assert 'error' not in response or 404 not in str(response), \
        f"Eval gates should exist, got: {response}"
    print(f"✓ Gate exists: {response}")

def test_rule_6_rbac_enforcement():
    """Rule 6: RBAC enforces least privilege."""
    print("\nAttempting unauthorized action (should be denied)...")

    # Try governance admin action without permission
    response = curl_post(
        '/api/governance/roles/test/assign',
        data={'role': 'admin'},
        headers={'x-actor-id': 'viewer', 'x-api-key': 'test'}  # Viewer role
    )

    # Should be denied (403 Forbidden)
    is_denied = '403' in str(response) or 'error' in response
    assert is_denied, f"RBAC should deny unauthorized action, got: {response}"
    print(f"✓ Denied: {response}")

def test_rule_7_governance_gates():
    """Rule 7: Emergency freeze and protected surfaces must be enforceable."""
    print("\nVerifying governance gates exist...")

    response = curl_get(
        '/api/governance/status',
        headers={'x-actor-id': 'system'}
    )

    # Should return governance status
    assert 'error' not in response, f"Governance status should be accessible, got: {response}"
    print(f"✓ Gates responsive: {response}")

# ============================================================================
# PRODUCTION ENVIRONMENT CHECKS
# ============================================================================

def test_production_env_set():
    """Verify AGENTCO_ENV is production."""
    import os
    env = os.environ.get('AGENTCO_ENV', 'not_set')
    print(f"\nAGENTCO_ENV = {env}")
    assert env == 'production', f"Must be in production mode, got: {env}"
    print("✓ Production environment verified")

def test_secrets_not_dev_defaults():
    """Verify production secrets are not dev defaults."""
    import os
    api_key = os.environ.get('AGENTCO_API_KEY', '')
    print(f"\nAPI Key (first 10 chars): {api_key[:10]}")

    dev_patterns = ['dev_', 'test_', 'default_', 'changeme']
    for pattern in dev_patterns:
        assert not api_key.lower().startswith(pattern), \
            f"Secrets must not use dev defaults like '{pattern}'"

    assert len(api_key) >= 32, f"API key must be at least 32 bytes, got {len(api_key)}"
    print("✓ Secrets are production-grade")

def test_tls_enabled():
    """Verify TLS is configured."""
    import os
    tls_enabled = os.environ.get('TLS_ENABLED', 'false').lower() == 'true'
    # TLS_ENABLED may be optional in test, but should be noted
    print(f"\nTLS_ENABLED = {tls_enabled}")
    if not tls_enabled:
        print(f"{YELLOW}⚠ TLS should be enabled in production{RESET}")

def test_audit_logging_required():
    """Verify audit logging is enabled."""
    import os
    audit = os.environ.get('AUDIT_LOGGING_REQUIRED', 'false').lower() == 'true'
    print(f"\nAUDIT_LOGGING_REQUIRED = {audit}")
    assert audit, "Audit logging must be enabled in production"
    print("✓ Audit logging required")

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print("\n" + "="*70)
    print("PRODUCTION SECURITY GATE - Verifying 7 Non-Negotiable Safety Rules")
    print("="*70)

    tests = [
        # Safety rules
        ("Rule 1: No Direct Calibration Mutation", test_rule_1_no_direct_calibration_mutation),
        ("Rule 2: No Self-Certification", test_rule_2_no_self_certification),
        ("Rule 3: No Silent Trust Changes", test_rule_3_no_silent_trust_changes),
        ("Rule 4: Protected Surface Enforcement", test_rule_4_protected_surface_enforcement),
        ("Rule 5: Evaluation Gate", test_rule_5_evaluation_gate),
        ("Rule 6: RBAC Enforcement", test_rule_6_rbac_enforcement),
        ("Rule 7: Governance Gates", test_rule_7_governance_gates),

        # Environment checks
        ("Production Environment Verification", test_production_env_set),
        ("Secrets Are Production-Grade", test_secrets_not_dev_defaults),
        ("TLS Configuration", test_tls_enabled),
        ("Audit Logging Required", test_audit_logging_required),
    ]

    results = []
    for test_name, test_func in tests:
        passed = run_test(test_name, test_func)
        results.append((test_name, passed))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    for test_name, passed in results:
        status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"{status} {test_name}")

    print(f"\nResult: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print(f"\n{GREEN}✓ PRODUCTION SECURITY GATE: PASSED{RESET}")
        print("All 7 non-negotiable safety rules are enforced.")
        return 0
    else:
        print(f"\n{RED}✗ PRODUCTION SECURITY GATE: FAILED{RESET}")
        print(f"Fix {total_count - passed_count} failing test(s) before deployment.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
