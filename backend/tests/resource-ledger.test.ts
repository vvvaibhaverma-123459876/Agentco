import fs from 'fs';
import path from 'path';
import { build } from '../src/server';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { resourceLedger } from '../src/services/resource-ledger.service';
import { provisionSignedActor, signHeaders } from './helpers/sign-request';

function authHeaders(): Record<string, string> {
  return process.env.AGENTCO_API_KEY ? { 'x-api-key': process.env.AGENTCO_API_KEY } : {};
}

// AUD-004: these routes now require a signed, credential-bound principal.
function signedHeaders(actor: { actorId: string; privateKey: import('crypto').KeyObject }, method: string, url: string, body?: unknown) {
  return { ...authHeaders(), ...signHeaders({ actorId: actor.actorId, privateKey: actor.privateKey, method, url, body }) };
}

async function applyMigrations() {
  for (const name of ['079_identity_authority.sql', '080_event_log.sql', '081_resource_ledger.sql', '082_resource_reservations.sql', '083_transactional_outbox.sql']) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await migrationDb.query(migration);
  }
}

async function createActor(prefix: string) {
  return identityAuthorityService.registerActor({
    actor_type: 'service',
    name: `${prefix}-${Date.now()}-${Math.random()}`,
    service_identity: {
      service_name: `${prefix}-${Date.now()}-${Math.random()}`,
      scopes: ['resource.ledger'],
    },
  });
}

describe('resource ledger', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('creates accounts and records credit/debit transactions with event and audit rows', async () => {
    const actor = await createActor('resource-ledger-service');
    const account = await resourceLedger.createAccount({
      owner_actor_id: actor.id,
      resource_type: 'llm_tokens',
      unit: 'tokens',
    });

    const credit = await resourceLedger.credit({
      account_id: account.id,
      actor_id: actor.id,
      amount: 1000,
      reason: 'initial allocation',
      idempotency_key: `credit-${account.id}`,
    });
    expect(Number(credit.balance_after)).toBe(1000);

    const duplicateCredit = await resourceLedger.credit({
      account_id: account.id,
      actor_id: actor.id,
      amount: 1000,
      reason: 'initial allocation',
      idempotency_key: `credit-${account.id}`,
    });
    expect(duplicateCredit.id).toBe(credit.id);

    const debit = await resourceLedger.debit({
      account_id: account.id,
      actor_id: actor.id,
      amount: 250,
      reason: 'llm task execution',
      idempotency_key: `debit-${account.id}`,
    });
    expect(Number(debit.balance_after)).toBe(750);

    const stored = await resourceLedger.getAccount(account.id);
    expect(Number(stored?.balance)).toBe(750);

    const event = await db.query(
      `SELECT id
         FROM event_log
        WHERE id = $1
          AND event_type = 'resource.spent'
          AND actor_id = $2`,
      [debit.event_log_id, actor.id]
    );
    expect(event.rowCount).toBe(1);

    const audit = await db.query(
      `SELECT log_id
         FROM decision_log
        WHERE downstream_events @> $1::uuid[]
          AND agent_id = $2`,
      [[debit.event_log_id], actor.id]
    );
    expect(audit.rowCount).toBe(1);
  });

  test('rejects debits that would overdraw the account', async () => {
    const actor = await createActor('resource-overdraft-service');
    const account = await resourceLedger.createAccount({
      owner_actor_id: actor.id,
      resource_type: 'tool_calls',
      unit: 'calls',
    });

    await expect(
      resourceLedger.debit({
        account_id: account.id,
        actor_id: actor.id,
        amount: 1,
        reason: 'unfunded execution',
        idempotency_key: `overdraft-${account.id}`,
      })
    ).rejects.toThrow(/insufficient tool_calls balance/);
  });

  test('resource ledger routes are reachable and backed by the same ledger', async () => {
    const app = await build();
    const actor = await provisionSignedActor({ name: `resource-route-service-${Date.now()}`, roles: ['civilization_operator'] });

    const createUrl = '/resources/accounts';
    const createBody = { resource_type: 'compute', unit: 'credits' };
    const create = await app.inject({
      method: 'POST',
      url: createUrl,
      headers: signedHeaders(actor, 'POST', createUrl, createBody),
      payload: createBody,
    });
    expect(create.statusCode).toBe(201);
    const accountId = create.json().account.id;

    const creditUrl = '/resources/transactions/credit';
    const creditBody = { account_id: accountId, amount: 3, reason: 'route allocation', idempotency_key: `route-credit-${accountId}` };
    const credit = await app.inject({
      method: 'POST',
      url: creditUrl,
      headers: signedHeaders(actor, 'POST', creditUrl, creditBody),
      payload: creditBody,
    });
    expect(credit.statusCode).toBe(201);

    const read = await app.inject({
      method: 'GET',
      url: `/resources/accounts/${accountId}`,
    });
    expect(read.statusCode).toBe(200);
    expect(Number(read.json().account.balance)).toBe(3);

    await app.close();
  });

  test('reserves, settles, and releases balances without leaking holds', async () => {
    const actor = await createActor('resource-reservation-service');
    const account = await resourceLedger.createAccount({
      owner_actor_id: actor.id,
      resource_type: 'llm_tokens',
      unit: 'tokens',
    });
    await resourceLedger.credit({
      account_id: account.id,
      actor_id: actor.id,
      amount: 500,
      reason: 'reservation funding',
      idempotency_key: `reservation-credit-${account.id}`,
    });

    const reservation = await resourceLedger.reserve({
      account_id: account.id,
      actor_id: actor.id,
      amount: 200,
      reason: 'planned LLM call',
      idempotency_key: `reservation-${account.id}`,
      expires_at: new Date(Date.now() + 60_000).toISOString(),
    });
    expect(reservation.status).toBe('reserved');

    const afterReserve = await resourceLedger.getAccount(account.id);
    expect(Number(afterReserve?.balance)).toBe(500);
    expect(Number(afterReserve?.reserved_balance)).toBe(200);

    await expect(
      resourceLedger.debit({
        account_id: account.id,
        actor_id: actor.id,
        amount: 350,
        reason: 'would consume reserved tokens',
        idempotency_key: `blocked-debit-${account.id}`,
      })
    ).rejects.toThrow(/insufficient llm_tokens balance/);

    const settled = await resourceLedger.settleReservation(
      reservation.id,
      actor.id,
      `settle-${reservation.id}`,
    );
    expect(Number(settled.balance_after)).toBe(300);

    const settledAgain = await resourceLedger.settleReservation(
      reservation.id,
      actor.id,
      `settle-${reservation.id}`,
    );
    expect(settledAgain.id).toBe(settled.id);

    const afterSettle = await resourceLedger.getAccount(account.id);
    expect(Number(afterSettle?.balance)).toBe(300);
    expect(Number(afterSettle?.reserved_balance)).toBe(0);

    const partialReservation = await resourceLedger.reserve({
      account_id: account.id,
      actor_id: actor.id,
      amount: 100,
      reason: 'partial LLM call',
      idempotency_key: `partial-reservation-${account.id}`,
      expires_at: new Date(Date.now() + 60_000).toISOString(),
    });
    const partialSettled = await resourceLedger.settleReservationUsage(
      partialReservation.id,
      actor.id,
      `partial-settle-${partialReservation.id}`,
      25,
    );
    expect(Number(partialSettled.amount)).toBe(25);
    const afterPartialSettle = await resourceLedger.getAccount(account.id);
    expect(Number(afterPartialSettle?.balance)).toBe(275);
    expect(Number(afterPartialSettle?.reserved_balance)).toBe(0);

    const releaseReservation = await resourceLedger.reserve({
      account_id: account.id,
      actor_id: actor.id,
      amount: 100,
      reason: 'release test',
      idempotency_key: `release-reservation-${account.id}`,
      expires_at: new Date(Date.now() + 60_000).toISOString(),
    });
    await resourceLedger.releaseReservation(releaseReservation.id, actor.id);
    const afterRelease = await resourceLedger.getAccount(account.id);
    expect(Number(afterRelease?.balance)).toBe(275);
    expect(Number(afterRelease?.reserved_balance)).toBe(0);
  });

  test('reservation routes are reachable and expired holds are released', async () => {
    const app = await build();
    const signer = await provisionSignedActor({ name: `resource-reservation-route-service-${Date.now()}`, roles: ['civilization_operator'] });
    const account = await resourceLedger.createAccount({
      owner_actor_id: signer.actorId,
      resource_type: 'tool_calls',
      unit: 'calls',
    });
    await resourceLedger.credit({
      account_id: account.id,
      actor_id: signer.actorId,
      amount: 5,
      reason: 'route reservation funding',
      idempotency_key: `route-reservation-credit-${account.id}`,
    });

    const reserveUrl = '/resources/reservations';
    const reserveBody = {
      account_id: account.id, amount: 2, reason: 'route reserve',
      idempotency_key: `route-reservation-${account.id}`, expires_at: new Date(Date.now() + 60_000).toISOString(),
    };
    const reserve = await app.inject({
      method: 'POST',
      url: reserveUrl,
      headers: signedHeaders(signer, 'POST', reserveUrl, reserveBody),
      payload: reserveBody,
    });
    expect(reserve.statusCode).toBe(201);

    const releaseUrl = `/resources/reservations/${reserve.json().reservation.id}/release`;
    const release = await app.inject({
      method: 'POST',
      url: releaseUrl,
      headers: signedHeaders(signer, 'POST', releaseUrl, {}),
      payload: {},
    });
    expect(release.statusCode).toBe(200);
    expect(release.json().reservation.status).toBe('released');

    await app.close();
  });
});
