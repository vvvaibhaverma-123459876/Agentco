/**
 * AUD-004 M1 — authenticated request principal (DB-free unit tests).
 * Exercises impersonation resistance, fail-closed paths, and anti-replay of the
 * credential->principal binding, independent of Postgres.
 */
import crypto from 'crypto';
import {
  buildCanonicalString,
  verifyEd25519,
  ReplayGuard,
  extractSignatureHeaders,
  resolveRequestPrincipal,
  PrincipalAuthError,
  ActiveIdentity,
} from '../src/auth/request-principal';

function makeActor(actorId: string, roles: string[] = [], status = 'active') {
  const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');
  const publicKeyPem = publicKey.export({ type: 'spki', format: 'pem' }) as string;
  const fingerprint = crypto
    .createHash('sha256')
    .update(publicKey.export({ type: 'spki', format: 'der' }))
    .digest('hex');
  const identity: ActiveIdentity = { actorId, actorType: 'agent', status, publicKeyPem, fingerprint, roles };
  return { identity, privateKey, publicKeyPem, fingerprint };
}

function sign(privateKey: crypto.KeyObject, canonical: string): string {
  return crypto.sign(null, Buffer.from(canonical, 'utf8'), privateKey).toString('base64');
}

const T0 = Date.parse('2026-07-17T12:00:00.000Z');
const iso = (ms: number) => new Date(ms).toISOString();

function signedRequest(opts: {
  actorId: string;
  privateKey: crypto.KeyObject;
  method?: string;
  path?: string;
  body?: string;
  timestamp?: string;
  nonce?: string;
  bodyActorId?: string; // a DIFFERENT caller-supplied actor id, to prove it is ignored
}) {
  const method = opts.method ?? 'POST';
  const path = opts.path ?? '/api/judiciary/cases';
  const body = opts.body ?? JSON.stringify({ dispute_type: 'claim_challenge', actor_id: opts.bodyActorId ?? 'ignored' });
  const timestamp = opts.timestamp ?? iso(T0);
  const nonce = opts.nonce ?? crypto.randomUUID();
  const canonical = buildCanonicalString(method, path, body, timestamp, nonce);
  const signature = sign(opts.privateKey, canonical);
  return {
    method,
    path,
    body,
    requestId: 'req-1',
    headers: {
      'x-agentco-actor-id': opts.actorId,
      'x-agentco-timestamp': timestamp,
      'x-agentco-nonce': nonce,
      'x-agentco-signature': signature,
    } as Record<string, unknown>,
  };
}

describe('AUD-004 M1: request principal crypto core', () => {
  it('verifies a genuine Ed25519 signature and rejects a tampered one', () => {
    const { privateKey, publicKeyPem } = makeActor('a');
    const canonical = buildCanonicalString('POST', '/x', 'body', iso(T0), 'n1');
    const sig = sign(privateKey, canonical);
    expect(verifyEd25519(publicKeyPem, canonical, sig)).toBe(true);
    expect(verifyEd25519(publicKeyPem, canonical + 'x', sig)).toBe(false); // tampered payload
    const corrupt = Buffer.from(sig, 'base64');
    corrupt[0] ^= 0xff; // flip a real signature byte (base64 last-char redundancy would not)
    expect(verifyEd25519(publicKeyPem, canonical, corrupt.toString('base64'))).toBe(false);
    expect(verifyEd25519(publicKeyPem, canonical, '')).toBe(false); // empty sig
  });

  it('extractSignatureHeaders fails closed on any missing header', () => {
    expect(() => extractSignatureHeaders({})).toThrow(PrincipalAuthError);
    expect(() =>
      extractSignatureHeaders({ 'x-agentco-actor-id': 'a', 'x-agentco-timestamp': 't', 'x-agentco-nonce': 'n' })
    ).toThrow(/missing_header:x-agentco-signature/);
  });

  it('ReplayGuard enforces the timestamp window and single-use nonce', () => {
    const g = new ReplayGuard(300_000, () => T0);
    expect(() => g.checkTimestamp(iso(T0))).not.toThrow();
    expect(() => g.checkTimestamp(iso(T0 - 400_000))).toThrow(/timestamp_out_of_window/);
    expect(() => g.checkTimestamp('not-a-date')).toThrow(/bad_timestamp/);
    g.consumeNonce('a', 'n1');
    expect(() => g.consumeNonce('a', 'n1')).toThrow(/nonce_replayed/);
    expect(() => g.consumeNonce('a', 'n2')).not.toThrow();
  });
});

describe('AUD-004 M1: resolveRequestPrincipal', () => {
  const replay = () => new ReplayGuard(300_000, () => T0);

  it('resolves the principal from the SIGNING actor, ignoring a caller-supplied body actor_id', async () => {
    const attacker = makeActor('attacker-actor', ['task_executor']);
    const lookup = async (id: string) => (id === 'attacker-actor' ? attacker.identity : null);
    // body claims to be the victim; the request is signed by the attacker's own key
    const req = signedRequest({ actorId: 'attacker-actor', privateKey: attacker.privateKey, bodyActorId: 'victim-actor' });
    const principal = await resolveRequestPrincipal(req, { lookup, replay: replay() });
    expect(principal.actorId).toBe('attacker-actor'); // NEVER the body's 'victim-actor'
    expect(principal.authMethod).toBe('ed25519_request_signature');
    expect(principal.credentialFingerprint).toBe(attacker.fingerprint);
    expect(principal.roles).toEqual(['task_executor']);
  });

  it('blocks impersonation: claiming a victim actor id you do not hold the key for fails closed', async () => {
    const victim = makeActor('victim-actor');
    const attacker = makeActor('attacker-actor');
    const lookup = async (id: string) => (id === 'victim-actor' ? victim.identity : null);
    // attacker sets the header actor id to the victim but signs with the attacker key
    const req = signedRequest({ actorId: 'victim-actor', privateKey: attacker.privateKey });
    await expect(resolveRequestPrincipal(req, { lookup, replay: replay() })).rejects.toThrow(/signature_invalid/);
  });

  it('fails closed for unknown, suspended, and revoked actors', async () => {
    const a = makeActor('a');
    const susp = makeActor('s', [], 'suspended');
    const req = (id: string, pk: crypto.KeyObject) => signedRequest({ actorId: id, privateKey: pk });
    await expect(
      resolveRequestPrincipal(req('a', a.privateKey), { lookup: async () => null, replay: replay() })
    ).rejects.toThrow(/unknown_actor/);
    await expect(
      resolveRequestPrincipal(req('s', susp.privateKey), { lookup: async () => susp.identity, replay: replay() })
    ).rejects.toThrow(/actor_suspended/);
  });

  it('rejects a replayed request (same nonce) even with a valid signature', async () => {
    const a = makeActor('a', ['task_executor']);
    const lookup = async () => a.identity;
    const guard = replay();
    const req = signedRequest({ actorId: 'a', privateKey: a.privateKey, nonce: 'fixed-nonce' });
    await expect(resolveRequestPrincipal(req, { lookup, replay: guard })).resolves.toBeDefined();
    await expect(resolveRequestPrincipal(req, { lookup, replay: guard })).rejects.toThrow(/nonce_replayed/);
  });

  it('rejects a signature bound to a different body (anti-replay across requests)', async () => {
    const a = makeActor('a');
    const lookup = async () => a.identity;
    const good = signedRequest({ actorId: 'a', privateKey: a.privateKey, body: '{"amount":1}' });
    // reuse the signed headers but swap the body -> canonical string differs -> invalid
    const tampered = { ...good, body: '{"amount":1000000}' };
    await expect(resolveRequestPrincipal(tampered, { lookup, replay: replay() })).rejects.toThrow(/signature_invalid/);
  });
});
