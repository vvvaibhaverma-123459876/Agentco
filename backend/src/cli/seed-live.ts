/**
 * Live-deployment bootstrap seed.
 *
 * Production boot (security.ts assertProductionSecrets) refuses to start when LLM
 * credentials are configured unless LLM_RESOURCE_ACTOR_ID and LLM_RESOURCE_ACCOUNT_ID
 * reference a real actor and llm_tokens resource account — but nothing in the repo
 * created them. This CLI closes that gap idempotently:
 *
 *   1. ensures the civilization root exists,
 *   2. ensures a `service` actor named by LLM_SEED_ACTOR_NAME (default
 *      "agentco-llm-budget-authority") exists — looked up by name, registered via
 *      identityAuthorityService (real event/audit trail) only when absent,
 *   3. ensures that actor's llm_tokens resource account exists (createAccount is
 *      ON CONFLICT idempotent),
 *   4. funds the account with LLM_SEED_BUDGET_TOKENS (default 5,000,000) exactly once,
 *      enforced by the ledger's UNIQUE idempotency_key.
 *
 * With --emit-env the ONLY stdout output is `export LLM_RESOURCE_ACTOR_ID=...` /
 * `export LLM_RESOURCE_ACCOUNT_ID=...` lines (all logging goes to stderr), so a
 * container entrypoint can `eval "$(node dist/cli/seed-live.js --emit-env)"` before
 * exec-ing the server.
 */
import { db } from '../db/client';
import { civilizationKernel } from '../services/civilization-kernel.service';
import { identityAuthorityService } from '../services/identity-authority.service';
import { resourceLedger } from '../services/resource-ledger.service';
import { shutdownRuntimeResources } from '../runtime/shutdown';

const SEED_ACTOR_NAME = process.env.LLM_SEED_ACTOR_NAME || 'agentco-llm-budget-authority';
const SEED_BUDGET_TOKENS = Math.max(1, Number(process.env.LLM_SEED_BUDGET_TOKENS || 5_000_000));
const FUND_IDEMPOTENCY_KEY = 'live-seed:initial-llm-budget';

function logStderr(message: string): void {
  process.stderr.write(`[seed-live] ${message}\n`);
}

async function ensureSeedActor(): Promise<string> {
  const existing = await db.query<{ id: string }>(
    `SELECT id FROM actors WHERE name = $1 AND actor_type = 'service' ORDER BY created_at ASC LIMIT 1`,
    [SEED_ACTOR_NAME]
  );
  if (existing.rowCount) {
    logStderr(`actor "${SEED_ACTOR_NAME}" already exists: ${existing.rows[0].id}`);
    return existing.rows[0].id;
  }
  const actor = await identityAuthorityService.registerActor({
    actor_type: 'service',
    name: SEED_ACTOR_NAME,
    metadata: { purpose: 'llm budget enforcement principal for live deployment', seeded_by: 'seed-live' },
    service_identity: { service_name: SEED_ACTOR_NAME, scopes: ['llm:budget'] },
  });
  logStderr(`registered actor "${SEED_ACTOR_NAME}": ${actor.id}`);
  return actor.id;
}

async function ensureLlmAccount(actorId: string): Promise<string> {
  const account = await resourceLedger.createAccount({
    owner_actor_id: actorId,
    resource_type: 'llm_tokens',
    unit: 'tokens',
    metadata: { seeded_by: 'seed-live' },
  });
  logStderr(`llm_tokens account for ${actorId}: ${account.id} (balance=${account.balance})`);
  return account.id;
}

async function ensureInitialFunding(accountId: string, actorId: string): Promise<void> {
  const funded = await db.query(
    `SELECT 1 FROM civilization_resource_transactions WHERE idempotency_key = $1`,
    [FUND_IDEMPOTENCY_KEY]
  );
  if (funded.rowCount) {
    logStderr('initial funding already applied; skipping');
    return;
  }
  await resourceLedger.credit({
    account_id: accountId,
    actor_id: actorId,
    amount: SEED_BUDGET_TOKENS,
    reason: 'live-seed initial llm_tokens budget',
    idempotency_key: FUND_IDEMPOTENCY_KEY,
  });
  logStderr(`funded account ${accountId} with ${SEED_BUDGET_TOKENS} llm_tokens`);
}

async function main(): Promise<void> {
  const emitEnv = process.argv.includes('--emit-env');

  const root = await civilizationKernel.ensureCivilizationRoot();
  logStderr(`civilization root: ${root.id}`);

  const actorId = await ensureSeedActor();
  const accountId = await ensureLlmAccount(actorId);
  await ensureInitialFunding(accountId, actorId);

  if (emitEnv) {
    process.stdout.write(`export LLM_RESOURCE_ACTOR_ID=${actorId}\n`);
    process.stdout.write(`export LLM_RESOURCE_ACCOUNT_ID=${accountId}\n`);
  } else {
    logStderr(`LLM_RESOURCE_ACTOR_ID=${actorId}`);
    logStderr(`LLM_RESOURCE_ACCOUNT_ID=${accountId}`);
  }
}

if (require.main === module) {
  main()
    .then(() => shutdownRuntimeResources({ closeDb: true }))
    .then(() => process.exit(0))
    .catch(error => {
      logStderr(`fatal: ${error instanceof Error ? error.stack || error.message : String(error)}`);
      process.exit(1);
    });
}
