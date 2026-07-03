import fs from 'fs';
import path from 'path';

function loadEnvFile(filePath: string): void {
  if (!fs.existsSync(filePath)) return;
  for (const raw of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
    let line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    if (line.startsWith('export ')) line = line.slice(7).trim();
    const [key, ...rest] = line.split('=');
    if (!key || process.env[key]) continue;
    process.env[key] = rest.join('=').trim().replace(/^['"]|['"]$/g, '');
  }
}

const root = path.resolve(__dirname, '..', '..');
loadEnvFile(path.join(root, '.codex.env'));
loadEnvFile(path.join(root, 'codex.env'));

process.env.DATABASE_URL ??= 'postgresql://agentco:password@localhost:5432/agentco';
process.env.AGENTCO_TEST_DATABASE_URL ??= process.env.DATABASE_URL;
process.env.SUPERUSER_DATABASE_URL ??= process.env.DATABASE_URL;

// Cap the shared DB pool in tests: the full serial suite runs many files
// against one Postgres (max_connections default 100) plus per-suite service
// pools. A smaller shared pool leaves headroom and avoids "too many clients".
process.env.AGENTCO_PG_POOL_MAX ??= '6';
