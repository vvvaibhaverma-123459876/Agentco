import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { build } from '../src/server';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';

function authHeaders(): Record<string, string> {
  return process.env.AGENTCO_API_KEY ? { 'x-api-key': process.env.AGENTCO_API_KEY } : {};
}

async function applyIdentityMigration() {
  for (const name of ['079_identity_authority.sql', '080_event_log.sql', '083_transactional_outbox.sql', '084_authority_chain.sql', '085_authority_chain_decision_actor_compatibility.sql', '086_key_ring.sql']) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await migrationDb.query(migration);
  }
}

describe('identity authority routes', () => {
  let app: Awaited<ReturnType<typeof build>> | undefined;

  beforeAll(async () => {
    await applyIdentityMigration();
  });

  afterEach(async () => {
    if (app) {
      app = undefined;
    }
  });

  test('registers an agent actor and writes event plus audit records', async () => {
    app = await build();
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
  });

  test('grants and verifies permission without allowing missing permissions', async () => {
    app = await build();
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
    expect(allowed.json().reason).toBe('direct_permission_granted');
    expect(allowed.json().chain[0].source).toBe('direct_permission');
  });

  test('assigns canonical roles to active actors and records the role event', async () => {
    app = await build();
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
  });

  test('role assignments grant mapped permissions with persisted authority-chain provenance', async () => {
    app = await build();
    const suffix = Date.now().toString();

    const actorResponse = await app.inject({
      method: 'POST',
      url: '/identity/actors',
      headers: authHeaders(),
      payload: {
        actor_type: 'human',
        name: `identity-role-chain-human-${suffix}`,
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

    const allowed = await app.inject({
      method: 'POST',
      url: '/identity/verify',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        permission_name: 'audit.read',
      },
    });
    expect(allowed.statusCode).toBe(200);
    expect(allowed.json().reason).toBe('role_permission_granted');
    expect(allowed.json().chain[0]).toMatchObject({
      source: 'role_permission',
      role_name: 'auditor',
      permission_name: 'audit.read',
    });

    const persisted = await db.query(
      `SELECT id, allowed, reason, chain, event_log_id
         FROM authority_decision_chains
        WHERE id = $1`,
      [allowed.json().decision_chain_id]
    );
    expect(persisted.rowCount).toBe(1);
    expect(persisted.rows[0].allowed).toBe(true);
    expect(persisted.rows[0].chain[0].source).toBe('role_permission');
    expect(persisted.rows[0].event_log_id).toBe(allowed.json().event_log_id);
  });

  test('delegation grants permission through an explicit principal-to-delegate authority chain', async () => {
    app = await build();
    const suffix = Date.now().toString();

    const principalResponse = await app.inject({
      method: 'POST',
      url: '/identity/actors',
      headers: authHeaders(),
      payload: {
        actor_type: 'service',
        name: `identity-delegation-principal-${suffix}`,
        service_identity: {
          service_name: `identity-delegation-principal-${suffix}`,
          scopes: ['task.execute'],
        },
      },
    });
    const delegateResponse = await app.inject({
      method: 'POST',
      url: '/identity/actors',
      headers: authHeaders(),
      payload: {
        actor_type: 'service',
        name: `identity-delegation-delegate-${suffix}`,
        service_identity: {
          service_name: `identity-delegation-delegate-${suffix}`,
          scopes: ['task.execute'],
        },
      },
    });
    expect(principalResponse.statusCode).toBe(201);
    expect(delegateResponse.statusCode).toBe(201);
    const principalId = principalResponse.json().actor.id;
    const delegateId = delegateResponse.json().actor.id;

    const principalGrant = await app.inject({
      method: 'POST',
      url: '/identity/permissions/grant',
      headers: authHeaders(),
      payload: {
        actor_id: principalId,
        permission_name: 'task.execute',
        scope: '*',
      },
    });
    expect(principalGrant.statusCode).toBe(201);

    const delegation = await app.inject({
      method: 'POST',
      url: '/identity/delegations/grant',
      headers: authHeaders(),
      payload: {
        principal_actor_id: principalId,
        delegate_actor_id: delegateId,
        permission_name: 'task.execute',
        scope: '*',
      },
    });
    expect(delegation.statusCode).toBe(201);
    expect(delegation.json()).toHaveProperty('delegation_id');

    const allowed = await app.inject({
      method: 'POST',
      url: '/identity/verify',
      headers: authHeaders(),
      payload: {
        actor_id: delegateId,
        permission_name: 'task.execute',
      },
    });
    expect(allowed.statusCode).toBe(200);
    expect(allowed.json().reason).toBe('delegated_permission_granted');
    expect(allowed.json().chain[0]).toMatchObject({
      source: 'delegation',
      principal_actor_id: principalId,
      delegate_actor_id: delegateId,
      delegation_id: delegation.json().delegation_id,
    });
  });

  test('missing actor authority checks deny and persist provenance through authority service actor', async () => {
    app = await build();
    const missingActorId = '11111111-1111-4111-8111-111111111111';

    const denied = await app.inject({
      method: 'POST',
      url: '/identity/verify',
      headers: authHeaders(),
      payload: {
        actor_id: missingActorId,
        permission_name: 'task.execute',
      },
    });
    expect(denied.statusCode).toBe(403);
    expect(denied.json().allowed).toBe(false);
    expect(denied.json().reason).toBe('actor_not_found');
    expect(denied.json()).toHaveProperty('decision_chain_id');
    expect(denied.json()).toHaveProperty('event_log_id');

    const persisted = await db.query(
      `SELECT actor_id, requested_actor_id, allowed, reason, event_log_id
         FROM authority_decision_chains
        WHERE id = $1`,
      [denied.json().decision_chain_id]
    );
    expect(persisted.rowCount).toBe(1);
    expect(persisted.rows[0].actor_id).toBeNull();
    expect(persisted.rows[0].requested_actor_id).toBe(missingActorId);
    expect(persisted.rows[0].allowed).toBe(false);

    const event = await db.query(
      `SELECT e.actor_id, a.name
         FROM event_log e
         JOIN actors a ON a.id = e.actor_id
        WHERE e.id = $1`,
      [denied.json().event_log_id]
    );
    expect(event.rowCount).toBe(1);
    expect(event.rows[0].name).toBe('agentco-authority-service');
  });

  test('registers public Ed25519 keys and verifies signatures without storing private material', async () => {
    app = await build();
    const suffix = Date.now().toString();
    const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');
    const publicKeyPem = publicKey.export({ type: 'spki', format: 'pem' }).toString();
    const privateKeyPem = privateKey.export({ type: 'pkcs8', format: 'pem' }).toString();
    const payload = JSON.stringify({ actor: 'key-ring', nonce: suffix });
    const signature = crypto.sign(null, Buffer.from(payload, 'utf8'), privateKey).toString('base64');

    const actorResponse = await app.inject({
      method: 'POST',
      url: '/identity/actors',
      headers: authHeaders(),
      payload: {
        actor_type: 'service',
        name: `identity-key-service-${suffix}`,
        service_identity: {
          service_name: `identity-key-service-${suffix}`,
          scopes: ['identity.keys'],
        },
      },
    });
    expect(actorResponse.statusCode).toBe(201);
    const actorId = actorResponse.json().actor.id;

    const privateRejected = await app.inject({
      method: 'POST',
      url: '/identity/keys',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        key_purpose: 'identity',
        public_key_pem: privateKeyPem,
      },
    });
    expect(privateRejected.statusCode).toBe(400);
    expect(privateRejected.json().error).toMatch(/private key material is not accepted|Ed25519 public key/);

    const registered = await app.inject({
      method: 'POST',
      url: '/identity/keys',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        key_purpose: 'identity',
        public_key_pem: publicKeyPem,
      },
    });
    expect(registered.statusCode).toBe(201);
    expect(registered.json().key.fingerprint_sha256).toMatch(/^[0-9a-f]{64}$/);
    expect(registered.json().key.public_key_pem).toContain('PUBLIC KEY');
    expect(registered.body).not.toContain('PRIVATE KEY');

    const valid = await app.inject({
      method: 'POST',
      url: '/identity/keys/verify-signature',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        key_purpose: 'identity',
        payload,
        signature_base64: signature,
      },
    });
    expect(valid.statusCode).toBe(200);
    expect(valid.json()).toMatchObject({
      valid: true,
      reason: 'signature_valid',
      key_id: registered.json().key.id,
    });

    const tampered = await app.inject({
      method: 'POST',
      url: '/identity/keys/verify-signature',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        key_purpose: 'identity',
        payload: `${payload}tampered`,
        signature_base64: signature,
      },
    });
    expect(tampered.statusCode).toBe(403);
    expect(tampered.json().reason).toBe('signature_invalid');

    const event = await db.query(
      `SELECT id
         FROM event_log
        WHERE event_type = 'identity.key_registered'
          AND payload->>'fingerprint_sha256' = $1`,
      [registered.json().key.fingerprint_sha256]
    );
    expect(event.rowCount).toBe(1);
  });

  test('rotates active keys and revokes key verification capability', async () => {
    app = await build();
    const suffix = Date.now().toString();
    const first = crypto.generateKeyPairSync('ed25519');
    const second = crypto.generateKeyPairSync('ed25519');
    const firstPublicPem = first.publicKey.export({ type: 'spki', format: 'pem' }).toString();
    const secondPublicPem = second.publicKey.export({ type: 'spki', format: 'pem' }).toString();
    const payload = `rotation-${suffix}`;
    const firstSignature = crypto.sign(null, Buffer.from(payload, 'utf8'), first.privateKey).toString('base64');
    const secondSignature = crypto.sign(null, Buffer.from(payload, 'utf8'), second.privateKey).toString('base64');

    const actorResponse = await app.inject({
      method: 'POST',
      url: '/identity/actors',
      headers: authHeaders(),
      payload: {
        actor_type: 'service',
        name: `identity-key-rotation-service-${suffix}`,
        service_identity: {
          service_name: `identity-key-rotation-service-${suffix}`,
          scopes: ['identity.keys'],
        },
      },
    });
    expect(actorResponse.statusCode).toBe(201);
    const actorId = actorResponse.json().actor.id;

    const firstRegistered = await app.inject({
      method: 'POST',
      url: '/identity/keys',
      headers: authHeaders(),
      payload: { actor_id: actorId, key_purpose: 'event_signing', public_key_pem: firstPublicPem },
    });
    expect(firstRegistered.statusCode).toBe(201);

    const rotated = await app.inject({
      method: 'POST',
      url: '/identity/keys',
      headers: authHeaders(),
      payload: { actor_id: actorId, key_purpose: 'event_signing', public_key_pem: secondPublicPem },
    });
    expect(rotated.statusCode).toBe(201);

    const oldKey = await db.query(
      `SELECT status, replaced_by_key_id
         FROM actor_key_ring
        WHERE id = $1`,
      [firstRegistered.json().key.id]
    );
    expect(oldKey.rows[0].status).toBe('rotated');
    expect(oldKey.rows[0].replaced_by_key_id).toBe(rotated.json().key.id);

    const oldSignature = await app.inject({
      method: 'POST',
      url: '/identity/keys/verify-signature',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        key_purpose: 'event_signing',
        payload,
        signature_base64: firstSignature,
      },
    });
    expect(oldSignature.statusCode).toBe(403);
    expect(oldSignature.json().reason).toBe('signature_invalid');

    const newSignature = await app.inject({
      method: 'POST',
      url: '/identity/keys/verify-signature',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        key_purpose: 'event_signing',
        payload,
        signature_base64: secondSignature,
      },
    });
    expect(newSignature.statusCode).toBe(200);

    const revoked = await app.inject({
      method: 'POST',
      url: `/identity/keys/${rotated.json().key.id}/revoke`,
      headers: authHeaders(),
      payload: { revoked_by: actorId },
    });
    expect(revoked.statusCode).toBe(200);
    expect(revoked.json().key.status).toBe('revoked');

    const afterRevoke = await app.inject({
      method: 'POST',
      url: '/identity/keys/verify-signature',
      headers: authHeaders(),
      payload: {
        actor_id: actorId,
        key_purpose: 'event_signing',
        payload,
        signature_base64: secondSignature,
      },
    });
    expect(afterRevoke.statusCode).toBe(403);
    expect(afterRevoke.json().reason).toBe('active_key_missing');
  });
});
