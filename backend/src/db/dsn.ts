/**
 * Single source of truth for database connection strings (G1).
 * =============================================================
 * The split-brain bug: `db/client.ts` resolved DATABASE_URL first while the
 * autonomy run path resolved AGENTCO_TEST_DATABASE_URL first, so with both
 * set (the documented `.codex.env` setup) predictions were written to one
 * database and resolved against another.
 *
 * Precedence — one order, used by every runtime module and test helper:
 *   1. DATABASE_URL
 *   2. AGENTCO_TEST_DATABASE_URL   (test harnesses; jest setup copies it into
 *                                   DATABASE_URL so both always agree in-process)
 *   3. postgresql://agentco:password@localhost:5432/agentco (local dev only)
 *
 * The resolution_service DSN is DERIVED from the same base URL (username and
 * password swapped), so the prediction writer and the resolution firewall can
 * never disagree about which database they are talking to. An explicit
 * RESOLUTION_SERVICE_DATABASE_URL still overrides for split-infrastructure
 * deployments.
 *
 * No other module may read DATABASE_URL / AGENTCO_TEST_DATABASE_URL /
 * RESOLUTION_SERVICE_PASSWORD directly; `tests/dsn-routing.test.ts` enforces
 * this by scanning the source tree.
 */

const LOCAL_DEV_DSN = 'postgresql://agentco:password@localhost:5432/agentco';
const DEV_RESOLUTION_PASSWORD = 'resolution-service-dev-password';

export function appDatabaseUrl(): string {
  return (
    process.env.DATABASE_URL ??
    process.env.AGENTCO_TEST_DATABASE_URL ??
    LOCAL_DEV_DSN
  );
}

/**
 * Password for the resolution_service DB role. Fails closed in production:
 * the dev default exists only for local/test databases, matching the policy
 * migrate.ts applies when provisioning the role (G11/E5).
 */
export function resolutionServicePassword(): string {
  const configured = process.env.RESOLUTION_SERVICE_PASSWORD;
  if (configured) return configured;
  if (process.env.AGENTCO_ENV === 'production' || process.env.AGENTCO_ENV === 'staging') {
    throw new Error(
      'RESOLUTION_SERVICE_PASSWORD must be set when AGENTCO_ENV is production/staging'
    );
  }
  return DEV_RESOLUTION_PASSWORD;
}

/**
 * DSN for the resolution_service firewall role. Always the same database as
 * appDatabaseUrl() unless explicitly overridden.
 */
export function resolutionServiceDatabaseUrl(): string {
  const explicit = process.env.RESOLUTION_SERVICE_DATABASE_URL;
  if (explicit) return explicit;
  const base = new URL(appDatabaseUrl());
  base.username = 'resolution_service';
  base.password = resolutionServicePassword();
  return base.toString();
}
