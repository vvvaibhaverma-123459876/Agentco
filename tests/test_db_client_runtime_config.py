from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_CLIENT = ROOT / "backend/src/db/client.ts"


def test_backend_db_client_has_bounded_pool_and_retry_contract():
    source = DB_CLIENT.read_text()

    assert "export const db: Pool = new Pool({" in source
    assert "max: Number(process.env.AGENTCO_PG_POOL_MAX) || 20" in source
    assert "idleTimeoutMillis: 10000" in source
    assert "connectionTimeoutMillis: 5000" in source
    assert "const QUERY_TIMEOUT_MS = 10000" in source
    assert "const MAX_RETRIES = 3" in source
    assert "Promise.race([queryPromise, timeoutPromise])" in source
    assert "metricsService.recordDbQuery" in source
    assert "export const pool = db" in source
