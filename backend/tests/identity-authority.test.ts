import fs from 'fs';
import path from 'path';
import { build } from '../src/server';
import { db } from '../src/db/client';

function authHeaders(): Record<string, string> {
  return process.env.AGENTCO_API_KEY ? { 'x-api-key': process.env.AGENTCO_API_KEY } : {};
}

async function applyIdentityMigration() {
  for (const name of ['079_identity_authority.sql', '080_event_log.sql']) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

describe('identity authority routes', () => {
  beforeAll(async () => {
    await applyIdentityMigration();
  });

  test('registers an agent actor and writes event plus audit records', async () => {
    const app = await build();
    const suffix = Date.now().toString();

    const response = await app.inject({
      method: 'POST',
      url: '/identity/actors',
      headers: authHeaders(),
      payload: {
        actor_type: 'agent',
        name: `identity-test-agent-${suffix}`,
        agent_identity: {
          agent_key: `identity-test-agent-${suffix}`,
          model_name: 'gpt-4o-mini',
          version: 'test',
          public_key_pem: 'test-public-key',
        },
      },
    });

    expect(response.statusCode).toBe(201);
    const actor = response.json().actor;
    expect(actor.actor_type).toBe('agent');

    const event = await db.query(
      `SELECT event_id
         FROM event_history
        WHERE event_type = 'actor.registered'
          AND producer_agent_id = $1
        ORDER BY created_at DESC
        LIMIT 1`,
      [actor.id]
    );
    expect(event.rowCount).toBe(1);

    const canonicalEvent = await db.query(
      `SELECT id, actor_id, event_hash, prev_hash
         FROM event_log
        WHERE id = $1
          AND event_type = 'actor.registered'
          AND actor_id = $2`,
      [event.rows[0].event_id, actor.id]
    );
    expect(canonicalEvent.rowCount).toBe(1);
    expect(canonicalEvent.rows[0].event_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(canonicalEvent.rows[0].prev_hash).toMatch(/^[0-9a-f]{64}$/);

    const audit = await db.query(
      `SELECT log_id
         FROM decision_log
        WHERE agent_id = $1
          AND action_type = 'event_published'
          AND downstream_events @> $2::uuid[]
        LIMIT 1`,
      [actor.id, [event.rows[0].event_id]]
    );
    expect(audit.rowCount).toBe(1);

    await app.close();
  });

  test('grants and verifies permission without allowing missing permissions', async () => {
    const app = await build();
    const suffix = Date.now().toString();

    const actorResponse = await app.inject({
      method: 'POST',
      url: '/identity/actors',
      headers: authHeaders(),
      payload: {
        actor_type: 'service',
        name: `identity-test-service-${suffix}`,
        service_identity: {
          service_name: `identity-test-service-${suffix}`,
          scopes: ['task.execute'],
        },
      },
    });
    expect(actorResponse.statusCode).toBe(201);
    const actorId = actorResponse.json().actor.id;

    const denied = await app.inject({
      method: 'POST',
      url: '/identity/verify',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        permission_name: 'task.execute',
      },
    });
    expect(denied.statusCode).toBe(403);
    expect(denied.json().allowed).toBe(false);

    const grant = await app.inject({
      method: 'POST',
      url: '/identity/permissions/grant',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        permission_name: 'task.execute',
        scope: '*',
      },
    });
    expect(grant.statusCode).toBe(201);
    expect(grant.json()).toHaveProperty('grant_id');

    const allowed = await app.inject({
      method: 'POST',
      url: '/identity/verify',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        permission_name: 'task.execute',
      },
    });
    expect(allowed.statusCode).toBe(200);
    expect(allowed.json().allowed).toBe(true);
    expect(allowed.json().reason).toBe('permission_granted');

    await app.close();
  });

  test('assigns canonical roles to active actors and records the role event', async () => {
    const app = await build();
    const suffix = Date.now().toString();

    const actorResponse = await app.inject({
      method: 'POST',
      url: '/identity/actors',
      headers: authHeaders(),
      payload: {
        actor_type: 'human',
        name: `identity-test-human-${suffix}`,
      },
    });
    expect(actorResponse.statusCode).toBe(201);
    const actorId = actorResponse.json().actor.id;

    const roleResponse = await app.inject({
      method: 'POST',
      url: '/identity/roles/assign',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        role_name: 'auditor',
      },
    });

    expect(roleResponse.statusCode).toBe(201);
    expect(roleResponse.json()).toHaveProperty('assignment_id');

    const event = await db.query(
      `SELECT event_id, payload
         FROM event_history
        WHERE event_type = 'role.assigned'
          AND payload->>'actor_id' = $1
          AND payload->>'role_name' = 'auditor'
        ORDER BY created_at DESC
        LIMIT 1`,
      [actorId]
    );
    expect(event.rowCount).toBe(1);
    expect(event.rows[0].payload.assignment_id).toBe(roleResponse.json().assignment_id);

    const canonicalEvent = await db.query(
      `SELECT id
         FROM event_log
        WHERE id = $1
          AND event_type = 'role.assigned'
          AND actor_id = $2`,
      [event.rows[0].event_id, actorId]
    );
    expect(canonicalEvent.rowCount).toBe(1);

    await app.close();
  });
});
