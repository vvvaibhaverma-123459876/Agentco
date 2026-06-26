import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';

export type ActorType =
  | 'human'
  | 'agent'
  | 'service'
  | 'institution'
  | 'external_system'
  | 'resolver'
  | 'auditor'
  | 'governor';

export interface RegisterActorInput {
  actor_type: ActorType;
  name: string;
  metadata?: Record<string, unknown>;
  agent_identity?: {
    agent_key: string;
    model_name: string;
    version: string;
    owner_institution_id?: string | null;
    public_key_pem?: string | null;
  };
  service_identity?: {
    service_name: string;
    scopes: string[];
  };
  correlation_id?: string;
}

export interface ActorRecord {
  id: string;
  actor_type: ActorType;
  name: string;
  status: 'active' | 'suspended' | 'revoked';
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface AssignRoleInput {
  actor_id: string;
  role_name: string;
  assigned_by?: string | null;
  institution_id?: string | null;
  correlation_id?: string;
}

export interface GrantPermissionInput {
  actor_id: string;
  permission_name: string;
  granted_by?: string | null;
  scope?: string;
  expires_at?: string | null;
  correlation_id?: string;
}

export interface AuthorityDecision {
  actor_id: string;
  permission_name: string;
  scope: string;
  allowed: boolean;
  reason: string;
}

const ACTOR_TYPES: Set<string> = new Set([
  'human',
  'agent',
  'service',
  'institution',
  'external_system',
  'resolver',
  'auditor',
  'governor',
]);

function requireUuid(value: string, field: string): void {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error(`${field} must be a UUID`);
  }
}

function normalizeScope(scope?: string): string {
  const normalized = (scope ?? '*').trim();
  if (!normalized) throw new Error('scope must not be empty');
  return normalized;
}

function toBuffer(pem?: string | null): Buffer | null {
  if (!pem) return null;
  return Buffer.from(pem, 'utf8');
}

function auditContent(fields: Record<string, unknown>): string {
  return JSON.stringify(fields, Object.keys(fields).sort());
}

export class IdentityAuthorityService {
  async registerActor(input: RegisterActorInput): Promise<ActorRecord> {
    this.validateRegisterActor(input);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const result = await client.query<ActorRecord>(
        `INSERT INTO actors (actor_type, name, metadata_json)
         VALUES ($1,$2,$3::jsonb)
         RETURNING id, actor_type, name, status, metadata_json, created_at`,
        [input.actor_type, input.name.trim(), JSON.stringify(input.metadata ?? {})]
      );
      const actor = result.rows[0];

      if (input.agent_identity) {
        await client.query(
          `INSERT INTO agent_identities
             (actor_id, agent_key, model_name, version, owner_institution_id, public_key)
           VALUES ($1,$2,$3,$4,$5,$6)`,
          [
            actor.id,
            input.agent_identity.agent_key,
            input.agent_identity.model_name,
            input.agent_identity.version,
            input.agent_identity.owner_institution_id ?? null,
            toBuffer(input.agent_identity.public_key_pem),
          ]
        );
      }

      if (input.service_identity) {
        await client.query(
          `INSERT INTO service_identities (actor_id, service_name, scopes)
           VALUES ($1,$2,$3::jsonb)`,
          [actor.id, input.service_identity.service_name, JSON.stringify(input.service_identity.scopes)]
        );
      }

      await this.writeEventAndAudit(client, {
        actorId: actor.id,
        eventType: 'actor.registered',
        payload: {
          actor_id: actor.id,
          actor_type: actor.actor_type,
          name: actor.name,
          has_agent_identity: !!input.agent_identity,
          has_service_identity: !!input.service_identity,
        },
        correlationId: input.correlation_id,
        inputSummary: `register actor type=${actor.actor_type}`,
        outputSummary: `actor_id=${actor.id}`,
      });

      await client.query('COMMIT');
      return actor;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async assignRole(input: AssignRoleInput): Promise<{ assignment_id: string }> {
    requireUuid(input.actor_id, 'actor_id');
    if (input.assigned_by) requireUuid(input.assigned_by, 'assigned_by');
    if (input.institution_id) requireUuid(input.institution_id, 'institution_id');
    if (!input.role_name?.trim()) throw new Error('role_name is required');

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireActiveActor(client, input.actor_id);
      if (input.assigned_by) await this.requireActiveActor(client, input.assigned_by);

      const role = await client.query<{ id: string }>(
        'SELECT id FROM roles WHERE role_name = $1',
        [input.role_name]
      );
      if (role.rowCount !== 1) {
        throw new Error(`unknown role: ${input.role_name}`);
      }

      const result = await client.query<{ id: string }>(
        `INSERT INTO role_assignments (actor_id, role_id, institution_id, assigned_by)
         VALUES ($1,$2,$3,$4)
         ON CONFLICT (actor_id, role_id, COALESCE(institution_id, '00000000-0000-0000-0000-000000000000'::uuid))
           WHERE revoked_at IS NULL
         DO UPDATE SET valid_from = role_assignments.valid_from
         RETURNING id`,
        [input.actor_id, role.rows[0].id, input.institution_id ?? null, input.assigned_by ?? null]
      );

      await this.writeEventAndAudit(client, {
        actorId: input.assigned_by ?? input.actor_id,
        eventType: 'role.assigned',
        payload: {
          actor_id: input.actor_id,
          role_name: input.role_name,
          institution_id: input.institution_id ?? null,
          assignment_id: result.rows[0].id,
        },
        correlationId: input.correlation_id,
        inputSummary: `assign role=${input.role_name}`,
        outputSummary: `assignment_id=${result.rows[0].id}`,
      });

      await client.query('COMMIT');
      return { assignment_id: result.rows[0].id };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async grantPermission(input: GrantPermissionInput): Promise<{ grant_id: string }> {
    requireUuid(input.actor_id, 'actor_id');
    if (input.granted_by) requireUuid(input.granted_by, 'granted_by');
    const scope = normalizeScope(input.scope);
    if (!input.permission_name?.trim()) throw new Error('permission_name is required');

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireActiveActor(client, input.actor_id);
      if (input.granted_by) await this.requireActiveActor(client, input.granted_by);

      const permission = await client.query<{ id: string }>(
        'SELECT id FROM permissions WHERE name = $1',
        [input.permission_name]
      );
      if (permission.rowCount !== 1) {
        throw new Error(`unknown permission: ${input.permission_name}`);
      }

      const result = await client.query<{ id: string }>(
        `INSERT INTO actor_permissions (actor_id, permission_id, scope, granted_by, expires_at)
         VALUES ($1,$2,$3,$4,$5)
         ON CONFLICT (actor_id, permission_id, scope)
           WHERE revoked_at IS NULL
         DO UPDATE SET expires_at = EXCLUDED.expires_at
         RETURNING id`,
        [input.actor_id, permission.rows[0].id, scope, input.granted_by ?? null, input.expires_at ?? null]
      );

      await this.writeEventAndAudit(client, {
        actorId: input.granted_by ?? input.actor_id,
        eventType: 'permission.granted',
        payload: {
          actor_id: input.actor_id,
          permission_name: input.permission_name,
          scope,
          grant_id: result.rows[0].id,
        },
        correlationId: input.correlation_id,
        inputSummary: `grant permission=${input.permission_name}`,
        outputSummary: `grant_id=${result.rows[0].id}`,
      });

      await client.query('COMMIT');
      return { grant_id: result.rows[0].id };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async verifyAuthority(actorId: string, permissionName: string, scope = '*'): Promise<AuthorityDecision> {
    requireUuid(actorId, 'actor_id');
    if (!permissionName?.trim()) throw new Error('permission_name is required');
    const requestedScope = normalizeScope(scope);

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const actor = await client.query<{ status: string }>(
        'SELECT status FROM actors WHERE id = $1',
        [actorId]
      );
      if (actor.rowCount !== 1) {
        const decision = {
          actor_id: actorId,
          permission_name: permissionName,
          scope: requestedScope,
          allowed: false,
          reason: 'actor_not_found',
        };
        await this.writeAuthorityEvent(client, decision);
        await client.query('COMMIT');
        return decision;
      }
      if (actor.rows[0].status !== 'active') {
        const decision = {
          actor_id: actorId,
          permission_name: permissionName,
          scope: requestedScope,
          allowed: false,
          reason: `actor_${actor.rows[0].status}`,
        };
        await this.writeAuthorityEvent(client, decision);
        await client.query('COMMIT');
        return decision;
      }

      const direct = await client.query(
        `SELECT 1
           FROM actor_permissions ap
           JOIN permissions p ON p.id = ap.permission_id
          WHERE ap.actor_id = $1
            AND p.name = $2
            AND ap.revoked_at IS NULL
            AND (ap.expires_at IS NULL OR ap.expires_at > now())
            AND (ap.scope = '*' OR ap.scope = $3)
          LIMIT 1`,
        [actorId, permissionName, requestedScope]
      );

      const decision = {
        actor_id: actorId,
        permission_name: permissionName,
        scope: requestedScope,
        allowed: (direct.rowCount ?? 0) > 0,
        reason: (direct.rowCount ?? 0) > 0 ? 'permission_granted' : 'permission_missing',
      };
      await this.writeAuthorityEvent(client, decision);
      await client.query('COMMIT');
      return decision;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private validateRegisterActor(input: RegisterActorInput): void {
    if (!ACTOR_TYPES.has(input.actor_type)) {
      throw new Error(`invalid actor_type: ${input.actor_type}`);
    }
    if (!input.name?.trim()) throw new Error('name is required');
    if (input.actor_type === 'agent' && !input.agent_identity) {
      throw new Error('agent actor requires agent_identity');
    }
    if (input.actor_type === 'service' && !input.service_identity) {
      throw new Error('service actor requires service_identity');
    }
    if (input.agent_identity) {
      if (!input.agent_identity.agent_key?.trim()) throw new Error('agent_key is required');
      if (!input.agent_identity.model_name?.trim()) throw new Error('model_name is required');
      if (!input.agent_identity.version?.trim()) throw new Error('version is required');
    }
    if (input.service_identity) {
      if (!input.service_identity.service_name?.trim()) throw new Error('service_name is required');
      if (!Array.isArray(input.service_identity.scopes)) throw new Error('service scopes must be an array');
    }
  }

  private async requireActiveActor(client: PoolClient, actorId: string): Promise<void> {
    const result = await client.query<{ status: string }>(
      'SELECT status FROM actors WHERE id = $1',
      [actorId]
    );
    if (result.rowCount !== 1) throw new Error(`actor not found: ${actorId}`);
    if (result.rows[0].status !== 'active') throw new Error(`actor is not active: ${actorId}`);
  }

  private async writeAuthorityEvent(client: PoolClient, decision: AuthorityDecision): Promise<void> {
    await this.writeEventAndAudit(client, {
      actorId: decision.actor_id,
      eventType: 'identity.authority_verified',
      payload: { ...decision },
      inputSummary: `verify permission=${decision.permission_name} scope=${decision.scope}`,
      outputSummary: `allowed=${decision.allowed} reason=${decision.reason}`,
    });
  }

  private async writeEventAndAudit(
    client: PoolClient,
    input: {
      actorId: string;
      eventType: string;
      payload: Record<string, unknown>;
      correlationId?: string;
      inputSummary: string;
      outputSummary: string;
    }
  ): Promise<void> {
    const eventId = crypto.randomUUID();
    const timestamp = new Date().toISOString();
    const sessionId = input.correlationId ?? crypto.randomUUID();

    await client.query(
      `INSERT INTO event_history
         (event_id, event_type, producer_agent_id, timestamp, confidence_score,
          payload, correlation_id, risk_level, requires_ack, ttl_seconds)
       VALUES ($1,$2,$3,$4,1.0,$5::jsonb,$6,'low',false,86400)`,
      [
        eventId,
        input.eventType,
        input.actorId,
        timestamp,
        JSON.stringify(input.payload),
        sessionId,
      ]
    );

    const previous = await client.query<{ chain_hash: string }>(
      `SELECT chain_hash FROM decision_log
        WHERE chain_hash <> ''
        ORDER BY timestamp DESC, log_id DESC
        LIMIT 1`
    );
    const prevHash = previous.rows[0]?.chain_hash ?? '0'.repeat(64);
    const logId = crypto.randomUUID();
    const content = auditContent({
      log_id: logId,
      timestamp,
      prev_hash: prevHash,
      agent_id: input.actorId,
      action_type: 'event_published',
      input_summary: input.inputSummary,
      output_summary: input.outputSummary,
      confidence_score: 1,
      risk_level: 'low',
      human_approved: false,
      human_approver_id: null,
      downstream_events: [eventId],
      session_id: sessionId,
    });
    const chainHash = crypto.createHash('sha256').update(prevHash + content).digest('hex');

    await client.query(
      `INSERT INTO decision_log
         (log_id, agent_id, action_type, input_summary, output_summary,
          confidence_score, risk_level, human_approved, downstream_events,
          session_id, timestamp, chain_hash, prev_hash)
       VALUES ($1,$2,'event_published',$3,$4,1.0,'low',false,$5::uuid[],$6,$7,$8,$9)`,
      [
        logId,
        input.actorId,
        input.inputSummary,
        input.outputSummary,
        [eventId],
        sessionId,
        timestamp,
        chainHash,
        prevHash,
      ]
    );
  }
}

export const identityAuthorityService = new IdentityAuthorityService();
