import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { idempotencyStore } from '../src/services/idempotency-store.service';

async function applyMigrations() {
  for (const name of [
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '096_idempotency_store.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await migrationDb.query(migration);
  }
}

describe('idempotency store', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('begins a request once and replays the in-progress record for the same payload', async () => {
    const actor = await identityAuthorityService.registerActor({
      actor_type: 'human',
      name: `idempotency-actor-${Date.now()}`,
    });
    const scope = 'test.idempotency';
    const key = `begin-${Date.now()}`;
    const payload = { b: 2, a: { nested: true } };

    const first = await idempotencyStore.begin({ scope, idempotencyKey: key, actorId: actor.id, payload });
    const second = await idempotencyStore.begin({ scope, idempotencyKey: key, actorId: actor.id, payload: { a: { nested: true }, b: 2 } });

    expect(first.replay).toBe(false);
    expect(second.replay).toBe(false);
    expect(second.record.id).toBe(first.record.id);
    expect(second.record.started_event_log_id).toBe(first.record.started_event_log_id);
  });

  test('rejects reusing a key with a different request payload', async () => {
    const actor = await identityAuthorityService.registerActor({
      actor_type: 'human',
      name: `idempotency-conflict-${Date.now()}`,
    });
    const scope = 'test.idempotency';
    const key = `conflict-${Date.now()}`;

    await idempotencyStore.begin({ scope, idempotencyKey: key, actorId: actor.id, payload: { value: 1 } });

    await expect(
      idempotencyStore.begin({ scope, idempotencyKey: key, actorId: actor.id, payload: { value: 2 } })
    ).rejects.toThrow(/different request payload/);
  });

  test('completion stores the response and later begin returns a replay', async () => {
    const actor = await identityAuthorityService.registerActor({
      actor_type: 'human',
      name: `idempotency-complete-${Date.now()}`,
    });
    const scope = 'test.idempotency';
    const key = `complete-${Date.now()}`;
    const payload = { operation: 'create', amount: 42 };
    const response = { status: 'ok', resource_id: 'resource-123' };

    await idempotencyStore.begin({ scope, idempotencyKey: key, actorId: actor.id, payload });
    const completed = await idempotencyStore.complete(scope, key, actor.id, payload, response);
    const replay = await idempotencyStore.begin({ scope, idempotencyKey: key, actorId: actor.id, payload });

    expect(completed.status).toBe('completed');
    expect(completed.response_json).toEqual(response);
    expect(completed.completed_event_log_id).toBeTruthy();
    expect(replay.replay).toBe(true);
    expect(replay.record.response_json).toEqual(response);
  });
});
