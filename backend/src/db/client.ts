/**
 * PostgreSQL connection pool — singleton used by all backend services.
 * Points at the same DB as the Python calibration layer.
 * Includes retry logic, exponential backoff, and query timeouts.
 */
import { Pool, PoolClient } from 'pg';
import { metricsService } from '../services/metrics.service';

const DSN = process.env.DATABASE_URL ??
  'postgresql://agentco:password@localhost:5433/agentco?host=/tmp';

const QUERY_TIMEOUT_MS = 10000; // 10 second timeout per query
const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY_MS = 100;

export const db: Pool = new Pool({
  connectionString: DSN,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

db.on('error', (err) => {
  console.error('Unexpected error on idle client', err);
});

async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function isRetryableError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  const msg = err.message.toLowerCase();
  return msg.includes('timeout') ||
         msg.includes('connection') ||
         msg.includes('ECONNREFUSED') ||
         (err as any).code === 'ECONNREFUSED' ||
         (err as any).code === 'ETIMEDOUT';
}

/** Convenience: run a single parameterised query with retry logic */
export async function query<T = Record<string, unknown>>(
  sql: string, params: unknown[] = []
): Promise<T[]> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const startTime = Date.now();
      const queryPromise = (async () => {
        const result = await db.query(sql, params);
        return result.rows as T[];
      })();

      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Query timeout')), QUERY_TIMEOUT_MS)
      );

      const result = await Promise.race([queryPromise, timeoutPromise]);
      const duration = (Date.now() - startTime) / 1000;
      metricsService.recordDbQuery(sql, duration, false);
      return result;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));
      metricsService.recordDbQuery(sql, 0, true);

      if (attempt < MAX_RETRIES && isRetryableError(err)) {
        const delay = INITIAL_RETRY_DELAY_MS * Math.pow(2, attempt);
        console.warn(`Query attempt ${attempt + 1} failed, retrying in ${delay}ms:`, lastError.message);
        await sleep(delay);
      } else {
        break;
      }
    }
  }

  throw lastError || new Error('Query failed after retries');
}

/** Convenience: execute inside an acquired client (callers must release) */
export async function withClient<T>(fn: (client: PoolClient) => Promise<T>): Promise<T> {
  const client = await db.connect();
  try {
    return await fn(client);
  } finally {
    client.release();
  }
}
