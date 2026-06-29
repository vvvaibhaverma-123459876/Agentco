import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { eventLog } from '../src/services/event-log.service';

async function applyMigrations() {
  for (const name of ['079_identity_authority.sql', '080_event_log.sql', '083_transactional_outbox.sql']) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

describe('canonical event log', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('appends hash-chained events for active actors and verifies integrity', async () => {
    const suffix = Date.now().toString();
    const actor = await identityAuthorityService.registerActor({
      actor_type: 'human',
      name: `event-log-test-actor-${suffix}`,
    });

    const first = await eventLog.append({
      event_type: 'test.first',
      actor_id: actor.id,
      object_type: 'test',
      payload: { ordinal: 1, nested: { b: 2, a: 1 } },
    });
    const second = await eventLog.append({
      event_type: 'test.second',
      actor_id: actor.id,
      object_type: 'test',
      payload: { ordinal: 2 },
      causation_id: first.id,
    });

    expect(first.event_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(second.prev_hash).toBe(first.event_hash);
    await expect(eventLog.verifyChainIntegrity()).resolves.toEqual({ valid: true });
  });

  test('rejects events from inactive or missing actors', async () => {
    await expect(
      eventLog.append({
        event_type: 'test.rejected',
        actor_id: '11111111-1111-4111-8111-111111111111',
        payload: { ok: false },
      })
    ).rejects.toThrow(/actor is not active/);
  });
});
