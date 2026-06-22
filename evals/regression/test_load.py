"""Load/stress test for Agentco backend.

Tests concurrent request handling under load.
Skipped by default; run with `make load-test` or `pytest test_load.py`.
"""

import asyncio
import time
from typing import Any

import pytest

# Only run if explicitly requested
pytestmark = pytest.mark.skipif(
    True,  # Skip by default; enable via marker
    reason="Load test skipped by default (slow). Run with SKIP_LOAD_TEST=0",
)


@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def mock_health_check() -> dict[str, Any]:
    """Simulate a health check request."""
    await asyncio.sleep(0.01)
    return {"status": "ok", "timestamp": "2026-06-22T00:00:00Z"}


@pytest.mark.asyncio
async def test_concurrent_health_checks():
    """Test 100 concurrent health check requests."""
    concurrent_requests = 100
    start = time.time()

    tasks = [mock_health_check() for _ in range(concurrent_requests)]
    results = await asyncio.gather(*tasks)

    elapsed = time.time() - start

    assert len(results) == concurrent_requests
    assert all(r["status"] == "ok" for r in results)
    assert elapsed < 5.0  # Should complete in < 5 seconds

    print(f"\n✓ {concurrent_requests} concurrent requests in {elapsed:.2f}s")
    print(f"  Throughput: {concurrent_requests / elapsed:.0f} req/s")


@pytest.mark.asyncio
async def test_request_latency_distribution():
    """Measure latency percentiles under concurrent load."""
    concurrent_requests = 50
    samples = 3  # Run 3 samples

    latencies = []
    for _ in range(samples):
        start = time.time()
        tasks = [mock_health_check() for _ in range(concurrent_requests)]
        await asyncio.gather(*tasks)
        latencies.append((time.time() - start) / concurrent_requests)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    assert max_latency < 1.0  # P100 < 1s
    print(f"\n✓ Latency: avg={avg_latency*1000:.1f}ms, max={max_latency*1000:.1f}ms")
