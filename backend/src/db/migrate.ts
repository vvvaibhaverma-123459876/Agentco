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
import crypto from 'crypto';
import { Pool } from 'pg';
import { appDatabaseUrl, resolutionServicePassword } from './dsn';

const DSN = appDatabaseUrl();

// __dirname is dist/db/ when compiled, src/db/ when run via ts-node.
// Migrations always live next to the source file.
const MIGRATIONS_DIR = __dirname.endsWith('dist/db')
  ? path.join(__dirname, '../../src/db/migrations')
  : path.join(__dirname, 'migrations');

function substituteEnvVars(sql: string): string {
  const token = "':RESOLUTION_SERVICE_PASSWORD'";
  if (!sql.includes(token)) return sql;
  // Shared policy (src/db/dsn.ts): dev default only outside production/staging.
  const password = resolutionServicePassword();
  return sql.replaceAll(token, `'${password.replaceAll("'", "''")}'`);
}

function migrationContentHash(sql: string): string {
  return crypto.createHash('sha256').update(sql).digest('hex');
}

function migrationSequence(filename: string): number | null {
  const match = filename.match(/^(\d+)_/);
  return match ? Number.parseInt(match[1], 10) : null;
}

async function run(): Promise<void> {
  const pool = new Pool({ connectionString: DSN });

  // Ensure migration tracking table exists
  await pool.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      filename TEXT PRIMARY KEY,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      content_hash TEXT,
      sequence_num INTEGER
    )
  `);
  await pool.query('ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS content_hash TEXT');
  await pool.query('ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS sequence_num INTEGER');

  const files = fs
    .readdirSync(MIGRATIONS_DIR)
    .filter(f => f.endsWith('.sql'))
    .sort();

  for (const filename of files) {
    const sql = substituteEnvVars(fs.readFileSync(path.join(MIGRATIONS_DIR, filename), 'utf8'));
    const contentHash = migrationContentHash(sql);
    const sequenceNum = migrationSequence(filename);
    const existing = await pool.query(
      'SELECT content_hash FROM schema_migrations WHERE filename = $1',
      [filename],
    );
    if (existing.rowCount && existing.rowCount > 0) {
      const recordedHash = existing.rows[0].content_hash;
      if (recordedHash && recordedHash !== contentHash) {
        console.error(`[error] ${filename}: content hash mismatch for already-applied migration`);
        await pool.end();
        process.exit(1);
      }
      if (!recordedHash) {
        await pool.query(
          'UPDATE schema_migrations SET content_hash = $1, sequence_num = $2 WHERE filename = $3 AND content_hash IS NULL',
          [contentHash, sequenceNum, filename],
        );
      }
      console.log(`[skip]  ${filename} (already applied)`);
      continue;
    }
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      await client.query(sql);
      await client.query(
        'INSERT INTO schema_migrations (filename, content_hash, sequence_num) VALUES ($1, $2, $3)',
        [filename, contentHash, sequenceNum],
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
          'INSERT INTO schema_migrations (filename, content_hash, sequence_num) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING',
          [filename, contentHash, sequenceNum],
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
