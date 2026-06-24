/**
 * PostgreSQL connection pool — singleton used by all backend services.
 * Points at the same DB as the Python calibration layer.
 */
import { Pool, PoolClient } from 'pg';

const DSN = process.env.DATABASE_URL ??
  'postgresql://agentco:password@localhost:5432/agentco';

export const db: Pool = new Pool({ connectionString: DSN });
export const pool: Pool = db; // Alias for backward compatibility

/** Convenience: run a single parameterised query */
export async function query<T = Record<string, unknown>>(
  sql: string, params: unknown[] = []
): Promise<T[]> {
  const { rows } = await db.query(sql, params);
  return rows as T[];
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
