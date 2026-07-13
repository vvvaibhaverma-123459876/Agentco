import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { getAgentRegistryEntry } from '../agent-registry';
import { PublicHttpError } from '../http-errors';

/**
 * Citizenry (build phase C2).
 *
 * Every agent, human, or service performing civilization work is a registered
 * actor AND a citizen. Citizenship status gates protected execution
 * immediately (suspension blocks work); roles are institution/time scoped;
 * autonomy envelopes are domain scoped; sanctions require an external
 * authorization reference and cannot be self-imposed; succession transfers
 * active role eligibility without transferring historical identity.
 *
 * Trust link: budget multipliers derive from the latest (subject, domain)
 * trust_scores window. Unknown subjects keep multiplier 1.0 (unknown is not
 * distrusted); low or force-downgraded trust constrains budgets.
 */

export type CitizenStatus =
  | 'candidate' | 'probationary' | 'active' | 'restricted'
  | 'suspended' | 'expelled' | 'retired';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

const CITIZEN_TRANSITIONS: Record<CitizenStatus, CitizenStatus[]> = {
  candidate: ['probationary', 'expelled'],
  probationary: ['active', 'expelled'],
  active: ['restricted', 'suspended', 'retired'],
  restricted: ['active', 'suspended', 'expelled', 'retired'],
  suspended: ['active', 'expelled', 'retired'],
  expelled: [],
  retired: [],
};

const RISK_RANK: Record<RiskLevel, number> = { low: 0, medium: 1, high: 2, critical: 3 };

/** Statuses allowed to execute protected civilization work. */
const EXECUTABLE_STATUSES: CitizenStatus[] = ['active', 'probationary'];

export class CitizenshipBlockedError extends PublicHttpError {
  constructor(message: string) {
    super(403, message);
    this.name = 'CitizenshipBlockedError';
  }
}

export interface CitizenRecord {
  id: string;
  civilization_id: string;
  actor_id: string;
  citizen_type: 'agent' | 'human' | 'service';
  status: CitizenStatus;
  display_name: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

const CITIZEN_COLUMNS =
  'id, civilization_id, actor_id, citizen_type, status, display_name, metadata_json, created_at, updated_at';

export class CitizenshipService {
  // -------------------------------------------------------------------------
  // Registration and lookup
  // -------------------------------------------------------------------------

  async registerCitizen(input: {
    actor_id: string;
    citizen_type: 'agent' | 'human' | 'service';
    display_name?: string;
    civilization_id?: string;
    initial_status?: 'candidate' | 'active';
    enrollment_reason?: string;
  }): Promise<CitizenRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.registerCitizenWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async registerCitizenWithClient(client: PoolClient, input: {
    actor_id: string;
    citizen_type: 'agent' | 'human' | 'service';
    display_name?: string;
    civilization_id?: string;
    initial_status?: 'candidate' | 'active';
    enrollment_reason?: string;
  }): Promise<CitizenRecord> {
    const existing = await client.query<CitizenRecord>(
      `SELECT ${CITIZEN_COLUMNS} FROM citizens WHERE actor_id = $1 LIMIT 1`,
      [input.actor_id]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];

    let civilizationId = input.civilization_id;
    if (!civilizationId) {
      const root = await client.query<{ id: string }>(
        `SELECT id FROM civilizations WHERE status = 'active' LIMIT 1`
      );
      if ((root.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(409, 'no active civilization root; bootstrap the kernel first');
      }
      civilizationId = root.rows[0].id;
    }

    const actor = await client.query<{ name: string }>(
      `SELECT name FROM actors WHERE id = $1 LIMIT 1`,
      [input.actor_id]
    );
    if ((actor.rowCount ?? 0) !== 1) {
      throw new PublicHttpError(404, `actor not found: ${input.actor_id}`);
    }

    const citizenId = crypto.randomUUID();
    const initialStatus = input.initial_status ?? 'candidate';
    const event = await eventLog.appendWithClient(client, {
      event_type: 'citizenship.registered',
      actor_id: input.actor_id,
      object_type: 'citizen',
      object_id: citizenId,
      correlation_id: crypto.randomUUID(),
      payload: {
        civilization_id: civilizationId,
        citizen_type: input.citizen_type,
        initial_status: initialStatus,
        enrollment_reason: input.enrollment_reason ?? 'registration',
      },
    });
    const inserted = await client.query<CitizenRecord>(
      `INSERT INTO citizens
         (id, civilization_id, actor_id, citizen_type, status, display_name, metadata_json, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
       RETURNING ${CITIZEN_COLUMNS}`,
      [citizenId, civilizationId, input.actor_id, input.citizen_type, initialStatus,
       input.display_name ?? actor.rows[0].name,
       JSON.stringify({ enrollment_reason: input.enrollment_reason ?? 'registration' }), event.id]
    );
    await client.query(
      `INSERT INTO citizenship_records (citizen_id, from_status, to_status, reason, changed_by_actor_id, event_log_id)
       VALUES ($1,'none',$2,$3,$4,$5)`,
      [citizenId, initialStatus, input.enrollment_reason ?? 'registration', input.actor_id, event.id]
    );
    return inserted.rows[0];
  }

  async getCitizenByActor(actorId: string): Promise<CitizenRecord | null> {
    const result = await db.query<CitizenRecord>(
      `SELECT ${CITIZEN_COLUMNS} FROM citizens WHERE actor_id = $1 LIMIT 1`,
      [actorId]
    );
    return result.rows[0] ?? null;
  }

  async getCitizenByAgentKey(agentKey: string): Promise<CitizenRecord | null> {
    const result = await db.query<CitizenRecord>(
      `SELECT ${CITIZEN_COLUMNS.split(', ').map(c => 'c.' + c).join(', ')}
         FROM citizens c
         JOIN agent_identities ai ON ai.actor_id = c.actor_id
        WHERE ai.agent_key = $1
        LIMIT 1`,
      [agentKey]
    );
    return result.rows[0] ?? null;
  }

  async getCitizen(citizenId: string): Promise<CitizenRecord | null> {
    const result = await db.query<CitizenRecord>(
      `SELECT ${CITIZEN_COLUMNS} FROM citizens WHERE id = $1 LIMIT 1`,
      [citizenId]
    );
    return result.rows[0] ?? null;
  }

  async listCitizens(filter: { status?: CitizenStatus; citizen_type?: string } = {}): Promise<CitizenRecord[]> {
    const clauses: string[] = [];
    const params: unknown[] = [];
    if (filter.status) { params.push(filter.status); clauses.push(`status = $${params.length}`); }
    if (filter.citizen_type) { params.push(filter.citizen_type); clauses.push(`citizen_type = $${params.length}`); }
    const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
    const result = await db.query<CitizenRecord>(
      `SELECT ${CITIZEN_COLUMNS} FROM citizens ${where} ORDER BY created_at`, params as any[]
    );
    return result.rows;
  }

  // -------------------------------------------------------------------------
  // Lifecycle
  // -------------------------------------------------------------------------

  async transitionCitizen(input: {
    citizen_id: string;
    to_status: CitizenStatus;
    actor_id: string;
    reason: string;
    sanction_id?: string;
  }): Promise<CitizenRecord> {
    if (!input.reason || input.reason.trim().length === 0) {
      throw new PublicHttpError(400, 'reason is required');
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.transitionWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async transitionWithClient(client: PoolClient, input: {
    citizen_id: string;
    to_status: CitizenStatus;
    actor_id: string;
    reason: string;
    sanction_id?: string;
  }): Promise<CitizenRecord> {
    const current = await client.query<CitizenRecord>(
      `SELECT ${CITIZEN_COLUMNS} FROM citizens WHERE id = $1 FOR UPDATE`,
      [input.citizen_id]
    );
    if ((current.rowCount ?? 0) !== 1) {
      throw new PublicHttpError(404, `citizen not found: ${input.citizen_id}`);
    }
    const citizen = current.rows[0];
    const from = citizen.status;
    if (!CITIZEN_TRANSITIONS[from]?.includes(input.to_status)) {
      throw new PublicHttpError(409, `illegal citizenship transition ${from} -> ${input.to_status}`);
    }

    if (input.to_status === 'suspended' || input.to_status === 'expelled') {
      const requiredType = input.to_status === 'suspended' ? 'suspension' : 'expulsion';
      if (!input.sanction_id) {
        throw new PublicHttpError(400, `${input.to_status} requires an authorized ${requiredType} sanction`);
      }
      const sanction = await client.query<{ citizen_id: string; sanction_type: string; status: string; imposed_by_actor_id: string }>(
        `SELECT citizen_id, sanction_type, status, imposed_by_actor_id FROM citizen_sanctions WHERE id = $1`,
        [input.sanction_id]
      );
      if ((sanction.rowCount ?? 0) !== 1
          || sanction.rows[0].citizen_id !== input.citizen_id
          || sanction.rows[0].sanction_type !== requiredType
          || sanction.rows[0].status !== 'active') {
        throw new PublicHttpError(409, `active ${requiredType} sanction for this citizen is required`);
      }
    }

    if (input.to_status === 'active' && from === 'suspended') {
      const blocking = await client.query<{ count: string }>(
        `SELECT COUNT(*)::int AS count FROM citizen_sanctions
          WHERE citizen_id = $1 AND status = 'active' AND sanction_type IN ('suspension','expulsion')`,
        [input.citizen_id]
      );
      if (Number(blocking.rows[0].count) > 0) {
        throw new PublicHttpError(409, 'reinstatement requires lifting active suspension/expulsion sanctions first');
      }
    }

    const event = await eventLog.appendWithClient(client, {
      event_type: 'citizenship.status_changed',
      actor_id: input.actor_id,
      object_type: 'citizen',
      object_id: input.citizen_id,
      correlation_id: crypto.randomUUID(),
      payload: {
        from_status: from,
        to_status: input.to_status,
        reason: input.reason,
        sanction_id: input.sanction_id ?? null,
      },
    });

    await client.query(`SELECT set_config('civilization.citizenship_transition_authorized', 'true', true)`);
    const updated = await client.query<CitizenRecord>(
      `UPDATE citizens SET status = $2 WHERE id = $1 RETURNING ${CITIZEN_COLUMNS}`,
      [input.citizen_id, input.to_status]
    );
    await client.query(`SELECT set_config('civilization.citizenship_transition_authorized', 'false', true)`);

    await client.query(
      `INSERT INTO citizenship_records
         (citizen_id, from_status, to_status, reason, changed_by_actor_id, sanction_id, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7)`,
      [input.citizen_id, from, input.to_status, input.reason, input.actor_id, input.sanction_id ?? null, event.id]
    );

    await auditLog.appendWithClient(client, {
      agent_id: input.actor_id,
      action_type: 'decision',
      input_summary: `citizen ${citizen.display_name} (${input.citizen_id}) ${from} -> ${input.to_status}: ${input.reason}`,
      output_summary: `citizenship status is now ${input.to_status}`,
      confidence_score: 1,
      risk_level: input.to_status === 'expelled' || input.to_status === 'suspended' ? 'high' : 'medium',
      human_approved: false,
      downstream_events: [event.id],
    }, { timestamp: new Date().toISOString() });

    return updated.rows[0];
  }

  // -------------------------------------------------------------------------
  // Sanctions
  // -------------------------------------------------------------------------

  async imposeSanction(input: {
    citizen_id: string;
    sanction_type: 'warning' | 'restriction' | 'suspension' | 'expulsion' | 'budget_penalty';
    reason: string;
    imposed_by_actor_id: string;
    authorized_decision_ref: string;
    effective_until?: string;
  }): Promise<{ id: string; sanction_type: string; status: string }> {
    if (!input.authorized_decision_ref || input.authorized_decision_ref.trim().length === 0) {
      throw new PublicHttpError(400, 'authorized_decision_ref is required — sanctions need governance or judiciary authority');
    }
    if (!input.reason || input.reason.trim().length === 0) {
      throw new PublicHttpError(400, 'reason is required');
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const citizen = await client.query<{ actor_id: string; display_name: string }>(
        `SELECT actor_id, display_name FROM citizens WHERE id = $1 LIMIT 1`,
        [input.citizen_id]
      );
      if ((citizen.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(404, `citizen not found: ${input.citizen_id}`);
      }
      if (citizen.rows[0].actor_id === input.imposed_by_actor_id) {
        throw new PublicHttpError(409, 'self-sanction is not permitted');
      }
      const sanctionId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'citizenship.sanction_imposed',
        actor_id: input.imposed_by_actor_id,
        object_type: 'citizen_sanction',
        object_id: sanctionId,
        correlation_id: crypto.randomUUID(),
        payload: {
          citizen_id: input.citizen_id,
          sanction_type: input.sanction_type,
          reason: input.reason,
          authorized_decision_ref: input.authorized_decision_ref,
          effective_until: input.effective_until ?? null,
        },
      });
      const inserted = await client.query<{ id: string; sanction_type: string; status: string }>(
        `INSERT INTO citizen_sanctions
           (id, citizen_id, sanction_type, reason, imposed_by_actor_id, authorized_decision_ref, effective_until, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
         RETURNING id, sanction_type, status`,
        [sanctionId, input.citizen_id, input.sanction_type, input.reason,
         input.imposed_by_actor_id, input.authorized_decision_ref, input.effective_until ?? null, event.id]
      );
      await auditLog.appendWithClient(client, {
        agent_id: input.imposed_by_actor_id,
        action_type: 'decision',
        input_summary: `impose ${input.sanction_type} on citizen ${citizen.rows[0].display_name}: ${input.reason}`,
        output_summary: `sanction ${sanctionId} active (authority: ${input.authorized_decision_ref})`,
        confidence_score: 1,
        risk_level: 'high',
        human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** Impose a suspension sanction and suspend the citizen in one transaction. */
  async suspendCitizen(input: {
    citizen_id: string;
    reason: string;
    imposed_by_actor_id: string;
    authorized_decision_ref: string;
  }): Promise<{ citizen: CitizenRecord; sanction_id: string }> {
    const sanction = await this.imposeSanction({
      citizen_id: input.citizen_id,
      sanction_type: 'suspension',
      reason: input.reason,
      imposed_by_actor_id: input.imposed_by_actor_id,
      authorized_decision_ref: input.authorized_decision_ref,
    });
    const citizen = await this.transitionCitizen({
      citizen_id: input.citizen_id,
      to_status: 'suspended',
      actor_id: input.imposed_by_actor_id,
      reason: input.reason,
      sanction_id: sanction.id,
    });
    return { citizen, sanction_id: sanction.id };
  }

  async liftSanction(input: { sanction_id: string; actor_id: string; reason: string }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const sanction = await client.query<{ citizen_id: string; status: string }>(
        `SELECT citizen_id, status FROM citizen_sanctions WHERE id = $1 FOR UPDATE`,
        [input.sanction_id]
      );
      if ((sanction.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(404, `sanction not found: ${input.sanction_id}`);
      }
      if (sanction.rows[0].status !== 'active') {
        throw new PublicHttpError(409, `sanction is already ${sanction.rows[0].status}`);
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: 'citizenship.sanction_lifted',
        actor_id: input.actor_id,
        object_type: 'citizen_sanction',
        object_id: input.sanction_id,
        correlation_id: crypto.randomUUID(),
        payload: { citizen_id: sanction.rows[0].citizen_id, reason: input.reason },
      });
      await client.query(
        `UPDATE citizen_sanctions SET status = 'lifted', lifted_at = now(), lifted_by_actor_id = $2 WHERE id = $1`,
        [input.sanction_id, input.actor_id]
      );
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `lift sanction ${input.sanction_id}: ${input.reason}`,
        output_summary: `sanction ${input.sanction_id} lifted`,
        confidence_score: 1,
        risk_level: 'medium',
        human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // -------------------------------------------------------------------------
  // Role eligibility and autonomy envelopes
  // -------------------------------------------------------------------------

  async grantRoleEligibility(input: {
    citizen_id: string;
    role_name: string;
    institution_id?: string;
    domain?: string;
    valid_to?: string;
    granted_by_actor_id: string;
  }): Promise<{ id: string; role_name: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const grantId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'citizenship.role_granted',
        actor_id: input.granted_by_actor_id,
        object_type: 'citizen_role_eligibility',
        object_id: grantId,
        correlation_id: crypto.randomUUID(),
        payload: {
          citizen_id: input.citizen_id,
          role_name: input.role_name,
          institution_id: input.institution_id ?? null,
          domain: input.domain ?? null,
          valid_to: input.valid_to ?? null,
        },
      });
      const inserted = await client.query<{ id: string; role_name: string }>(
        `INSERT INTO citizen_role_eligibility
           (id, citizen_id, role_name, institution_id, domain, valid_to, granted_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
         RETURNING id, role_name`,
        [grantId, input.citizen_id, input.role_name, input.institution_id ?? null,
         input.domain ?? null, input.valid_to ?? null, input.granted_by_actor_id, event.id]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async revokeRoleEligibility(input: { eligibility_id: string; actor_id: string; reason: string }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await eventLog.appendWithClient(client, {
        event_type: 'citizenship.role_revoked',
        actor_id: input.actor_id,
        object_type: 'citizen_role_eligibility',
        object_id: input.eligibility_id,
        correlation_id: crypto.randomUUID(),
        payload: { reason: input.reason },
      });
      const updated = await client.query(
        `UPDATE citizen_role_eligibility
            SET status = 'revoked', revoked_at = now(), revoked_by_actor_id = $2
          WHERE id = $1 AND status = 'active'`,
        [input.eligibility_id, input.actor_id]
      );
      if ((updated.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(409, 'eligibility not found or not active');
      }
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async hasActiveRole(citizenId: string, roleName: string, options: { institution_id?: string; domain?: string } = {}): Promise<boolean> {
    const result = await db.query<{ count: string }>(
      `SELECT COUNT(*)::int AS count FROM citizen_role_eligibility
        WHERE citizen_id = $1 AND role_name = $2 AND status = 'active'
          AND valid_from <= now() AND (valid_to IS NULL OR valid_to > now())
          AND ($3::varchar IS NULL OR institution_id IS NULL OR institution_id = $3)
          AND ($4::text IS NULL OR domain IS NULL OR domain = $4)`,
      [citizenId, roleName, options.institution_id ?? null, options.domain ?? null]
    );
    return Number(result.rows[0].count) > 0;
  }

  async setAutonomyEnvelope(input: {
    citizen_id: string;
    domain: string;
    max_risk_level: RiskLevel;
    budget_multiplier?: number;
    granted_by_actor_id: string;
  }): Promise<{ id: string; domain: string; max_risk_level: string; budget_multiplier: number }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      // Revoke any current active envelope for this (citizen, domain).
      await client.query(
        `UPDATE citizen_autonomy_envelopes
            SET status = 'revoked', revoked_at = now(), revoked_by_actor_id = $3
          WHERE citizen_id = $1 AND domain = $2 AND status = 'active'`,
        [input.citizen_id, input.domain, input.granted_by_actor_id]
      );
      const envelopeId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'citizenship.envelope_set',
        actor_id: input.granted_by_actor_id,
        object_type: 'citizen_autonomy_envelope',
        object_id: envelopeId,
        correlation_id: crypto.randomUUID(),
        payload: {
          citizen_id: input.citizen_id,
          domain: input.domain,
          max_risk_level: input.max_risk_level,
          budget_multiplier: input.budget_multiplier ?? 1.0,
        },
      });
      const inserted = await client.query<{ id: string; domain: string; max_risk_level: string; budget_multiplier: number }>(
        `INSERT INTO citizen_autonomy_envelopes
           (id, citizen_id, domain, max_risk_level, budget_multiplier, granted_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7)
         RETURNING id, domain, max_risk_level, budget_multiplier`,
        [envelopeId, input.citizen_id, input.domain, input.max_risk_level,
         input.budget_multiplier ?? 1.0, input.granted_by_actor_id, event.id]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // -------------------------------------------------------------------------
  // Succession
  // -------------------------------------------------------------------------

  async recordSuccession(input: {
    from_citizen_id: string;
    to_citizen_id: string;
    reason: string;
    recorded_by_actor_id: string;
    scope?: Record<string, unknown>;
  }): Promise<{ id: string; transferred_roles: string[] }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const fromCitizen = await client.query<CitizenRecord>(
        `SELECT ${CITIZEN_COLUMNS} FROM citizens WHERE id = $1 FOR UPDATE`,
        [input.from_citizen_id]
      );
      const toCitizen = await client.query<CitizenRecord>(
        `SELECT ${CITIZEN_COLUMNS} FROM citizens WHERE id = $1 FOR UPDATE`,
        [input.to_citizen_id]
      );
      if ((fromCitizen.rowCount ?? 0) !== 1 || (toCitizen.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(404, 'both citizens must exist');
      }
      if (!['suspended', 'expelled', 'retired'].includes(fromCitizen.rows[0].status)) {
        throw new PublicHttpError(409, 'succession source must be suspended, expelled, or retired');
      }
      if (toCitizen.rows[0].status !== 'active') {
        throw new PublicHttpError(409, 'succession target must be an active citizen');
      }

      // Transfer responsibilities: revoke source's active roles, re-grant to target.
      const activeRoles = await client.query<{ id: string; role_name: string; institution_id: string | null; domain: string | null; valid_to: string | null }>(
        `SELECT id, role_name, institution_id, domain, valid_to
           FROM citizen_role_eligibility
          WHERE citizen_id = $1 AND status = 'active'`,
        [input.from_citizen_id]
      );
      const transferred: string[] = [];
      for (const role of activeRoles.rows) {
        await client.query(
          `UPDATE citizen_role_eligibility
              SET status = 'revoked', revoked_at = now(), revoked_by_actor_id = $2
            WHERE id = $1`,
          [role.id, input.recorded_by_actor_id]
        );
        await client.query(
          `INSERT INTO citizen_role_eligibility
             (citizen_id, role_name, institution_id, domain, valid_to, granted_by_actor_id)
           VALUES ($1,$2,$3,$4,$5,$6)
           ON CONFLICT DO NOTHING`,
          [input.to_citizen_id, role.role_name, role.institution_id, role.domain,
           role.valid_to, input.recorded_by_actor_id]
        );
        transferred.push(role.role_name);
      }

      const successionId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'citizenship.succession_recorded',
        actor_id: input.recorded_by_actor_id,
        object_type: 'citizen_succession',
        object_id: successionId,
        correlation_id: crypto.randomUUID(),
        payload: {
          from_citizen_id: input.from_citizen_id,
          to_citizen_id: input.to_citizen_id,
          transferred_roles: transferred,
          reason: input.reason,
        },
      });
      await client.query(
        `INSERT INTO citizen_successions
           (id, from_citizen_id, to_citizen_id, transferred_roles, scope_json, reason, recorded_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4::jsonb,$5::jsonb,$6,$7,$8)`,
        [successionId, input.from_citizen_id, input.to_citizen_id, JSON.stringify(transferred),
         JSON.stringify(input.scope ?? {}), input.reason, input.recorded_by_actor_id, event.id]
      );
      await auditLog.appendWithClient(client, {
        agent_id: input.recorded_by_actor_id,
        action_type: 'decision',
        input_summary: `succession ${input.from_citizen_id} -> ${input.to_citizen_id}: ${input.reason}`,
        output_summary: `transferred roles: ${transferred.join(', ') || 'none'}`,
        confidence_score: 1,
        risk_level: 'high',
        human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return { id: successionId, transferred_roles: transferred };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // -------------------------------------------------------------------------
  // Protected-execution gate (wired into work gateways)
  // -------------------------------------------------------------------------

  /**
   * Assert that the given actor/agent may execute protected civilization
   * work. Fail-closed on suspended/restricted/expelled/retired citizens.
   * Registry agents and registered autonomy specialist roles are auto-enrolled
   * as active citizens on first use (recorded enrollment), so pre-citizenship
   * flows keep working while state becomes real and suspendable.
   */
  async assertProtectedExecutionAllowed(input: {
    actor_id?: string;
    agent_key?: string;
    specialist_role?: string;
    domain?: string;
    risk_level?: RiskLevel;
  }): Promise<CitizenRecord> {
    const risk: RiskLevel = input.risk_level ?? 'low';
    let citizen: CitizenRecord | null = null;

    if (input.actor_id) {
      citizen = await this.getCitizenByActor(input.actor_id);
    } else if (input.agent_key) {
      citizen = await this.getCitizenByAgentKey(input.agent_key);
      if (!citizen) citizen = await this.autoEnrollRegistryAgent(input.agent_key);
    } else if (input.specialist_role) {
      citizen = await this.autoEnrollSpecialist(input.specialist_role);
    } else {
      throw new PublicHttpError(400, 'actor_id, agent_key, or specialist_role is required');
    }

    if (!citizen) {
      await this.recordExecutionBlocked(input, 'no citizen record and not eligible for enrollment');
      throw new CitizenshipBlockedError('actor is not a registered citizen of the civilization');
    }

    if (!EXECUTABLE_STATUSES.includes(citizen.status)) {
      await this.recordExecutionBlocked(input, `citizen status is ${citizen.status}`);
      throw new CitizenshipBlockedError(`citizen is ${citizen.status}; protected execution is blocked`);
    }

    if (citizen.status === 'probationary' && RISK_RANK[risk] > RISK_RANK.low) {
      await this.recordExecutionBlocked(input, `probationary citizen attempted ${risk} risk work`);
      throw new CitizenshipBlockedError('probationary citizens may only execute low-risk work');
    }

    if (input.domain) {
      const envelope = await db.query<{ max_risk_level: RiskLevel }>(
        `SELECT max_risk_level FROM citizen_autonomy_envelopes
          WHERE citizen_id = $1 AND domain = $2 AND status = 'active' LIMIT 1`,
        [citizen.id, input.domain]
      );
      const maxRisk: RiskLevel = envelope.rows[0]?.max_risk_level ?? 'medium';
      if (RISK_RANK[risk] > RISK_RANK[maxRisk]) {
        await this.recordExecutionBlocked(input, `risk ${risk} exceeds ${input.domain} envelope ${maxRisk}`);
        throw new CitizenshipBlockedError(
          `risk ${risk} exceeds the citizen's autonomy envelope (${maxRisk}) for domain ${input.domain}`
        );
      }
    }

    return citizen;
  }

  /**
   * Budget multiplier for a citizen in a domain: envelope multiplier × trust
   * modifier from the latest (subject, domain) trust window. Unknown trust
   * keeps 1.0; low or force-downgraded trust constrains the budget.
   */
  async budgetMultiplierFor(input: { agent_key?: string; actor_id?: string; specialist_role?: string; domain?: string }): Promise<number> {
    const subjectKeys: string[] = [];
    let citizen: CitizenRecord | null = null;
    if (input.agent_key) {
      subjectKeys.push(input.agent_key);
      citizen = await this.getCitizenByAgentKey(input.agent_key);
    }
    if (input.specialist_role) {
      subjectKeys.push(`autonomy-specialist:${input.specialist_role}`, input.specialist_role);
      citizen = citizen ?? await this.getCitizenByActorName(`autonomy-specialist:${input.specialist_role}`);
    }
    if (input.actor_id) {
      subjectKeys.push(input.actor_id);
      citizen = citizen ?? await this.getCitizenByActor(input.actor_id);
    }

    let envelopeMultiplier = 1.0;
    if (citizen && input.domain) {
      const envelope = await db.query<{ budget_multiplier: string | number }>(
        `SELECT budget_multiplier FROM citizen_autonomy_envelopes
          WHERE citizen_id = $1 AND domain = $2 AND status = 'active' LIMIT 1`,
        [citizen.id, input.domain]
      );
      if (envelope.rows[0]) envelopeMultiplier = Number(envelope.rows[0].budget_multiplier);
    }

    let trustModifier = 1.0;
    if (subjectKeys.length > 0) {
      const trust = await db.query<{ trust_factor: string | number; force_downgrade: boolean }>(
        `SELECT trust_factor, force_downgrade FROM trust_scores
          WHERE subject_id = ANY($1::text[]) AND ($2::text IS NULL OR domain = $2)
          ORDER BY window_end DESC, created_at DESC LIMIT 1`,
        [subjectKeys, input.domain ?? null]
      );
      if (trust.rows[0]) {
        if (trust.rows[0].force_downgrade) trustModifier = 0.25;
        else {
          const factor = Number(trust.rows[0].trust_factor);
          trustModifier = factor >= 0.75 ? 1.0 : factor >= 0.5 ? 0.75 : 0.5;
        }
      }
    }

    const combined = envelopeMultiplier * trustModifier;
    return Math.min(2.0, Math.max(0.1, combined));
  }

  private async getCitizenByActorName(name: string): Promise<CitizenRecord | null> {
    const result = await db.query<CitizenRecord>(
      `SELECT ${CITIZEN_COLUMNS.split(', ').map(c => 'c.' + c).join(', ')}
         FROM citizens c JOIN actors a ON a.id = c.actor_id
        WHERE a.name = $1 AND a.status = 'active'
        LIMIT 1`,
      [name]
    );
    return result.rows[0] ?? null;
  }

  private async autoEnrollRegistryAgent(agentKey: string): Promise<CitizenRecord | null> {
    const entry = getAgentRegistryEntry(agentKey);
    if (!entry) return null;
    await civilizationKernel.ensureCivilizationRoot();
    const actor = await db.query<{ id: string }>(
      `SELECT a.id FROM actors a
        JOIN agent_identities ai ON ai.actor_id = a.id
       WHERE ai.agent_key = $1 LIMIT 1`,
      [agentKey]
    );
    let actorId = actor.rows[0]?.id;
    if (!actorId) {
      const inserted = await db.query<{ id: string }>(
        `INSERT INTO actors (actor_type, name, metadata_json)
         VALUES ('agent',$1,'{}'::jsonb)
         ON CONFLICT (actor_type, name) WHERE status = 'active'
         DO UPDATE SET updated_at = actors.updated_at
         RETURNING id`,
        [agentKey]
      );
      actorId = inserted.rows[0].id;
      await db.query(
        `INSERT INTO agent_identities (actor_id, agent_key, model_name, version, status)
         VALUES ($1,$2,'unknown','citizenship-bootstrap','active')
         ON CONFLICT (agent_key) DO NOTHING`,
        [actorId, agentKey]
      );
    }
    return this.registerCitizen({
      actor_id: actorId,
      citizen_type: 'agent',
      display_name: agentKey,
      initial_status: 'active',
      enrollment_reason: 'bootstrap enrollment from agent registry',
    });
  }

  private async autoEnrollSpecialist(role: string): Promise<CitizenRecord | null> {
    await civilizationKernel.ensureCivilizationRoot();
    const name = `autonomy-specialist:${role}`;
    const existing = await this.getCitizenByActorName(name);
    if (existing) return existing;
    const actor = await db.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ specialist_role: role })]
    );
    return this.registerCitizen({
      actor_id: actor.rows[0].id,
      citizen_type: 'service',
      display_name: name,
      initial_status: 'active',
      enrollment_reason: 'bootstrap enrollment from specialist role registry',
    });
  }

  private async recordExecutionBlocked(
    input: { actor_id?: string; agent_key?: string; specialist_role?: string; domain?: string; risk_level?: RiskLevel },
    reason: string
  ): Promise<void> {
    try {
      const client = await db.connect();
      try {
        await client.query('BEGIN');
        const serviceActor = await client.query<{ id: string }>(
          `INSERT INTO actors (actor_type, name, metadata_json)
           VALUES ('service','agentco-citizenship-gate','{}'::jsonb)
           ON CONFLICT (actor_type, name) WHERE status = 'active'
           DO UPDATE SET updated_at = actors.updated_at
           RETURNING id`
        );
        await eventLog.appendWithClient(client, {
          event_type: 'citizenship.execution_blocked',
          actor_id: serviceActor.rows[0].id,
          object_type: 'citizenship_gate',
          object_id: crypto.randomUUID(),
          correlation_id: crypto.randomUUID(),
          payload: {
            actor_id: input.actor_id ?? null,
            agent_key: input.agent_key ?? null,
            specialist_role: input.specialist_role ?? null,
            domain: input.domain ?? null,
            risk_level: input.risk_level ?? 'low',
            reason,
          },
        });
        await client.query('COMMIT');
      } catch {
        await client.query('ROLLBACK');
      } finally {
        client.release();
      }
    } catch {
      // Denial recording is best-effort; the denial itself still throws.
    }
  }
}

export const citizenshipService = new CitizenshipService();
