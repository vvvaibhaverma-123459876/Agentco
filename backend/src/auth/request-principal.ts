/**
 * AUD-004 remediation — Milestone M1: authenticated request principal.
 *
 * Binds a governed HTTP request to an IMMUTABLE authenticated principal by verifying an
 * Ed25519 signature over a canonical request string, using the actor's registered `identity`
 * key from the existing key ring (identity-authority.service `verifySignature` / `actor_key_ring`).
 *
 * The principal is the actor whose key VERIFIES the signature — never a caller-supplied
 * `body.actor_id` / `x-actor-id`. Fail-closed on any missing/invalid/expired/replayed/ambiguous
 * identity. This module is dependency-injected (the key lookup is passed in) so its crypto +
 * replay core is unit-testable without a database.
 */
import crypto from 'crypto';

export interface RequestPrincipal {
  /** Immutable actor id proven by the verified signature. */
  actorId: string;
  actorType: string;
  /** sha256 fingerprint of the key ring identity key that verified the request. */
  credentialFingerprint: string;
  roles: string[];
  authMethod: 'ed25519_request_signature';
  requestId: string;
}

export interface SignatureHeaders {
  actorId: string;
  timestamp: string;
  nonce: string;
  signature: string; // base64 Ed25519
}

/** Every failure path is fail-closed and carries a machine reason (never leaks key material). */
export class PrincipalAuthError extends Error {
  constructor(public readonly reason: string) {
    super(`principal authentication failed: ${reason}`);
    this.name = 'PrincipalAuthError';
  }
}

/**
 * Canonical string bound by the signature. Includes method, path, a hash of the body, a
 * timestamp and a nonce so a signature cannot be replayed against a different request.
 */
export function buildCanonicalString(
  method: string,
  path: string,
  body: Buffer | string | undefined,
  timestamp: string,
  nonce: string
): string {
  const bodyBuf = body === undefined ? Buffer.alloc(0) : typeof body === 'string' ? Buffer.from(body, 'utf8') : body;
  const bodyHash = crypto.createHash('sha256').update(bodyBuf).digest('hex');
  return [method.toUpperCase(), path, bodyHash, timestamp, nonce].join('\n');
}

/** Pure Ed25519 verify; returns false (never throws) on any malformed input. */
export function verifyEd25519(publicKeyPem: string, canonical: string, signatureB64: string): boolean {
  try {
    const pub = crypto.createPublicKey(publicKeyPem);
    if (pub.asymmetricKeyType !== 'ed25519') return false;
    return crypto.verify(null, Buffer.from(canonical, 'utf8'), pub, Buffer.from(signatureB64, 'base64'));
  } catch {
    return false;
  }
}

/** Anti-replay: bounded timestamp window + single-use (actorId,nonce). In-memory TTL store. */
export class ReplayGuard {
  private readonly seen = new Map<string, number>();
  constructor(
    private readonly windowMs = 300_000,
    private readonly now: () => number = () => Date.now()
  ) {}

  checkTimestamp(tsIso: string): void {
    const t = Date.parse(tsIso);
    if (Number.isNaN(t)) throw new PrincipalAuthError('bad_timestamp');
    if (Math.abs(this.now() - t) > this.windowMs) throw new PrincipalAuthError('timestamp_out_of_window');
  }

  /** Consume a nonce; throws if it was already used within the window. Call AFTER signature verifies. */
  consumeNonce(actorId: string, nonce: string): void {
    this.evict();
    const key = `${actorId}:${nonce}`;
    if (this.seen.has(key)) throw new PrincipalAuthError('nonce_replayed');
    this.seen.set(key, this.now() + this.windowMs);
  }

  private evict(): void {
    const n = this.now();
    for (const [k, exp] of this.seen) if (exp <= n) this.seen.delete(k);
  }
}

/** Extract the four signature headers, fail-closed on any missing one. */
export function extractSignatureHeaders(headers: Record<string, unknown>): SignatureHeaders {
  const get = (h: string): string => {
    const v = headers[h];
    const s = Array.isArray(v) ? v[0] : v;
    if (typeof s !== 'string' || s.length === 0) throw new PrincipalAuthError(`missing_header:${h}`);
    return s;
  };
  return {
    actorId: get('x-agentco-actor-id'),
    timestamp: get('x-agentco-timestamp'),
    nonce: get('x-agentco-nonce'),
    signature: get('x-agentco-signature'),
  };
}

export interface ActiveIdentity {
  actorId: string;
  actorType: string;
  status: string; // 'active' | 'suspended' | 'revoked'
  publicKeyPem: string;
  fingerprint: string;
  roles: string[];
}

/** DB-backed lookup of an actor's active `identity` key + roles. Injected so the core is DB-free-testable. */
export type IdentityLookup = (actorId: string) => Promise<ActiveIdentity | null>;

/**
 * Resolve the authenticated principal for a request, or throw PrincipalAuthError (fail-closed).
 * The returned actorId is ALWAYS the signing actor — a body/header `actor_id` has no effect here.
 */
export async function resolveRequestPrincipal(
  input: { method: string; path: string; body: Buffer | string | undefined; headers: Record<string, unknown>; requestId: string },
  deps: { lookup: IdentityLookup; replay: ReplayGuard }
): Promise<RequestPrincipal> {
  const h = extractSignatureHeaders(input.headers);
  deps.replay.checkTimestamp(h.timestamp);

  const identity = await deps.lookup(h.actorId);
  if (!identity) throw new PrincipalAuthError('unknown_actor');
  if (identity.status !== 'active') throw new PrincipalAuthError(`actor_${identity.status}`);

  const canonical = buildCanonicalString(input.method, input.path, input.body, h.timestamp, h.nonce);
  if (!verifyEd25519(identity.publicKeyPem, canonical, h.signature)) {
    throw new PrincipalAuthError('signature_invalid');
  }

  // Consume the nonce only after the signature verifies, so an attacker cannot burn a victim's nonce.
  deps.replay.consumeNonce(h.actorId, h.nonce);

  return {
    actorId: identity.actorId,
    actorType: identity.actorType,
    credentialFingerprint: identity.fingerprint,
    roles: identity.roles,
    authMethod: 'ed25519_request_signature',
    requestId: input.requestId,
  };
}
