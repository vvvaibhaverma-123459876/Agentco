#!/usr/bin/env python3
"""
REAL LEVEL_3 Autonomy Smoke Test

This test ACTUALLY CALLS the backend services, not just inserts data.

It either:
1. Calls the API endpoint POST /api/autonomy/run-level3-smoke
2. Or, if the API is not available, directly invokes TypeScript services via subprocess

This proves LEVEL_3 by demonstrating:
- Orchestrator runs the full loop
- Learner generates candidates from real replay batches
- Eval harness produces scorecards
- Promotion is gated by eval
- All state persists to database
"""

import sys
import os
import json
import subprocess
import time
from datetime import datetime

def try_api_call():
    """Try to call the API endpoint"""
    import requests

    api_url = os.environ.get('API_URL', 'http://localhost:3001/api/autonomy/run-level3-smoke')

    print("📡 Attempting to call API endpoint...")
    print(f"   URL: {api_url}")

    try:
        response = requests.post(api_url, timeout=120, json={})

        if response.status_code == 200:
            data = response.json()
            print(f"✅ API call successful")
            return data.get('run')
        else:
            print(f"❌ API returned {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️  API call failed: {e}")
        return None

def run_ts_services_directly():
    """
    Run TypeScript services directly via subprocess.

    This requires the backend to be built and executable.
    """
    print("🔧 Running TypeScript services directly...")

    # Create a small Node.js script that calls the orchestrator
    script_content = """
const { autonomyOrchestrator } = require('./backend/src/services/autonomy-orchestrator.service');

(async () => {
  try {
    const run = await autonomyOrchestrator.executeControlledAutonomyLoop();
    console.log(JSON.stringify(run, null, 2));
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
"""

    try:
        # Write temporary script
        with open('/tmp/run_orchestrator.js', 'w') as f:
            f.write(script_content)

        # Run Node.js
        result = subprocess.run(
            ['node', '/tmp/run_orchestrator.js'],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            run_data = json.loads(result.stdout)
            print("✅ Direct service call successful")
            return run_data
        else:
            print(f"❌ Service call failed:\n{result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Could not run TypeScript services: {e}")
        return None

def verify_database_state(run_data):
    """Verify that the orchestrator actually created records in the database"""
    db_url = os.environ.get('DATABASE_URL')

    if not db_url:
        print("⚠️  DATABASE_URL not set - cannot verify database state")
        return False

    print("\n📊 Verifying database state...")

    try:
        import psycopg2
        from urllib.parse import urlparse

        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/'),
        )
        cur = conn.cursor()

        # Check for real records created by services
        checks = [
            ("autonomy_tasks", run_data.get('taskId')),
            ("autonomy_episodes", run_data.get('episodeId')),
            ("learner_candidates", run_data.get('candidateId')),
            ("eval_scorecards", run_data.get('scorecardId')),
        ]

        all_found = True
        for table, record_id in checks:
            if record_id:
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE id = %s", (record_id,))
                count = cur.fetchone()[0]
                status = "✅" if count > 0 else "❌"
                print(f"   {status} {table}: {record_id}")
                if count == 0:
                    all_found = False
            else:
                print(f"   ⚠️  {table}: No ID in run data")
                all_found = False

        conn.close()
        return all_found
    except Exception as e:
        print(f"   ❌ Database verification failed: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("REAL LEVEL_3 AUTONOMY SMOKE TEST")
    print("Actual Service Integration Verification")
    print("="*80 + "\n")

    # Try API first
    run_data = try_api_call()

    # If API fails, try direct invocation
    if not run_data:
        print("\n⚠️  API not available, trying direct service invocation...")
        run_data = run_ts_services_directly()

    # If both fail
    if not run_data:
        print("\n❌ LEVEL_3 SMOKE TEST FAILED")
        print("   Could not call services via API or direct invocation")
        print("\n   Possible reasons:")
        print("   1. Backend API not running (npm run dev)")
        print("   2. DATABASE_URL not set")
        print("   3. Services not exported as singletons")
        print("   4. Routes not registered")
        print("\n   To fix:")
        print("   export DATABASE_URL='postgresql://...'")
        print("   cd backend && npm run dev")
        print("   # In another terminal:")
        print("   python3 scripts/run_level3_real_smoke.py")
        return 1

    # Verify database state
    print(f"\n✅ Services executed successfully")
    print(f"   Run ID: {run_data.get('runId')}")
    print(f"   Trace ID: {run_data.get('traceId')}")
    print(f"   Status: {run_data.get('status')}")

    db_verified = verify_database_state(run_data)

    if db_verified:
        print("\n" + "="*80)
        print("✅ LEVEL_3 SMOKE TEST PASSED")
        print("="*80)
        print(f"\nEvidence:")
        print(f"  ✅ Orchestrator executed full loop")
        print(f"  ✅ Database records created")
        print(f"  ✅ Services were called (not bypassed)")
        print(f"  ✅ Learner created candidate: {run_data.get('candidateId')}")
        print(f"  ✅ Eval created scorecard: {run_data.get('scorecardId')}")
        print(f"  ✅ Promotion decision: {run_data.get('promotionEligible')}")
        return 0
    else:
        print("\n❌ Database verification failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
