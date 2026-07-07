import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { eventLog } from '../src/services/event-log.service';
import { transactionalOutbox, OutboxEnvelope } from '../src/services/transactional-outbox.service';

async function applyMigrations() {
  for (const name of ['079_identity_authority.sql', '080_event_log.sql', '083_transactional_outbox.sql']) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function createActor(prefix: string) {
  return identityAuthorityService.registerActor({
    actor_type: 'service',
    name: `${prefix}-${Date.now()}-${Math.random()}`,
    service_identity: {
      service_name: `${prefix}-${Date.now()}-${Math.random()}`,
      scopes: ['events.publish'],
    },
  });
}

describe('transactional outbox', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  beforeEach(async () => {
    await db.query('TRUNCATE event_outbox, event_log RESTART IDENTITY CASCADE');
  });

  test('atomically enqueues an outbox row for every canonical event', async () => {
    const actor = await createActor('outbox-atomic-service');
    const event = await eventLog.append({
      event_type: 'resource.credited',
      actor_id: actor.id,
      object_type: 'resource_account',
      object_id: actor.id,
      payload: { amount: 7 },
    });

    const outbox = await db.query(
      `SELECT event_log_id, topic, envelope, status
         FROM event_outbox
        WHERE event_log_id = $1`,
      [event.id]
    );
    expect(outbox.rowCount).toBe(1);
    expect(outbox.rows[0].topic).toBe('agentco.resources');
    expect(outbox.rows[0].status).toBe('pending');
    expect(outbox.rows[0].envelope.event_hash).toBe(event.event_hash);
  });

  test('relay publishes pending rows and marks them published only after publisher success', async () => {
    const actor = await createActor('outbox-relay-service');
    const event = await eventLog.append({
      event_type: 'permission.granted',
      actor_id: actor.id,
      payload: { actor_id: actor.id, permission_name: 'test.permission' },
    });
    await db.query(`UPDATE event_outbox SET created_at = now() - interval '1 day' WHERE event_log_id = $1`, [event.id]);
    const published: Array<{ topic: string; envelope: OutboxEnvelope }> = [];

    const result = await transactionalOutbox.relayBatch({
      async publish(topic, envelope) {
        if (envelope.event_id === event.id) published.push({ topic, envelope });
      },
    }, { limit: 100, workerId: `test-worker-${Date.now()}` });

    expect(result.published).toBeGreaterThanOrEqual(1);
    expect(published.some(item => item.envelope.event_id === event.id)).toBe(true);
    const stored = await db.query(
      `SELECT status, published_at
         FROM event_outbox
        WHERE event_log_id = $1`,
      [event.id]
    );
    expect(stored.rows[0].status).toBe('published');
    expect(stored.rows[0].published_at).toBeTruthy();
  });

  test('relay records retryable failures without losing the outbox row', async () => {
    const actor = await createActor('outbox-failure-service');
    const event = await eventLog.append({
      event_type: 'actor.registered',
      actor_id: actor.id,
      payload: { actor_id: actor.id },
    });
    await db.query(`UPDATE event_outbox SET created_at = now() - interval '1 day' WHERE event_log_id = $1`, [event.id]);

    const result = await transactionalOutbox.relayBatch({
      async publish(_topic, envelope) {
        if (envelope.event_id === event.id) throw new Error('publisher unavailable');
      },
    }, { limit: 100, workerId: `failing-worker-${Date.now()}`, maxAttempts: 3 });

    expect(result.failed).toBeGreaterThanOrEqual(1);
    const stored = await db.query(
      `SELECT status, attempts, last_error
         FROM event_outbox
        WHERE event_log_id = $1`,
      [event.id]
    );
    expect(stored.rows[0].status).toBe('failed');
    expect(Number(stored.rows[0].attempts)).toBe(1);
    expect(stored.rows[0].last_error).toMatch(/publisher unavailable/);
  });

  test('relay dead-letters poison events at the configured attempt limit', async () => {
    const actor = await createActor('outbox-dead-letter-service');
    const event = await eventLog.append({
      event_type: 'test.poison',
      actor_id: actor.id,
      payload: { poison: true },
    });
    await db.query(`UPDATE event_outbox SET created_at = now() - interval '1 day' WHERE event_log_id = $1`, [event.id]);

    const result = await transactionalOutbox.relayBatch({
      async publish(_topic, envelope) {
        if (envelope.event_id === event.id) throw new Error('poison event');
      },
    }, { limit: 100, workerId: `dead-letter-worker-${Date.now()}`, maxAttempts: 1 });

    expect(result.dead_lettered).toBeGreaterThanOrEqual(1);
    const stored = await db.query(
      `SELECT o.status, d.error
         FROM event_outbox o
         JOIN event_dead_letters d ON d.outbox_id = o.id
        WHERE o.event_log_id = $1`,
      [event.id]
    );
    expect(stored.rows[0].status).toBe('dead_lettered');
    expect(stored.rows[0].error).toMatch(/poison event/);
  });
});
