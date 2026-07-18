/**
 * AUD-004 M2 — DB-backed identity lookup for principal resolution.
 * Reads the EXISTING identity substrate (migration 079 / key ring 086): the actor's status,
 * its active `identity` Ed25519 public key + fingerprint, and its currently-valid roles.
 * Returns null when the actor is unknown or has no active identity key (fail-closed upstream).
 */
import { db } from '../db/client';
import type { ActiveIdentity, IdentityLookup } from './request-principal';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export const dbIdentityLookup: IdentityLookup = async (actorId: string): Promise<ActiveIdentity | null> => {
  if (!UUID_RE.test(actorId)) return null;

  const actor = await db.query<{ actor_type: string; status: string }>(
    'SELECT actor_type, status FROM actors WHERE id = $1',
    [actorId]
  );
  if (actor.rowCount !== 1) return null;

  const key = await db.query<{ public_key_pem: string; fingerprint_sha256: string }>(
    `SELECT public_key_pem, fingerprint_sha256
       FROM actor_key_ring
      WHERE actor_id = $1 AND key_purpose = 'identity' AND status = 'active'
      ORDER BY created_at DESC
      LIMIT 1`,
    [actorId]
  );
  if (key.rowCount !== 1) return null; // no active identity credential -> cannot authenticate

  const roles = await db.query<{ role_name: string }>(
    `SELECT r.role_name
       FROM role_assignments ra
       JOIN roles r ON r.id = ra.role_id
      WHERE ra.actor_id = $1
        AND ra.revoked_at IS NULL
        AND ra.valid_from <= now()
        AND (ra.valid_to IS NULL OR ra.valid_to > now())`,
    [actorId]
  );

  return {
    actorId,
    actorType: actor.rows[0].actor_type,
    status: actor.rows[0].status, // resolver rejects non-active
    publicKeyPem: key.rows[0].public_key_pem,
    fingerprint: key.rows[0].fingerprint_sha256,
    roles: roles.rows.map((r) => r.role_name),
  };
};
