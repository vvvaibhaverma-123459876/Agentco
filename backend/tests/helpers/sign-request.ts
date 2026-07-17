/**
 * AUD-004 test helper — provision a signed principal and sign inject requests.
 * Registers a real actor + its Ed25519 `identity` key via the existing IdentityAuthorityService,
 * so governed-route tests exercise the SAME credential->principal path as production.
 */
import crypto from 'crypto';
import type { InjectOptions } from 'light-my-request';
import { identityAuthorityService, ActorType } from '../../src/services/identity-authority.service';
import { buildCanonicalString, canonicalJson } from '../../src/auth/request-principal';

export interface SignedActor {
  actorId: string;
  privateKey: crypto.KeyObject;
  publicKeyPem: string;
}

/** Register an actor + its identity key + roles; returns the signing material. */
export async function provisionSignedActor(opts: {
  name: string;
  actorType?: ActorType;
  roles?: string[];
}): Promise<SignedActor> {
  const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');
  const publicKeyPem = publicKey.export({ type: 'spki', format: 'pem' }) as string;
  const actor = await identityAuthorityService.registerActor({
    actor_type: opts.actorType ?? 'human',
    name: opts.name,
  });
  await identityAuthorityService.registerKey({
    actor_id: actor.id,
    key_purpose: 'identity',
    public_key_pem: publicKeyPem,
  });
  for (const role of opts.roles ?? []) {
    await identityAuthorityService.assignRole({ actor_id: actor.id, role_name: role });
  }
  return { actorId: actor.id, privateKey, publicKeyPem };
}

export interface SignOpts {
  actorId: string;
  privateKey: crypto.KeyObject;
  method: string;
  url: string;
  body?: unknown;
  timestamp?: string;
  nonce?: string;
}

/** Build the four signature headers for a request. */
export function signHeaders(opts: SignOpts): Record<string, string> {
  const path = opts.url.split('?')[0];
  const bodyStr =
    opts.body === undefined || opts.body === null
      ? ''
      : typeof opts.body === 'string'
        ? opts.body
        : canonicalJson(opts.body);
  const timestamp = opts.timestamp ?? new Date().toISOString();
  const nonce = opts.nonce ?? crypto.randomUUID();
  const canonical = buildCanonicalString(opts.method, path, bodyStr, timestamp, nonce);
  const signature = crypto.sign(null, Buffer.from(canonical, 'utf8'), opts.privateKey).toString('base64');
  return {
    'x-agentco-actor-id': opts.actorId,
    'x-agentco-timestamp': timestamp,
    'x-agentco-nonce': nonce,
    'x-agentco-signature': signature,
  };
}

/** Full inject options (headers + payload) for a signed request. Extra headers merge in. */
export function signedInject(opts: SignOpts & { headers?: Record<string, string> }): InjectOptions {
  return {
    method: opts.method as InjectOptions['method'],
    url: opts.url,
    headers: { ...signHeaders(opts), ...(opts.headers ?? {}) },
    ...(opts.body === undefined ? {} : { payload: opts.body as InjectOptions['payload'] }),
  };
}
