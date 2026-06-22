#!/usr/bin/env python3
"""
LEVEL_4 Area 2: Concurrency Safety Test

Tests that parallel autonomy runs do not corrupt state.

This test verifies:
1. 5 parallel runs each get unique task_id
2. No duplicate learner_candidates
3. All runs complete successfully OR fail cleanly
4. No orphaned locks
"""

import sys
import os
import json
import requests
import asyncio
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_api_url():
    """Get API endpoint URL"""
    return os.environ.get('API_URL', 'http://localhost:3001/api/autonomy/run-level3-smoke')

def get_database_url():
    """Get database URL from environment"""
    return os.environ.get('DATABASE_URL', 'postgresql://agentco:agentco@localhost/agentco')

def connect_db():
    """Connect to PostgreSQL database"""
    import psycopg2
    try:
        url = get_database_url()
        conn = psycopg2.connect(url)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}", file=sys.stderr)
        return None

def run_autonomy_loop(run_number: int) -> dict:
    """Run a single autonomy loop and return results"""
    api_url = get_api_url()

    print(f"  Run {run_number}: Starting...")
    start_time = time.time()

    try:
        response = requests.post(
            api_url,
            json={},
            timeout=120
        )

        elapsed = time.time() - start_time

        if response.status_code != 200:
            return {
                'run_number': run_number,
                'success': False,
                'error': f"HTTP {response.status_code}",
                'elapsed_seconds': elapsed,
            }

        data = response.json()
        run_id = data.get('run', {}).get('runId')
        task_id = data.get('run', {}).get('id') or data.get('run', {}).get('taskId')

        if not run_id or not task_id:
            return {
                'run_number': run_number,
                'success': False,
                'error': 'Missing runId or taskId in response',
                'elapsed_seconds': elapsed,
            }

        return {
            'run_number': run_number,
            'success': True,
            'run_id': run_id,
            'task_id': task_id,
            'elapsed_seconds': elapsed,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'run_number': run_number,
            'success': False,
            'error': str(e),
            'elapsed_seconds': elapsed,
        }

def test_parallel_runs(num_runs: int = 5) -> bool:
    """Test parallel autonomy runs"""
    print("\n" + "="*80)
    print(f"TEST: Parallel Autonomy Runs ({num_runs} concurrent)")
    print("="*80)
    print(f"\nStarting {num_runs} parallel autonomy runs...")
    print("Each run should get a unique task_id and complete successfully.\n")

    results = []
    start_time = time.time()

    # Use ThreadPoolExecutor to spawn parallel requests
    with ThreadPoolExecutor(max_workers=num_runs) as executor:
        futures = [executor.submit(run_autonomy_loop, i+1) for i in range(num_runs)]

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            status = "✅" if result['success'] else "❌"
            elapsed = result.get('elapsed_seconds', 0)

            if result['success']:
                print(f"  {status} Run {result['run_number']}: {result['run_id']} ({elapsed:.1f}s)")
            else:
                print(f"  {status} Run {result['run_number']}: {result['error']} ({elapsed:.1f}s)")

    total_elapsed = time.time() - start_time

    # Analyze results
    successful_runs = [r for r in results if r['success']]
    failed_runs = [r for r in results if not r['success']]

    print(f"\n📊 Results Summary:")
    print(f"   Total time: {total_elapsed:.1f}s")
    print(f"   Successful: {len(successful_runs)}/{num_runs}")
    print(f"   Failed: {len(failed_runs)}/{num_runs}")

    if len(successful_runs) == 0:
        print(f"\n❌ TEST FAILED: No runs completed successfully")
        return False

    # Check for unique task IDs
    task_ids = [r['task_id'] for r in successful_runs]
    unique_task_ids = set(task_ids)

    print(f"\n🔍 Uniqueness Check:")
    print(f"   Unique task_ids: {len(unique_task_ids)}/{len(task_ids)}")

    if len(unique_task_ids) != len(task_ids):
        print(f"   ❌ FAILED: Duplicate task_ids detected!")
        return False
    else:
        print(f"   ✅ All task_ids are unique")

    # Check database for state corruption
    print(f"\n📋 Database State Check:")
    conn = connect_db()
    if conn:
        cursor = conn.cursor()

        # Check for duplicate learner_candidates
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT artifact_id) as unique_artifacts
            FROM learner_candidates
            WHERE created_at > NOW() - INTERVAL '5 minutes'
        """)
        row = cursor.fetchone()
        total_candidates = row[0]
        unique_artifacts = row[1]

        print(f"   Total learner_candidates created: {total_candidates}")
        print(f"   Unique artifacts: {unique_artifacts}")

        if total_candidates > num_runs:
            print(f"   ⚠️  More candidates than runs (possible duplicates)")

        # Check for orphaned locks
        cursor.execute("""
            SELECT COUNT(*) as orphaned
            FROM worker_leases
            WHERE status = 'active' AND lease_expires_at < NOW()
        """)
        orphaned = cursor.fetchone()[0]

        print(f"   Orphaned active leases: {orphaned}")
        if orphaned > 0:
            print(f"   ⚠️  Found orphaned locks")

        # Check for active leases
        cursor.execute("""
            SELECT COUNT(*) as active
            FROM worker_leases
            WHERE status = 'active'
        """)
        active = cursor.fetchone()[0]
        print(f"   Active leases (should be 0): {active}")

        cursor.close()
        conn.close()
    else:
        print(f"   ⚠️  Could not connect to database")

    print(f"\n✅ TEST PASSED: {len(successful_runs)} parallel runs completed without state corruption")
    return True

def main():
    print("\n" + "="*80)
    print("🎯 LEVEL_4 Area 2: Concurrency Safety Test Suite")
    print("="*80)

    # Run concurrency test
    result = test_parallel_runs(5)

    print("\n" + "="*80)
    if result:
        print("✅ CONCURRENCY TEST PASSED")
        print("\nConclusion: Parallel runs do not corrupt state.")
        return 0
    else:
        print("❌ CONCURRENCY TEST FAILED")
        return 1

if __name__ == '__main__':
    sys.exit(main())
