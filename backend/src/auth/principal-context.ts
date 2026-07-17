/**
 * AUD-004 M2 — central request-principal resolution + fail-closed enforcement for Fastify.
 *
 * Registers one preHandler that:
 *   - resolves `request.principal` from a signed request (Ed25519 over the canonical string),
 *     using the DB identity lookup — the principal is ALWAYS the signing actor;
 *   - for a route that declares `config.principal.required`, fails closed (401) if no valid
 *     principal was resolved.
 *
 * `body.actor_id` / `x-actor-id` are never consulted here and cannot influence the principal.
 * Authorization (permission checks) is layered on top in M3 via `assertPermission`.
 */
import type { FastifyInstance, FastifyRequest } from 'fastify';
import {
  RequestPrincipal,
  ReplayGuard,
  resolveRequestPrincipal,
  canonicalJson,
  PrincipalAuthError,
  IdentityLookup,
} from './request-principal';
import { dbIdentityLookup } from './identity-lookup';

declare module 'fastify' {
  interface FastifyRequest {
    /** The authenticated principal, resolved from a verified signature. Never from the body. */
    principal?: RequestPrincipal;
    /** Machine reason a signed request failed to resolve (for fail-closed responses / audit). */
    principalError?: string;
  }
  interface FastifyContextConfig {
    principal?: { required?: boolean; permission?: string };
  }
}

export interface PrincipalDeps {
  lookup: IdentityLookup;
  replay: ReplayGuard;
}

/** Process-wide replay guard (single instance; a DB-backed nonce store replaces it for multi-node). */
export const defaultReplayGuard = new ReplayGuard();

function signatureHeaderPresent(req: FastifyRequest): boolean {
  const h = req.headers['x-agentco-signature'];
  return typeof h === 'string' && h.length > 0;
}

/** The body bytes bound by the signature: canonical JSON of the parsed body (both sides agree). */
function bodyForSignature(req: FastifyRequest): string {
  if (req.body === undefined || req.body === null) return '';
  if (typeof req.body === 'string') return req.body;
  return canonicalJson(req.body);
}

export function registerPrincipalResolution(
  app: FastifyInstance,
  deps: PrincipalDeps = { lookup: dbIdentityLookup, replay: defaultReplayGuard }
): void {
  app.addHook('preHandler', async (request, reply) => {
    if (signatureHeaderPresent(request)) {
      try {
        request.principal = await resolveRequestPrincipal(
          {
            method: request.method,
            path: request.url.split('?')[0],
            body: bodyForSignature(request),
            headers: request.headers as Record<string, unknown>,
            requestId: request.id,
          },
          deps
        );
      } catch (error) {
        request.principalError = error instanceof PrincipalAuthError ? error.reason : 'principal_error';
      }
    }

    const cfg = request.routeOptions?.config?.principal;
    if (cfg?.required && !request.principal) {
      return reply.status(401).send({
        error: 'authenticated principal required',
        reason: request.principalError ?? 'missing_signature',
      });
    }
  });
}

/** Route config helper: `{ config: requirePrincipal('judiciary.appeal.decide') }`. */
export function requirePrincipal(permission?: string): { principal: { required: true; permission?: string } } {
  return { principal: { required: true, ...(permission ? { permission } : {}) } };
}
