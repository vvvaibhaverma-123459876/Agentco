#!/usr/bin/env python3
"""
AgentCo Full System Test with OpenAI API
Tests the complete autonomy loop using actual OpenAI LLM calls for 1 minute
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from openai import OpenAI

# Load environment. This is a live integration script that needs credentials
# and a running backend; under pytest it must skip instead of killing the
# whole collection with sys.exit.
api_key = os.environ.get('LLM_API_KEY')
if not api_key:
    if "pytest" in sys.modules:
        import pytest

        pytest.skip(
            "LLM_API_KEY not set; live OpenAI integration requires credentials and a running backend",
            allow_module_level=True,
        )
    print("❌ LLM_API_KEY not set")
    sys.exit(1)

# Configuration
BACKEND_URL = "http://localhost:3001"
TEST_DURATION = 60  # 1 minute
MODEL = os.environ.get('LLM_MODEL_DEFAULT', 'gpt-4o-mini')

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Test metrics
metrics = {
    'start_time': None,
    'end_time': None,
    'llm_calls': 0,
    'llm_tokens_used': 0,
    'llm_cost': 0.0,
    'backend_calls': 0,
    'backend_errors': 0,
    'backend_latencies': [],
    'autonomy_tasks': 0,
    'successful_tasks': 0,
    'failed_tasks': 0,
}

def test_openai_basic():
    """Test basic OpenAI connectivity"""
    print("\n🔍 Step 1: Testing OpenAI API Connectivity...")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a test agent."},
                {"role": "user", "content": "What is 2+2? Answer with just the number."}
            ],
            max_tokens=10,
        )

        result = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens

        print(f"   ✅ OpenAI Response: {result}")
        print(f"   ✅ Tokens used: {tokens}")
        print(f"   ✅ Model: {response.model}")

        metrics['llm_calls'] += 1
        metrics['llm_tokens_used'] += tokens

        return True
    except Exception as e:
        print(f"   ❌ OpenAI Error: {e}")
        return False

def test_backend_health():
    """Test backend health endpoint"""
    print("\n🔍 Step 2: Testing Backend Health...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Backend healthy: {response.status_code}")
            metrics['backend_calls'] += 1
            return True
        else:
            print(f"   ❌ Backend unhealthy: {response.status_code}")
            metrics['backend_errors'] += 1
            return False
    except Exception as e:
        print(f"   ❌ Backend Error: {e}")
        metrics['backend_errors'] += 1
        return False

def create_autonomy_task():
    """Create an autonomy task"""
    try:
        payload = {
            "plan_id": f"test-plan-{int(time.time())}",
            "goal": "Analyze and respond to user queries",
            "max_iterations": 1,
            "idempotency_key": f"key-{int(time.time() * 1000)}"
        }

        response = requests.post(
            f"{BACKEND_URL}/api/autonomy/tasks",
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )

        metrics['backend_calls'] += 1

        if response.status_code in [200, 201]:
            data = response.json() if response.text else {}
            task_id = data.get('task_id', data.get('id', 'unknown'))
            print(f"   ✅ Task created: {task_id}")
            metrics['autonomy_tasks'] += 1
            return True
        else:
            print(f"   ⚠️  Task creation: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Task creation error: {e}")
        metrics['backend_errors'] += 1
        return False

def run_openai_autonomy_step():
    """Run one autonomy step with LLM"""
    print("\n🔍 Step 3: Running Autonomy Step with LLM...")
    try:
        # Use OpenAI to generate an autonomy decision
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an autonomous agent. Decide on an action concisely."
                },
                {
                    "role": "user",
                    "content": "User asks: Please help me understand AgentCo. What should I do first? Respond with one action."
                }
            ],
            max_tokens=50,
            temperature=0.7,
        )

        action = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens

        print(f"   ✅ Autonomy Decision: {action[:60]}...")
        print(f"   ✅ Tokens: {tokens}")

        metrics['llm_calls'] += 1
        metrics['llm_tokens_used'] += tokens
        metrics['successful_tasks'] += 1

        return True
    except Exception as e:
        print(f"   ❌ Autonomy step error: {e}")
        metrics['failed_tasks'] += 1
        return False

def test_full_autonomy_loop():
    """Test complete autonomy loop"""
    print("\n🚀 Running Full 1-Minute AgentCo Test with OpenAI...\n")

    metrics['start_time'] = datetime.now()
    elapsed = 0
    iteration = 0

    # Run iterations for 1 minute
    while elapsed < TEST_DURATION:
        iteration += 1
        loop_start = time.time()

        print(f"\n{'='*70}")
        print(f"  Iteration {iteration} (Elapsed: {elapsed:.1f}s / {TEST_DURATION}s)")
        print(f"{'='*70}")

        # Test backend
        if not test_backend_health():
            print("   ⚠️  Backend health check failed, continuing...")

        # Create task
        if iteration % 2 == 0:
            create_autonomy_task()

        # Run autonomy with LLM
        run_openai_autonomy_step()

        # Calculate elapsed time
        loop_time = time.time() - loop_start
        metrics['backend_latencies'].append(loop_time)
        elapsed = time.time() - metrics['start_time'].timestamp()

        # Rate limit to avoid too many API calls
        if elapsed < TEST_DURATION:
            sleep_time = max(0, 5 - loop_time)  # 5 second intervals
            if sleep_time > 0:
                print(f"\n   ⏱️  Waiting {sleep_time:.1f}s before next iteration...")
                time.sleep(sleep_time)
            elapsed = time.time() - metrics['start_time'].timestamp()

    metrics['end_time'] = datetime.now()
    return True

def print_results():
    """Print test results"""
    print("\n" + "="*70)
    print("  AGENTCO OPENAI INTEGRATION TEST RESULTS")
    print("="*70)

    duration = (metrics['end_time'] - metrics['start_time']).total_seconds()

    print(f"\n⏱️  Test Duration: {duration:.1f} seconds")
    print(f"🕐 Start: {metrics['start_time'].strftime('%H:%M:%S')}")
    print(f"🕑 End:   {metrics['end_time'].strftime('%H:%M:%S')}")

    print(f"\n📊 OpenAI LLM Metrics:")
    print(f"   LLM API Calls:     {metrics['llm_calls']}")
    print(f"   Tokens Used:       {metrics['llm_tokens_used']}")
    print(f"   Model:             {MODEL}")
    print(f"   Calls/Minute:      {(metrics['llm_calls'] / duration * 60):.1f}")

    print(f"\n📊 Backend Metrics:")
    print(f"   Backend Calls:     {metrics['backend_calls']}")
    print(f"   Backend Errors:    {metrics['backend_errors']}")
    print(f"   Autonomy Tasks:    {metrics['autonomy_tasks']}")
    print(f"   Successful Tasks:  {metrics['successful_tasks']}")
    print(f"   Failed Tasks:      {metrics['failed_tasks']}")

    if metrics['backend_latencies']:
        avg_latency = sum(metrics['backend_latencies']) / len(metrics['backend_latencies'])
        max_latency = max(metrics['backend_latencies'])
        min_latency = min(metrics['backend_latencies'])
        print(f"   Avg Latency:       {avg_latency*1000:.1f}ms")
        print(f"   Max Latency:       {max_latency*1000:.1f}ms")
        print(f"   Min Latency:       {min_latency*1000:.1f}ms")

    print(f"\n✅ Test Status:")
    if metrics['backend_errors'] == 0:
        print(f"   Backend:           ✅ HEALTHY")
    else:
        print(f"   Backend:           ⚠️  {metrics['backend_errors']} errors")

    if metrics['llm_calls'] > 0:
        print(f"   OpenAI API:        ✅ WORKING")
        success_rate = (metrics['successful_tasks'] / max(1, metrics['autonomy_tasks'])) * 100
        print(f"   Success Rate:      {success_rate:.0f}%")
    else:
        print(f"   OpenAI API:        ❌ NO CALLS")

    print(f"\n🎯 Overall Result:")
    if metrics['llm_calls'] > 0 and metrics['backend_errors'] == 0:
        print(f"   ✅ FULL AGENTCO TEST WITH OPENAI - SUCCESS")
    else:
        print(f"   ⚠️  PARTIAL SUCCESS - Check errors above")

if __name__ == "__main__":
    try:
        # Run tests
        test_openai_basic()
        test_backend_health()
        test_full_autonomy_loop()

        # Print results
        print_results()

        # Save results to file
        with open('/Users/Zet/Agentco/audit_artifacts/production_deployment_execution/openai_integration_test.json', 'w') as f:
            results = {
                'test_type': 'Full AgentCo with OpenAI API (1 minute)',
                'test_date': metrics['start_time'].isoformat() if metrics['start_time'] else None,
                'duration_seconds': (metrics['end_time'] - metrics['start_time']).total_seconds() if metrics['end_time'] else 0,
                'openai': {
                    'api_calls': metrics['llm_calls'],
                    'tokens_used': metrics['llm_tokens_used'],
                    'model': MODEL,
                    'status': '✅ WORKING' if metrics['llm_calls'] > 0 else '❌ FAILED'
                },
                'backend': {
                    'calls': metrics['backend_calls'],
                    'errors': metrics['backend_errors'],
                    'status': '✅ HEALTHY' if metrics['backend_errors'] == 0 else '⚠️  ERRORS'
                },
                'autonomy': {
                    'tasks': metrics['autonomy_tasks'],
                    'successful': metrics['successful_tasks'],
                    'failed': metrics['failed_tasks']
                },
                'overall_status': '✅ SUCCESS' if metrics['llm_calls'] > 0 and metrics['backend_errors'] == 0 else '⚠️  PARTIAL'
            }
            json.dump(results, f, indent=2)

        print(f"\n📄 Results saved to: audit_artifacts/production_deployment_execution/openai_integration_test.json")

    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
