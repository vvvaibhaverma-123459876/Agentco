/**
 * AUD-004 M2 — HTTP boundary wiring (DB-backed integration).
 * A governed route declaring `requirePrincipal()` must reject unsigned/forged/stale/replayed
 * requests and resolve the principal from the SIGNING actor — never from body.actor_id.
 */
import Fastify, { FastifyInstance } from 'fastify';
import crypto from 'crypto';
import { registerPrincipalResolution, requirePrincipal } from '../src/auth/principal-context';
import { ReplayGuard } from '../src/auth/request-principal';
import { dbIdentityLookup } from '../src/auth/identity-lookup';
import { provisionSignedActor, signedInject, signHeaders } from './helpers/sign-request';

async function buildApp(): Promise<FastifyInstance> {
  const app = Fastify();
  registerPrincipalResolution(app, { lookup: dbIdentityLookup, replay: new ReplayGuard() });
  app.post('/test/governed', { config: requirePrincipal() }, async (req) => ({
    principalActor: req.principal?.actorId,
    roles: req.principal?.roles,
  }));
  // M3: route requiring an explicit credential-bound permission (RBAC over the authenticated principal)
  app.post('/test/treasury-penalty', { config: requirePrincipal('treasury.penalty.impose') }, async (req) => ({
    principalActor: req.principal?.actorId,
  }));
  app.get('/test/open', async () => ({ ok: true }));
  await app.ready();
  return app;
}

describe('AUD-004 M2: principal boundary enforcement', () => {
  let app: FastifyInstance;
  let actor: Awaited<ReturnType<typeof provisionSignedActor>>;

  beforeAll(async () => {
    app = await buildApp();
    actor = await provisionSignedActor({ name: `m2-actor-${crypto.randomUUID()}`, roles: ['governor'] });
  });
  afterAll(async () => {
    await app.close();
  });

  it('rejects an unsigned request to a governed route (fail closed, 401)', async () => {
    const res = await app.inject({ method: 'POST', url: '/test/governed', payload: { x: 1 } });
    expect(res.statusCode).toBe(401);
    expect(res.json().reason).toBe('missing_signature');
  });

  it('accepts a properly signed request and resolves the SIGNING actor + roles', async () => {
    const res = await app.inject(
      signedInject({ actorId: actor.actorId, privateKey: actor.privateKey, method: 'POST', url: '/test/governed', body: { x: 1 } })
    );
    expect(res.statusCode).toBe(200);
    expect(res.json().principalActor).toBe(actor.actorId);
    expect(res.json().roles).toContain('governor');
  });

  it('ignores a caller-supplied body.actor_id — principal is the signer, not the body', async () => {
    const res = await app.inject(
      signedInject({
        actorId: actor.actorId,
        privateKey: actor.privateKey,
        method: 'POST',
        url: '/test/governed',
        body: { actor_id: '00000000-0000-4000-8000-000000000000', x: 2 },
      })
    );
    expect(res.statusCode).toBe(200);
    expect(res.json().principalActor).toBe(actor.actorId); // NOT the body's actor_id
  });

  it('rejects a forged signature (signed by a different key) with signature_invalid', async () => {
    const attacker = crypto.generateKeyPairSync('ed25519').privateKey;
    const res = await app.inject(
      signedInject({ actorId: actor.actorId, privateKey: attacker, method: 'POST', url: '/test/governed', body: { x: 1 } })
    );
    expect(res.statusCode).toBe(401);
    expect(res.json().reason).toBe('signature_invalid');
  });

  it('rejects a stale timestamp (outside the replay window)', async () => {
    const stale = new Date(Date.now() - 400_000).toISOString();
    const res = await app.inject(
      signedInject({ actorId: actor.actorId, privateKey: actor.privateKey, method: 'POST', url: '/test/governed', body: { x: 1 }, timestamp: stale })
    );
    expect(res.statusCode).toBe(401);
    expect(res.json().reason).toBe('timestamp_out_of_window');
  });

  it('rejects a replayed request (same nonce reused)', async () => {
    const headers = signHeaders({ actorId: actor.actorId, privateKey: actor.privateKey, method: 'POST', url: '/test/governed', body: { x: 9 }, nonce: 'm2-fixed-nonce' });
    const first = await app.inject({ method: 'POST', url: '/test/governed', headers, payload: { x: 9 } });
    expect(first.statusCode).toBe(200);
    const replay = await app.inject({ method: 'POST', url: '/test/governed', headers, payload: { x: 9 } });
    expect(replay.statusCode).toBe(401);
    expect(replay.json().reason).toBe('nonce_replayed');
  });

  it('rejects an unknown actor id (no registered identity)', async () => {
    const ephemeral = crypto.generateKeyPairSync('ed25519').privateKey;
    const res = await app.inject(
      signedInject({ actorId: '11111111-1111-4111-8111-111111111111', privateKey: ephemeral, method: 'POST', url: '/test/governed', body: { x: 1 } })
    );
    expect(res.statusCode).toBe(401);
    expect(res.json().reason).toBe('unknown_actor');
  });

  it('leaves non-governed routes unaffected (no signature required)', async () => {
    const res = await app.inject({ method: 'GET', url: '/test/open' });
    expect(res.statusCode).toBe(200);
  });

  describe('M3: credential-bound permission enforcement', () => {
    it('allows a principal whose role grants the required permission (governor -> treasury.penalty.impose)', async () => {
      const governor = await provisionSignedActor({ name: `m3-gov-${crypto.randomUUID()}`, roles: ['governor'] });
      const res = await app.inject(
        signedInject({ actorId: governor.actorId, privateKey: governor.privateKey, method: 'POST', url: '/test/treasury-penalty', body: { amount: 100 } })
      );
      expect(res.statusCode).toBe(200);
      expect(res.json().principalActor).toBe(governor.actorId);
    });

    it('fails closed (403) for an authenticated principal lacking the permission (task_executor)', async () => {
      const worker = await provisionSignedActor({ name: `m3-worker-${crypto.randomUUID()}`, roles: ['task_executor'] });
      const res = await app.inject(
        signedInject({ actorId: worker.actorId, privateKey: worker.privateKey, method: 'POST', url: '/test/treasury-penalty', body: { amount: 100 } })
      );
      expect(res.statusCode).toBe(403);
      expect(res.json().permission).toBe('treasury.penalty.impose');
    });
  });
});
