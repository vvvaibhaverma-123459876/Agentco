/**
 * Migration runner — applies all SQL files in backend/src/db/migrations/
 * in filename order to the database at DATABASE_URL.
 *
 * Usage:
 *   npm run db:migrate
 *   # or directly:
 *   npx ts-node src/db/migrate.ts
 */

import fs from 'fs';
import path from 'path';
import { Pool } from 'pg';

const DSN =
  process.env.DATABASE_URL ??
  'postgresql://agentco:password@localhost:5432/agentco';

// __dirname is dist/db/ when compiled, src/db/ when run via ts-node.
// Migrations always live next to the source file.
const MIGRATIONS_DIR = __dirname.endsWith('dist/db')
  ? path.join(__dirname, '../../src/db/migrations')
  : path.join(__dirname, 'migrations');

async function run(): Promise<void> {
  const pool = new Pool({ connectionString: DSN });

  // Ensure migration tracking table exists
  await pool.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      filename TEXT PRIMARY KEY,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  const files = fs
    .readdirSync(MIGRATIONS_DIR)
    .filter(f => f.endsWith('.sql'))
    .sort();

  for (const filename of files) {
    const { rowCount } = await pool.query(
      'SELECT 1 FROM schema_migrations WHERE filename = $1',
      [filename],
    );
    if (rowCount && rowCount > 0) {
      console.log(`[skip]  ${filename} (already applied)`);
      continue;
    }
    const sql = fs.readFileSync(path.join(MIGRATIONS_DIR, filename), 'utf8');
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      await client.query(sql);
      await client.query(
        'INSERT INTO schema_migrations (filename) VALUES ($1)',
        [filename],
      );
      await client.query('COMMIT');
      console.log(`[apply] ${filename}`);
    } catch (err: unknown) {
      await client.query('ROLLBACK');
      const msg = err instanceof Error ? err.message : String(err);
      // Treat "already exists" errors as idempotent — migration was applied
      // outside the tracker (e.g. manual psql run). Record it and continue.
      if (msg.includes('already exists')) {
        await pool.query(
          'INSERT INTO schema_migrations (filename) VALUES ($1) ON CONFLICT DO NOTHING',
          [filename],
        );
        console.log(`[idempotent] ${filename} (objects already exist; recorded)`);
      } else {
        console.error(`[error] ${filename}: ${msg}`);
        client.release();
        await pool.end();
        process.exit(1);
      }
    } finally {
      client.release();
    }
  }

  await pool.end();
  console.log('Migrations complete.');
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
