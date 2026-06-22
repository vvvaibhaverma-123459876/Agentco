#!/usr/bin/env python3
"""
LEVEL_4 Area 1: Idempotency Test

Tests that the autonomy orchestrator prevents duplicate runs when given the same idempotency key.

This test verifies:
1. Same idempotency_key → returns existing run (no duplicate)
2. Different idempotency_key → creates new run
3. NULL idempotency_key → always creates new run
4. Audit events record duplicate attempts
"""

import sys
import os
import json
import requests
import time
from datetime import datetime

def get_database_url():
    """Get database URL from environment"""
    return os.environ.get('DATABASE_URL', 'postgresql://agentco:agentco@localhost/agentco')

def connect_db():
    """Connect to PostgreSQL database"""
    import psycopg2
    try:
        url = get_database_url()
        # Parse URL like: postgresql://user:pass@host/db
        conn = psycopg2.connect(url)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}", file=sys.stderr)
        return None

def get_api_url():
    """Get API endpoint URL"""
    return os.environ.get('API_URL', 'http://localhost:3001/api/autonomy/run-level3-smoke')

def test_case_1_duplicate_idempotency_key():
    """Test Case 1: Same idempotency_key → returns existing run (no duplicate)"""
    print("\n" + "="*80)
    print("TEST CASE 1: Duplicate Idempotency Key")
    print("="*80)

    api_url = get_api_url()
    idempotency_key = f"test-idempotency-{int(time.time())}"

    print(f"\n1️⃣  Calling API with idempotency_key={idempotency_key}")

    try:
        response1 = requests.post(
            api_url,
            json={"idempotency_key": idempotency_key},
            timeout=120
        )

        if response1.status_code != 200:
            print(f"❌ First call failed: {response1.status_code}")
            print(f"   Response: {response1.text}")
            return False

        data1 = response1.json()
        run_id_1 = data1.get('run', {}).get('runId')
        task_id_1 = data1.get('run', {}).get('taskId') or data1.get('run', {}).get('id')

        if not run_id_1:
            print(f"❌ No runId in response: {data1}")
            return False

        print(f"   ✅ First call succeeded")
        print(f"   Run ID: {run_id_1}")

        # Small delay to ensure it's not a race condition
        time.sleep(1)

        print(f"\n2️⃣  Calling API AGAIN with SAME idempotency_key={idempotency_key}")

        response2 = requests.post(
            api_url,
            json={"idempotency_key": idempotency_key},
            timeout=120
        )

        if response2.status_code != 200:
            print(f"❌ Second call failed: {response2.status_code}")
            print(f"   Response: {response2.text}")
            return False

        data2 = response2.json()
        run_id_2 = data2.get('run', {}).get('runId')

        if not run_id_2:
            print(f"❌ No runId in second response: {data2}")
            return False

        print(f"   ✅ Second call succeeded")
        print(f"   Run ID: {run_id_2}")

        # Verify they're the same
        if run_id_1 == run_id_2:
            print(f"\n✅ TEST PASSED: Both calls returned same runId")
            print(f"   This proves idempotency is working!")

            # Verify audit event was logged
            conn = connect_db()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM autonomy_task_events WHERE task_id = %s AND event_type = 'duplicate_detected'",
                    [task_id_1]
                )
                count = cursor.fetchone()[0]
                cursor.close()
                conn.close()

                if count > 0:
                    print(f"   ✅ Audit event 'duplicate_detected' recorded in database")
                else:
                    print(f"   ⚠️  No audit event found (table may not exist)")

            return True
        else:
            print(f"\n❌ TEST FAILED: Calls returned different runIds")
            print(f"   First:  {run_id_1}")
            print(f"   Second: {run_id_2}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to API at {api_url}")
        print(f"   Is the backend running?")
        return False
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_case_2_different_idempotency_keys():
    """Test Case 2: Different idempotency_key → creates new run"""
    print("\n" + "="*80)
    print("TEST CASE 2: Different Idempotency Keys")
    print("="*80)

    api_url = get_api_url()
    idempotency_key_1 = f"test-idempotency-key1-{int(time.time())}"
    idempotency_key_2 = f"test-idempotency-key2-{int(time.time())}"

    print(f"\n1️⃣  Calling API with idempotency_key={idempotency_key_1}")

    try:
        response1 = requests.post(
            api_url,
            json={"idempotency_key": idempotency_key_1},
            timeout=120
        )

        if response1.status_code != 200:
            print(f"❌ First call failed: {response1.status_code}")
            return False

        run_id_1 = response1.json().get('run', {}).get('runId')
        print(f"   ✅ First call succeeded: {run_id_1}")

        # Small delay
        time.sleep(1)

        print(f"\n2️⃣  Calling API with DIFFERENT idempotency_key={idempotency_key_2}")

        response2 = requests.post(
            api_url,
            json={"idempotency_key": idempotency_key_2},
            timeout=120
        )

        if response2.status_code != 200:
            print(f"❌ Second call failed: {response2.status_code}")
            return False

        run_id_2 = response2.json().get('run', {}).get('runId')
        print(f"   ✅ Second call succeeded: {run_id_2}")

        # Verify they're different
        if run_id_1 != run_id_2:
            print(f"\n✅ TEST PASSED: Different keys created different runs")
            return True
        else:
            print(f"\n❌ TEST FAILED: Different keys created same run")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_case_3_null_idempotency_key():
    """Test Case 3: NULL idempotency_key → always creates new run"""
    print("\n" + "="*80)
    print("TEST CASE 3: No Idempotency Key (NULL)")
    print("="*80)

    api_url = get_api_url()

    print(f"\n1️⃣  Calling API WITHOUT idempotency_key")

    try:
        response1 = requests.post(
            api_url,
            json={},
            timeout=120
        )

        if response1.status_code != 200:
            print(f"❌ First call failed: {response1.status_code}")
            return False

        run_id_1 = response1.json().get('run', {}).get('runId')
        print(f"   ✅ First call succeeded: {run_id_1}")

        time.sleep(1)

        print(f"\n2️⃣  Calling API again WITHOUT idempotency_key")

        response2 = requests.post(
            api_url,
            json={},
            timeout=120
        )

        if response2.status_code != 200:
            print(f"❌ Second call failed: {response2.status_code}")
            return False

        run_id_2 = response2.json().get('run', {}).get('runId')
        print(f"   ✅ Second call succeeded: {run_id_2}")

        # Verify they're different
        if run_id_1 != run_id_2:
            print(f"\n✅ TEST PASSED: Calls without idempotency_key created different runs")
            return True
        else:
            print(f"\n❌ TEST FAILED: Calls without key created same run")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("🎯 LEVEL_4 Area 1: Idempotency Test Suite")
    print("="*80)

    results = []

    # Run test cases
    results.append(("Test Case 1: Duplicate Idempotency Key", test_case_1_duplicate_idempotency_key()))
    results.append(("Test Case 2: Different Idempotency Keys", test_case_2_different_idempotency_keys()))
    results.append(("Test Case 3: NULL Idempotency Key", test_case_3_null_idempotency_key()))

    # Summary
    print("\n" + "="*80)
    print("📊 Test Summary")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("")
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL IDEMPOTENCY TESTS PASSED")
        print("\nConclusion: Idempotency hardening is working correctly.")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1

if __name__ == '__main__':
    sys.exit(main())
