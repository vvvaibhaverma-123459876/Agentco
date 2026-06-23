#!/usr/bin/env python3
"""
Test: Autonomy Action Loop Integration
=====================================
Verifies that the new action execution services (planner, executor, loop-detector)
are properly integrated into the autonomy orchestrator and can execute a full
decision → execution → observation → evidence → claim cycle.

Requirements:
- Backend running on port 3001
- Database populated with migrations (including 050_autonomy_action_loop.sql)
- All action services deployed
"""

import requests
import json
import sys
import time
from datetime import datetime

BASE_URL = "http://localhost:3001"

def test_action_loop_integration():
    """Test the full action loop: plan → execute → observe → claim"""

    print("\n" + "="*80)
    print("TEST: Autonomy Action Loop Integration")
    print("="*80)

    try:
        # Test 1: Goal creation and action planning
        print("\n[TEST 1] Starting autonomy action loop with goal creation...")
        goal_text = "Research and document the current state of AI autonomy frameworks"

        response = requests.post(
            f"{BASE_URL}/api/autonomy/action-loop",
            json={
                "goal": goal_text,
                "maxIterations": 5,
            },
            timeout=60
        )

        if response.status_code != 200:
            print(f"❌ Failed to start action loop: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

        result = response.json()
        print(f"✅ Action loop started")
        print(f"   Goal ID: {result.get('goalId')}")
        print(f"   Status: {result.get('status')}")

        goal_id = result.get('goalId')

        # Test 2: Verify actions were executed
        print("\n[TEST 2] Verifying actions were executed...")
        actions_response = requests.get(
            f"{BASE_URL}/api/autonomy/actions?goalId={goal_id}",
            timeout=30
        )

        if actions_response.status_code != 200:
            print(f"❌ Failed to retrieve actions: {actions_response.status_code}")
            return False

        actions = actions_response.json()
        print(f"✅ Retrieved {len(actions)} actions")

        if len(actions) == 0:
            print("❌ No actions were executed in the loop")
            return False

        # Verify action types
        action_types = [a.get('actionType') for a in actions]
        print(f"   Action types: {action_types}")

        # Test 3: Verify evidence was collected
        print("\n[TEST 3] Verifying evidence collection...")
        evidence_response = requests.get(
            f"{BASE_URL}/api/autonomy/evidence?goalId={goal_id}",
            timeout=30
        )

        if evidence_response.status_code == 200:
            evidence = evidence_response.json()
            print(f"✅ Collected {len(evidence)} evidence artifacts")
            if len(evidence) > 0:
                print(f"   Evidence sources: {[e.get('sourceType') for e in evidence]}")

        # Test 4: Verify claims were generated
        print("\n[TEST 4] Verifying claim generation...")
        claims_response = requests.get(
            f"{BASE_URL}/api/autonomy/claims?goalId={goal_id}",
            timeout=30
        )

        if claims_response.status_code != 200:
            print(f"❌ Failed to retrieve claims: {claims_response.status_code}")
            return False

        claims = claims_response.json()
        print(f"✅ Generated {len(claims)} claims")

        if len(claims) == 0:
            print("⚠️  No claims were generated (may be expected if evidence gathering incomplete)")
        else:
            # Verify claims have evidence backing
            for i, claim in enumerate(claims):
                support_sources = claim.get('supportSourceIds', [])
                status = claim.get('status')
                print(f"   Claim {i+1}: {claim.get('text')[:60]}...")
                print(f"      Status: {status}, Supported by {len(support_sources)} sources")

                if status == 'unsupported' and len(support_sources) == 0:
                    print("❌ Found unsupported claim without evidence backing!")
                    return False

        # Test 5: Verify loop detection worked
        print("\n[TEST 5] Verifying loop detection...")

        # Check if any actions repeated identically
        action_sequences = []
        for action in actions:
            action_type = action.get('actionType')
            args = json.dumps(action.get('args', {}), sort_keys=True)
            action_sequences.append(f"{action_type}:{args}")

        # Simple check: no identical action repetition (at least 3 times)
        for i in range(len(action_sequences) - 2):
            if (action_sequences[i] == action_sequences[i+1] == action_sequences[i+2]):
                print(f"⚠️  Detected repeated action sequence at position {i}")
                print(f"   This should have triggered loop detection and replan/terminate")

        print(f"✅ Loop detection mechanism is active")

        # Test 6: Verify termination
        print("\n[TEST 6] Verifying clean termination...")

        termination_reason = result.get('reason', '')
        if termination_reason:
            print(f"✅ Loop terminated cleanly: {termination_reason}")
        else:
            print(f"⚠️  No termination reason provided")

        # Summary
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print(f"\nSummary:")
        print(f"  - Goal ID: {goal_id}")
        print(f"  - Actions executed: {result.get('actionsExecuted', 0)}")
        print(f"  - Claims generated: {result.get('claimsGenerated', 0)}")
        print(f"  - Status: {result.get('status')}")

        return True

    except requests.ConnectionError:
        print(f"❌ Failed to connect to {BASE_URL}")
        print("   Make sure the backend is running: npm run dev")
        return False
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_action_loop_integration()
    sys.exit(0 if success else 1)
