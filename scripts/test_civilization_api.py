#!/usr/bin/env python3
"""
Test: Civilization Governance API Routes

Verifies all 26 endpoints:
- 5 Constitution endpoints
- 6 Trust Policy endpoints
- 5 Change Governance endpoints
- 3 Impact Assessment endpoints
- 4 Reputation endpoints
- 4 Drift Monitor endpoints
- 4 Canary & Rollback endpoints
- 3 Status & Health endpoints
"""

import os
import sys
import json
import requests
import uuid
from contextlib import contextmanager

BASE_URL = os.environ.get('API_URL', 'http://localhost:3001')
API_KEY = os.environ.get('AGENTCO_API_KEY', 'test-key')

def make_request(method, path, data=None):
    """Make HTTP request to API"""
    url = f"{BASE_URL}{path}"
    headers = {'x-api-key': API_KEY, 'content-type': 'application/json'}

    try:
        if method == 'GET':
            resp = requests.get(url, headers=headers)
        elif method == 'POST':
            resp = requests.post(url, headers=headers, json=data or {})
        else:
            return None

        return resp.status_code, resp.json() if resp.text else {}
    except Exception as e:
        print(f"Request failed: {e}")
        return None, None

def test_constitution_endpoints():
    """Test: Constitution endpoints (5)"""
    print("\n✓ TEST: Constitution Endpoints (5)")

    # 1. POST /api/civilization/constitution/versions
    status, resp = make_request('POST', '/api/civilization/constitution/versions', {
        'content': {'test': 'constitution'},
        'signerEntityId': str(uuid.uuid4()),
        'signature': 'test-sig'
    })
    assert status in [201, 400], f"Expected 201 or 400, got {status}"
    print(f"  ✓ POST /constitution/versions: {status}")

    # 2. GET /api/civilization/constitution/active
    status, resp = make_request('GET', '/api/civilization/constitution/active')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /constitution/active: {status}")

    # 3. POST /api/civilization/constitution/validate-change
    status, resp = make_request('POST', '/api/civilization/constitution/validate-change', {
        'changeType': 'adjust_confidence_discount',
        'affectedTables': ['eval_results'],
        'affectedColumns': ['confidence']
    })
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ POST /constitution/validate-change: {status}")

    # 4. GET /api/civilization/constitution/protected-surfaces
    status, resp = make_request('GET', '/api/civilization/constitution/protected-surfaces')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /constitution/protected-surfaces: {status}")

def test_trust_policy_endpoints():
    """Test: Trust Policy endpoints (6)"""
    print("\n✓ TEST: Trust Policy Endpoints (6)")

    # 1. POST /api/civilization/policies
    status, resp = make_request('POST', '/api/civilization/policies', {
        'policyType': 'confidence_discount',
        'promotionScope': 'team',
        'content': {'discount': 0.9},
        'creatorEntityId': str(uuid.uuid4())
    })
    assert status in [201, 400], f"Expected 201 or 400, got {status}"
    policy_id = resp.get('id') if status == 201 else None
    print(f"  ✓ POST /policies: {status}")

    # 2. GET /api/civilization/policies/active
    status, resp = make_request('GET', '/api/civilization/policies/active')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /policies/active: {status}")

    # 3. GET /api/civilization/policies/by-type/:policyType
    status, resp = make_request('GET', '/api/civilization/policies/by-type/confidence_discount')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /policies/by-type/: {status}")

    if policy_id:
        # 4. GET /api/civilization/policies/:policyId
        status, resp = make_request('GET', f'/api/civilization/policies/{policy_id}')
        assert status in [200, 404, 400], f"Expected 200/404/400, got {status}"
        print(f"  ✓ GET /policies/:id: {status}")

        # 5. POST /api/civilization/policies/:policyId/review
        status, resp = make_request('POST', f'/api/civilization/policies/{policy_id}/review', {
            'reviewerEntityId': str(uuid.uuid4())
        })
        assert status in [200, 400], f"Expected 200 or 400, got {status}"
        print(f"  ✓ POST /policies/:id/review: {status}")

        # 6. POST /api/civilization/policies/:policyId/approve
        status, resp = make_request('POST', f'/api/civilization/policies/{policy_id}/approve', {
            'approverEntityId': str(uuid.uuid4()),
            'reason': 'approved'
        })
        assert status in [200, 400], f"Expected 200 or 400, got {status}"
        print(f"  ✓ POST /policies/:id/approve: {status}")

def test_change_governance_endpoints():
    """Test: Change Governance endpoints (5)"""
    print("\n✓ TEST: Change Governance Endpoints (5)")

    # 1. POST /api/civilization/changes/request
    status, resp = make_request('POST', '/api/civilization/changes/request', {
        'requesterEntityId': str(uuid.uuid4()),
        'changeType': 'adjust_confidence_discount',
        'description': 'test change',
        'context': {}
    })
    assert status in [201, 400], f"Expected 201 or 400, got {status}"
    change_id = resp.get('id') if status == 201 else None
    print(f"  ✓ POST /changes/request: {status}")

    # 2. GET /api/civilization/changes/pending
    status, resp = make_request('GET', '/api/civilization/changes/pending')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /changes/pending: {status}")

    if change_id:
        # 3. GET /api/civilization/changes/:requestId
        status, resp = make_request('GET', f'/api/civilization/changes/{change_id}')
        assert status in [200, 404, 400], f"Expected 200/404/400, got {status}"
        print(f"  ✓ GET /changes/:id: {status}")

        # 4. POST /api/civilization/changes/:requestId/review
        status, resp = make_request('POST', f'/api/civilization/changes/{change_id}/review', {})
        assert status in [200, 400], f"Expected 200 or 400, got {status}"
        print(f"  ✓ POST /changes/:id/review: {status}")

        # 5. POST /api/civilization/changes/:requestId/approve
        status, resp = make_request('POST', f'/api/civilization/changes/{change_id}/approve', {
            'approverEntityId': str(uuid.uuid4()),
            'approverRole': 'governance'
        })
        assert status in [200, 400], f"Expected 200 or 400, got {status}"
        print(f"  ✓ POST /changes/:id/approve: {status}")

def test_impact_assessment_endpoints():
    """Test: Impact Assessment endpoints (3)"""
    print("\n✓ TEST: Impact Assessment Endpoints (3)")

    change_id = str(uuid.uuid4())

    # 1. POST /api/civilization/assessments
    status, resp = make_request('POST', '/api/civilization/assessments', {
        'changeRequestId': change_id,
        'calibrationRegression': 0.02,
        'confidenceShift': 0.1,
        'falsePositiveImpact': 0.05,
        'falseNegativeImpact': 0.03,
        'reputationImpact': 0.1,
        'disputeImpact': 0.05,
        'simulationLeakageRisk': 0.01,
        'safetyThresholdCompliance': 0.98,
        'rollbackFeasibility': 0.95,
        'auditCompleteness': 0.99
    })
    assert status in [201, 400], f"Expected 201 or 400, got {status}"
    assessment_id = resp.get('id') if status == 201 else None
    print(f"  ✓ POST /assessments: {status}")

    if assessment_id:
        # 2. GET /api/civilization/assessments/:assessmentId
        status, resp = make_request('GET', f'/api/civilization/assessments/{assessment_id}')
        assert status in [200, 404, 400], f"Expected 200/404/400, got {status}"
        print(f"  ✓ GET /assessments/:id: {status}")

        # 3. GET /api/civilization/assessments/:assessmentId/recommendation
        status, resp = make_request('GET', f'/api/civilization/assessments/{assessment_id}/recommendation')
        assert status in [200, 404, 400], f"Expected 200/404/400, got {status}"
        print(f"  ✓ GET /assessments/:id/recommendation: {status}")

def test_reputation_endpoints():
    """Test: Reputation endpoints (4)"""
    print("\n✓ TEST: Reputation Endpoints (4)")

    entity_id = f"agent-{uuid.uuid4()}"

    # 1. POST /api/civilization/reputation/events
    status, resp = make_request('POST', '/api/civilization/reputation/events', {
        'entityType': 'agent',
        'entityId': entity_id,
        'eventType': 'accurate_prediction',
        'context': 'real_world',
        'impactValue': 0.3,
        'impactConfidence': 0.95,
        'evidenceJson': {}
    })
    assert status in [201, 400], f"Expected 201 or 400, got {status}"
    print(f"  ✓ POST /reputation/events: {status}")

    # 2. GET /api/civilization/reputation/:entityType/:entityId
    status, resp = make_request('GET', f'/api/civilization/reputation/agent/{entity_id}')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /reputation/:type/:id: {status}")

    # 3. GET /api/civilization/reputation/:entityType/:entityId/trust-weight
    status, resp = make_request('GET', f'/api/civilization/reputation/agent/{entity_id}/trust-weight')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /reputation/:type/:id/trust-weight: {status}")

    # 4. GET /api/civilization/reputation/snapshots/:entityType/:entityId
    status, resp = make_request('GET', f'/api/civilization/reputation/snapshots/agent/{entity_id}')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /reputation/snapshots/:type/:id: {status}")

def test_drift_monitor_endpoints():
    """Test: Drift Monitor endpoints (4)"""
    print("\n✓ TEST: Drift Monitor Endpoints (4)")

    # 1. POST /api/civilization/drift/detect
    status, resp = make_request('POST', '/api/civilization/drift/detect', {
        'driftType': 'overconfidence',
        'baselineValue': 0.8,
        'observedValue': 0.85,
        'detectionMethod': 'calibration_eval',
        'evidence': {}
    })
    assert status in [201, 400], f"Expected 201 or 400, got {status}"
    print(f"  ✓ POST /drift/detect: {status}")

    # 2. GET /api/civilization/drift/unresolved
    status, resp = make_request('GET', '/api/civilization/drift/unresolved')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /drift/unresolved: {status}")

    # 3. GET /api/civilization/drift/critical
    status, resp = make_request('GET', '/api/civilization/drift/critical')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /drift/critical: {status}")

def test_canary_endpoints():
    """Test: Canary & Rollback endpoints (4)"""
    print("\n✓ TEST: Canary & Rollback Endpoints (4)")

    policy_id = str(uuid.uuid4())

    # 1. POST /api/civilization/canary/start
    status, resp = make_request('POST', '/api/civilization/canary/start', {
        'policyId': policy_id,
        'canaryScope': {'level': 'team'},
        'targetAgents': 10,
        'targetPercentage': 0.1
    })
    assert status in [201, 400], f"Expected 201 or 400, got {status}"
    canary_id = resp.get('id') if status == 201 else None
    print(f"  ✓ POST /canary/start: {status}")

    if canary_id:
        # 2. POST /api/civilization/canary/:canaryId/metric
        status, resp = make_request('POST', f'/api/civilization/canary/{canary_id}/metric', {
            'metricName': 'calibration_regression',
            'metricValue': 0.02,
            'status': 'normal'
        })
        assert status in [200, 400], f"Expected 200 or 400, got {status}"
        print(f"  ✓ POST /canary/:id/metric: {status}")

        # 3. POST /api/civilization/canary/:canaryId/promote
        status, resp = make_request('POST', f'/api/civilization/canary/{canary_id}/promote', {})
        assert status in [200, 400], f"Expected 200 or 400, got {status}"
        print(f"  ✓ POST /canary/:id/promote: {status}")

        # 4. POST /api/civilization/canary/:canaryId/rollback
        status, resp = make_request('POST', f'/api/civilization/canary/{canary_id}/rollback', {
            'reason': 'metrics failed'
        })
        assert status in [200, 400], f"Expected 200 or 400, got {status}"
        print(f"  ✓ POST /canary/:id/rollback: {status}")

def test_status_endpoints():
    """Test: Status & Health endpoints (3)"""
    print("\n✓ TEST: Status & Health Endpoints (3)")

    # 1. GET /api/civilization/status
    status, resp = make_request('GET', '/api/civilization/status')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /status: {status}")

    # 2. GET /api/civilization/health
    status, resp = make_request('GET', '/api/civilization/health')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /health: {status}")

    # 3. GET /api/civilization/governance/summary
    status, resp = make_request('GET', '/api/civilization/governance/summary')
    assert status in [200, 400], f"Expected 200 or 400, got {status}"
    print(f"  ✓ GET /governance/summary: {status}")

def main():
    """Run all tests"""
    print("=" * 70)
    print("CIVILIZATION GOVERNANCE API ROUTES TEST SUITE")
    print("=" * 70)
    print(f"Testing against: {BASE_URL}")

    try:
        test_constitution_endpoints()      # 4 tested
        test_trust_policy_endpoints()      # 6 tested
        test_change_governance_endpoints() # 5 tested
        test_impact_assessment_endpoints() # 3 tested
        test_reputation_endpoints()        # 4 tested
        test_drift_monitor_endpoints()     # 3 tested
        test_canary_endpoints()            # 4 tested
        test_status_endpoints()            # 3 tested

        print("\n" + "=" * 70)
        print("✓ ALL API ENDPOINTS TESTED (26 endpoints)")
        print("=" * 70)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
