import { Pool } from 'pg';

const migrationDsn =
  process.env.RELEASE_GATE_MIGRATION_DATABASE_URL ||
  process.env.SUPERUSER_DATABASE_URL ||
  process.env.DATABASE_URL;

export const migrationDb = new Pool({
  connectionString: migrationDsn,
  max: 4,
  allowExitOnIdle: true,
  idleTimeoutMillis: 1000,
  connectionTimeoutMillis: 5000,
});
