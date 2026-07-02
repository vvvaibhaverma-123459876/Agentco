#!/usr/bin/env ts-node
/**
 * DB Table Usage Manifest
 * =======================
 * Generates docs/DB_TABLE_USAGE.md by cross-referencing:
 *   - tables declared in migrations (CREATE TABLE ...)
 *   - which service/test files reference each table name
 *   - live row counts from the connected database (if reachable)
 *
 * A table is "speculative" when no service references it and it has no rows.
 * This makes empty/unused schema visible instead of implying capability.
 *
 * Usage: DATABASE_URL=... ts-node src/cli/db-table-usage.ts
 */

import * as fs from 'fs';
import * as path from 'path';
import { pool } from '../db/client';

const backendRoot = path.resolve(__dirname, '..', '..');
const repoRoot = path.resolve(backendRoot, '..');
const migrationsDir = path.resolve(backendRoot, 'src/db/migrations');
const servicesDir = path.resolve(backendRoot, 'src/services');
const testsDir = path.resolve(backendRoot, 'tests');

function listFiles(dir: string, ext: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter(f => f.endsWith(ext))
    .map(f => path.join(dir, f));
}

function collectTables(): Map<string, string> {
  const tables = new Map<string, string>(); // table -> migration file
  for (const file of listFiles(migrationsDir, '.sql')) {
    const sql = fs.readFileSync(file, 'utf8');
    const regex = /CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([a-z_][a-z0-9_]*)/gi;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(sql))) {
      const name = match[1].toLowerCase();
      if (!tables.has(name)) tables.set(name, path.basename(file));
    }
  }
  return tables;
}

function referencesFor(table: string, files: string[]): string[] {
  const refs: string[] = [];
  const needle = new RegExp(`\\b${table}\\b`);
  for (const file of files) {
    const content = fs.readFileSync(file, 'utf8');
    if (needle.test(content)) refs.push(path.basename(file));
  }
  return refs;
}

async function rowCounts(): Promise<Map<string, number> | null> {
  try {
    const result = await pool.query<{ relname: string; n_live_tup: string }>(
      `SELECT relname, n_live_tup FROM pg_stat_user_tables`
    );
    const counts = new Map<string, number>();
    for (const row of result.rows) counts.set(row.relname, Number(row.n_live_tup));
    return counts;
  } catch {
    return null;
  }
}

async function main() {
  const tables = collectTables();
  const serviceFiles = listFiles(servicesDir, '.ts');
  const testFiles = listFiles(testsDir, '.ts');
  const counts = await rowCounts();

  const rows: Array<{
    table: string;
    migration: string;
    writers: string[];
    tests: string[];
    rows: number | null;
    classification: string;
  }> = [];

  for (const [table, migration] of [...tables.entries()].sort()) {
    const writers = referencesFor(table, serviceFiles);
    const tests = referencesFor(table, testFiles);
    const count = counts ? counts.get(table) ?? 0 : null;
    let classification: string;
    if (writers.length > 0) classification = 'runtime';
    else if (tests.length > 0) classification = 'test-only';
    else if (count && count > 0) classification = 'written-elsewhere';
    else classification = 'speculative';
    rows.push({ table, migration, writers, tests, rows: count, classification });
  }

  const speculative = rows.filter(r => r.classification === 'speculative').length;
  const runtime = rows.filter(r => r.classification === 'runtime').length;

  const md = [
    '# Database Table Usage',
    '',
    `Generated from migrations + service/test references${counts ? ' + live row counts' : ' (database not reachable; row counts omitted)'}.`,
    '',
    `- Total tables declared in migrations: ${rows.length}`,
    `- Referenced by a runtime service: ${runtime}`,
    `- Speculative (no service reference, no rows): ${speculative}`,
    '',
    'Classification:',
    '- **runtime** — a `backend/src/services` file references the table.',
    '- **test-only** — only tests reference it.',
    '- **written-elsewhere** — has rows but no service/test reference found (likely written by SQL functions/triggers or Python).',
    '- **speculative** — no reference and no rows; schema exists but capability is unproven.',
    '',
    '| Table | Migration | Runtime writers | Rows | Classification |',
    '|---|---|---|---|---|',
    ...rows.map(
      r =>
        `| ${r.table} | ${r.migration} | ${r.writers.length > 0 ? r.writers.slice(0, 3).join(', ') : '—'} | ${
          r.rows === null ? 'n/a' : r.rows
        } | ${r.classification} |`
    ),
    '',
  ].join('\n');

  const outPath = path.resolve(repoRoot, 'docs/DB_TABLE_USAGE.md');
  fs.writeFileSync(outPath, md);
  console.log(`[db-table-usage] ${rows.length} tables; ${runtime} runtime, ${speculative} speculative`);
  console.log(`[db-table-usage] written to ${outPath}`);
  await pool.end();
}

main().catch(error => {
  console.error(`[db-table-usage] failed: ${error}`);
  process.exitCode = 1;
});
