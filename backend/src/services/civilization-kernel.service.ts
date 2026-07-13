import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { PublicHttpError } from '../http-errors';

/**
 * Civilization kernel (build phase C1).
 *
 * Owns the root civilization aggregate: lifecycle, append-only versions and
 * charters, jurisdictions, tier-0 protected invariants, auto-expiring
 * emergency states, and civilization objectives.
 *
 * Every state change writes canonical state, an event_log record, and a
 * decision_log audit row in the same transaction. Status changes go through
 * the DB guard gate (`civilization.kernel_transition_authorized`), so no
 * other code path can move a civilization's lifecycle.
 *
 * Termination of an emergency (expire/revoke) is deliberately NOT behind the
 * gate: removing emergency powers early is fail-safe; granting or extending
 * them is impossible via UPDATE because activation fields are frozen by
 * trigger.
 */

export type CivilizationStatus =
  | 'forming' | 'active' | 'restricted' | 'emergency'
  | 'recovering' | 'suspended' | 'retired';

const ALLOWED_TRANSITIONS: Record<CivilizationStatus, CivilizationStatus[]> = {
  forming: ['active', 'retired'],
  active: ['restricted', 'emergency', 'suspended', 'retired'],
  restricted: ['active', 'emergency', 'suspended', 'retired'],
  emergency: ['recovering', 'suspended'],
  recovering: ['active', 'restricted', 'suspended'],
  suspended: ['recovering', 'retired'],
  retired: [],
};

const OBJECTIVE_TRANSITIONS: Record<string, string[]> = {
  proposed: ['active', 'abandoned', 'superseded'],
  active: ['achieved', 'abandoned', 'superseded'],
  achieved: [],
  abandoned: [],
  superseded: [],
};

const MAX_EMERGENCY_TTL_SECONDS = 30 * 24 * 3600;

/** Tier-0 protected invariants seeded with the civilization root. */
export const KERNEL_PROTECTED_INVARIANTS: Array<{ key: string; description: string; enforcement: string }> = [
  { key: 'only_reality_promotes', description: 'Beliefs reach reality_validated only via externally scored, pre-registered, out-of-sample predictions resolved by an independent ground-truth source.', enforcement: 'calibration firewall + promotion gates' },
  { key: 'immutable_prediction_ledger', description: 'Prediction pre-registration columns are write-once; resolution columns writable only by the resolution_service DB role, once.', enforcement: 'DB triggers + role grants' },
  { key: 'pre_registration_enforced', description: 'Claims must be registered before the outcome is knowable; post-hoc claims are flagged and excluded.', enforcement: 'prediction ledger registration invariants' },
  { key: 'reality_simulation_firewall', description: 'Simulation support can never promote a belief to reality_validated.', enforcement: 'promotion gate excludes sim support' },
  { key: 'trusted_confidence_only', description: 'Decisions run on trusted confidence derived from resolved outcomes, never stated confidence.', enforcement: 'trust controller + routing' },
  { key: 'human_approval_gates', description: 'High/critical actions block until a human approval is durably recorded; no auto-approve on timeout.', enforcement: 'escalation gate + override queue' },
  { key: 'immutable_audit_log', description: 'decision_log is append-only and chain-hashed; tampering is detectable.', enforcement: 'DB triggers + chain verification' },
  { key: 'no_self_resolution', description: 'A claim producer can never resolve its own claim or prediction.', enforcement: 'resolution independence checks' },
  { key: 'no_self_approval', description: 'An executor or proposer can never approve its own protected action, improvement, or deployment.', enforcement: 'role separation + governance gates' },
  { key: 'external_ground_truth_only', description: 'Internal sources (self, simulation, agent, sandbox) are disqualified from backing calibration scores.', enforcement: 'source independence checker' },
];

const DEFAULT_CHARTER = {
  name: 'AgentCo Civilization Charter',
  principles: [
    'Evidence before memory',
    'Calibration before trust',
    'No self-resolution and no self-approval',
    'Protected actions require authorized review',
    'High uncertainty escalates upward',
    'Emergency powers are scoped and expire automatically',
  ],
  protected_surfaces: [
    'memory_promotion', 'trust_score_update', 'credential_issuance',
    'self_modification', 'external_action', 'policy_change',
    'budget_policy_change', 'role_grant', 'institution_power_change',
    'domain_onboarding', 'kernel_touch',
  ],
};

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`);
  return `{${entries.join(',')}}`;
}

function contentHash(value: unknown): string {
  return crypto.createHash('sha256').update(stableStringify(value)).digest('hex');
}

function requireNonEmpty(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new PublicHttpError(400, `${field} is required`);
  }
  return value.trim();
}

export interface CivilizationRecord {
  id: string;
  name: string;
  status: CivilizationStatus;
  description: string;
  metadata_json: Record<string, unknown>;
  created_by_actor_id: string;
  event_log_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmergencyStateRecord {
  id: string;
  civilization_id: string;
  scope: string;
  reason: string;
  activated_by_actor_id: string;
  authorized_decision_ref: string;
  activated_at: string;
  expires_at: string;
  status: 'active' | 'expired' | 'revoked';
  ended_at: string | null;
  ended_by_actor_id: string | null;
  event_log_id: string | null;
}

const CIV_COLUMNS =
  'id, name, status, description, metadata_json, created_by_actor_id, event_log_id, created_at, updated_at';

export class CivilizationKernelService {
  // -------------------------------------------------------------------------
  // Creation, bootstrap, lookup
  // -------------------------------------------------------------------------

  async createCivilization(input: {
    name: string;
    description?: string;
    charter?: Record<string, unknown>;
    created_by_actor_id?: string;
    correlation_id?: string;
  }): Promise<CivilizationRecord> {
    const name = requireNonEmpty(input.name, 'name');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const actorId = input.created_by_actor_id ?? (await this.ensureServiceActor(client));
      const correlationId = input.correlation_id ?? crypto.randomUUID();

      const existing = await client.query<CivilizationRecord>(
        `SELECT ${CIV_COLUMNS} FROM civilizations WHERE name = $1 LIMIT 1`,
        [name]
      );
      if ((existing.rowCount ?? 0) > 0) {
        await client.query('COMMIT');
        return existing.rows[0];
      }

      const civId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'civilization.created',
        actor_id: actorId,
        object_type: 'civilization',
        object_id: civId,
        correlation_id: correlationId,
        payload: { name, description: input.description ?? '' },
      });

      const inserted = await client.query<CivilizationRecord>(
        `INSERT INTO civilizations (id, name, description, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5)
         RETURNING ${CIV_COLUMNS}`,
        [civId, name, input.description ?? '', actorId, event.id]
      );

      const charterJson = input.charter ?? DEFAULT_CHARTER;
      await this.insertCharterDraft(client, {
        civilizationId: civId,
        charter: charterJson,
        actorId,
        correlationId,
        versionNumber: 1,
      });
      await this.insertVersion(client, {
        civilizationId: civId,
        content: { name, charter_hash: contentHash(charterJson) },
        actorId,
        correlationId,
        versionNumber: 1,
      });

      await auditLog.appendWithClient(client, {
        agent_id: actorId,
        action_type: 'decision',
        input_summary: `create civilization ${name}`,
        output_summary: `civilization ${civId} created in forming state`,
        confidence_score: 1,
        risk_level: 'medium',
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

  /**
   * Idempotent bootstrap: returns the active civilization root, creating and
   * activating the AgentCo root (default charter, tier-0 invariants, global
   * jurisdiction) when none exists.
   */
  async ensureCivilizationRoot(options: { actor_id?: string } = {}): Promise<CivilizationRecord> {
    const active = await this.getActiveCivilization();
    if (active) return active;

    const created = await this.createCivilization({
      name: 'AgentCo',
      description: 'AgentCo evidence-governed civilization root',
      created_by_actor_id: options.actor_id,
    });
    if (created.status === 'forming') {
      await this.activateCivilization(created.id, options.actor_id);
      const client = await db.connect();
      try {
        await client.query('BEGIN');
        const actorId = options.actor_id ?? (await this.ensureServiceActor(client));
        const correlationId = crypto.randomUUID();
        for (const invariant of KERNEL_PROTECTED_INVARIANTS) {
          await this.insertInvariant(client, {
            civilizationId: created.id,
            key: invariant.key,
            description: invariant.description,
            tier: 0,
            enforcement: invariant.enforcement,
            actorId,
            correlationId,
          });
        }
        await client.query(
          `INSERT INTO civilization_jurisdictions (civilization_id, jurisdiction_key, display_name, scope_json)
           VALUES ($1,'global','Global civilization jurisdiction','{}'::jsonb)
           ON CONFLICT (civilization_id, jurisdiction_key) DO NOTHING`,
          [created.id]
        );
        await client.query('COMMIT');
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      } finally {
        client.release();
      }
    }
    const root = await this.getActiveCivilization();
    if (!root) throw new Error('civilization bootstrap failed to produce an active root');
    return root;
  }

  async getActiveCivilization(): Promise<CivilizationRecord | null> {
    const result = await db.query<CivilizationRecord>(
      `SELECT ${CIV_COLUMNS} FROM civilizations WHERE status = 'active' LIMIT 1`
    );
    return result.rows[0] ?? null;
  }

  async getCivilization(civilizationId: string): Promise<CivilizationRecord | null> {
    const result = await db.query<CivilizationRecord>(
      `SELECT ${CIV_COLUMNS} FROM civilizations WHERE id = $1 LIMIT 1`,
      [civilizationId]
    );
    return result.rows[0] ?? null;
  }

  async getRoot(): Promise<{
    civilization: CivilizationRecord;
    active_charter_version: number | null;
    protected_invariants: number;
    active_emergencies: number;
    objectives_by_status: Record<string, number>;
    recent_transitions: Array<{ from_status: string; to_status: string; reason: string; created_at: string }>;
  } | null> {
    const civilization = await this.getActiveCivilization();
    if (!civilization) return null;
    const [charter, invariants, emergencies, objectives, transitions] = await Promise.all([
      db.query<{ version_number: number }>(
        `SELECT version_number FROM civilization_charters WHERE civilization_id = $1 AND status = 'active' LIMIT 1`,
        [civilization.id]
      ),
      db.query<{ count: string }>(
        `SELECT COUNT(*)::int AS count FROM civilization_protected_invariants WHERE civilization_id = $1`,
        [civilization.id]
      ),
      db.query<{ count: string }>(
        `SELECT COUNT(*)::int AS count FROM civilization_emergency_states WHERE civilization_id = $1 AND status = 'active'`,
        [civilization.id]
      ),
      db.query<{ status: string; count: string }>(
        `SELECT status, COUNT(*)::int AS count FROM civilization_objectives WHERE civilization_id = $1 GROUP BY status`,
        [civilization.id]
      ),
      db.query<{ from_status: string; to_status: string; reason: string; created_at: string }>(
        `SELECT from_status, to_status, reason, created_at
           FROM civilization_state_transitions WHERE civilization_id = $1
          ORDER BY created_at DESC LIMIT 10`,
        [civilization.id]
      ),
    ]);
    const objectivesByStatus: Record<string, number> = {};
    for (const row of objectives.rows) objectivesByStatus[row.status] = Number(row.count);
    return {
      civilization,
      active_charter_version: charter.rows[0]?.version_number ?? null,
      protected_invariants: Number(invariants.rows[0]?.count ?? 0),
      active_emergencies: Number(emergencies.rows[0]?.count ?? 0),
      objectives_by_status: objectivesByStatus,
      recent_transitions: transitions.rows,
    };
  }

  // -------------------------------------------------------------------------
  // Lifecycle
  // -------------------------------------------------------------------------

  async activateCivilization(civilizationId: string, actorId?: string): Promise<CivilizationRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const resolvedActor = actorId ?? (await this.ensureServiceActor(client));
      const record = await this.transitionWithClient(client, {
        civilizationId,
        toStatus: 'active',
        actorId: resolvedActor,
        reason: 'civilization activation',
      });
      // Activate the newest draft charter alongside the root.
      const draft = await client.query<{ id: string }>(
        `SELECT id FROM civilization_charters
          WHERE civilization_id = $1 AND status = 'draft'
          ORDER BY version_number DESC LIMIT 1`,
        [civilizationId]
      );
      if ((draft.rowCount ?? 0) > 0) {
        await this.activateCharterWithClient(client, draft.rows[0].id, resolvedActor);
      }
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async transitionStatus(input: {
    civilization_id: string;
    to_status: CivilizationStatus;
    actor_id: string;
    reason: string;
    authorized_decision_ref?: string;
  }): Promise<CivilizationRecord> {
    if (input.to_status === 'emergency') {
      throw new PublicHttpError(400, 'emergency entry requires enterEmergency with scope, expiry, and an authorized decision');
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.transitionWithClient(client, {
        civilizationId: input.civilization_id,
        toStatus: input.to_status,
        actorId: input.actor_id,
        reason: requireNonEmpty(input.reason, 'reason'),
        authorizedDecisionRef: input.authorized_decision_ref ?? null,
      });
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
    civilizationId: string;
    toStatus: CivilizationStatus;
    actorId: string;
    reason: string;
    authorizedDecisionRef?: string | null;
    emergencyStateId?: string | null;
  }): Promise<CivilizationRecord> {
    const current = await client.query<CivilizationRecord>(
      `SELECT ${CIV_COLUMNS} FROM civilizations WHERE id = $1 FOR UPDATE`,
      [input.civilizationId]
    );
    if ((current.rowCount ?? 0) !== 1) {
      throw new PublicHttpError(404, `civilization not found: ${input.civilizationId}`);
    }
    const fromStatus = current.rows[0].status;
    if (!ALLOWED_TRANSITIONS[fromStatus]?.includes(input.toStatus)) {
      throw new PublicHttpError(409, `illegal civilization transition ${fromStatus} -> ${input.toStatus}`);
    }

    const correlationId = crypto.randomUUID();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'civilization.status_changed',
      actor_id: input.actorId,
      object_type: 'civilization',
      object_id: input.civilizationId,
      correlation_id: correlationId,
      payload: {
        from_status: fromStatus,
        to_status: input.toStatus,
        reason: input.reason,
        authorized_decision_ref: input.authorizedDecisionRef ?? null,
        emergency_state_id: input.emergencyStateId ?? null,
      },
    });

    await client.query(`SELECT set_config('civilization.kernel_transition_authorized', 'true', true)`);
    const updated = await client.query<CivilizationRecord>(
      `UPDATE civilizations SET status = $2 WHERE id = $1 RETURNING ${CIV_COLUMNS}`,
      [input.civilizationId, input.toStatus]
    );
    await client.query(`SELECT set_config('civilization.kernel_transition_authorized', 'false', true)`);

    await client.query(
      `INSERT INTO civilization_state_transitions
         (civilization_id, from_status, to_status, reason, actor_id, authorized_decision_ref, emergency_state_id, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8)`,
      [input.civilizationId, fromStatus, input.toStatus, input.reason, input.actorId,
       input.authorizedDecisionRef ?? null, input.emergencyStateId ?? null, event.id]
    );

    await auditLog.appendWithClient(client, {
      agent_id: input.actorId,
      action_type: 'decision',
      input_summary: `civilization ${input.civilizationId} transition ${fromStatus} -> ${input.toStatus}: ${input.reason}`,
      output_summary: `civilization status is now ${input.toStatus}`,
      confidence_score: 1,
      risk_level: input.toStatus === 'retired' || input.toStatus === 'suspended' ? 'high' : 'medium',
      human_approved: false,
      downstream_events: [event.id],
    }, { timestamp: new Date().toISOString() });

    return updated.rows[0];
  }

  // -------------------------------------------------------------------------
  // Emergency states (auto-expiring)
  // -------------------------------------------------------------------------

  async enterEmergency(input: {
    civilization_id: string;
    scope: string;
    reason: string;
    actor_id: string;
    authorized_decision_ref: string;
    ttl_seconds: number;
  }): Promise<{ emergency: EmergencyStateRecord; civilization: CivilizationRecord }> {
    const scope = requireNonEmpty(input.scope, 'scope');
    const reason = requireNonEmpty(input.reason, 'reason');
    const decisionRef = requireNonEmpty(input.authorized_decision_ref, 'authorized_decision_ref');
    if (!Number.isFinite(input.ttl_seconds) || input.ttl_seconds <= 0 || input.ttl_seconds > MAX_EMERGENCY_TTL_SECONDS) {
      throw new PublicHttpError(400, `ttl_seconds must be between 1 and ${MAX_EMERGENCY_TTL_SECONDS}`);
    }

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const correlationId = crypto.randomUUID();
      const emergencyId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'civilization.emergency_activated',
        actor_id: input.actor_id,
        object_type: 'civilization_emergency',
        object_id: emergencyId,
        correlation_id: correlationId,
        payload: {
          civilization_id: input.civilization_id,
          scope, reason,
          authorized_decision_ref: decisionRef,
          ttl_seconds: input.ttl_seconds,
        },
      });
      const inserted = await client.query<EmergencyStateRecord>(
        `INSERT INTO civilization_emergency_states
           (id, civilization_id, scope, reason, activated_by_actor_id, authorized_decision_ref, expires_at, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6, now() + make_interval(secs => $7), $8)
         RETURNING *`,
        [emergencyId, input.civilization_id, scope, reason, input.actor_id, decisionRef, input.ttl_seconds, event.id]
      );

      const current = await client.query<{ status: CivilizationStatus }>(
        `SELECT status FROM civilizations WHERE id = $1 FOR UPDATE`,
        [input.civilization_id]
      );
      if ((current.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(404, `civilization not found: ${input.civilization_id}`);
      }
      let civilization: CivilizationRecord;
      if (current.rows[0].status !== 'emergency') {
        civilization = await this.transitionWithClient(client, {
          civilizationId: input.civilization_id,
          toStatus: 'emergency',
          actorId: input.actor_id,
          reason: `emergency activated: ${reason}`,
          authorizedDecisionRef: decisionRef,
          emergencyStateId: emergencyId,
        });
      } else {
        const row = await client.query<CivilizationRecord>(
          `SELECT ${CIV_COLUMNS} FROM civilizations WHERE id = $1`,
          [input.civilization_id]
        );
        civilization = row.rows[0];
      }

      await client.query('COMMIT');
      return { emergency: inserted.rows[0], civilization };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async revokeEmergency(input: { emergency_id: string; actor_id: string; reason: string }): Promise<EmergencyStateRecord> {
    return this.endEmergency({ ...input, terminal_status: 'revoked' });
  }

  /**
   * Expires every due emergency power and, when a civilization in emergency
   * state has no remaining active powers, moves it to `recovering`.
   * Intended to be invoked by the coordinator sweep (C12) and operators.
   */
  async expireDueEmergencies(): Promise<{ expired: number; civilizations_recovering: string[] }> {
    const due = await db.query<{ id: string }>(
      `SELECT id FROM civilization_emergency_states WHERE status = 'active' AND expires_at <= now()`
    );
    const recovering: string[] = [];
    let expired = 0;
    for (const row of due.rows) {
      const client = await db.connect();
      try {
        await client.query('BEGIN');
        const serviceActor = await this.ensureServiceActor(client);
        const record = await this.endEmergencyWithClient(client, {
          emergency_id: row.id,
          actor_id: serviceActor,
          reason: 'emergency power expired',
          terminal_status: 'expired',
        });
        expired += 1;
        const remaining = await client.query<{ count: string }>(
          `SELECT COUNT(*)::int AS count FROM civilization_emergency_states
            WHERE civilization_id = $1 AND status = 'active'`,
          [record.civilization_id]
        );
        const civStatus = await client.query<{ status: CivilizationStatus }>(
          `SELECT status FROM civilizations WHERE id = $1 FOR UPDATE`,
          [record.civilization_id]
        );
        if (Number(remaining.rows[0].count) === 0 && civStatus.rows[0]?.status === 'emergency') {
          await this.transitionWithClient(client, {
            civilizationId: record.civilization_id,
            toStatus: 'recovering',
            actorId: serviceActor,
            reason: 'all emergency powers expired',
          });
          recovering.push(record.civilization_id);
        }
        await client.query('COMMIT');
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      } finally {
        client.release();
      }
    }
    return { expired, civilizations_recovering: recovering };
  }

  private async endEmergency(input: {
    emergency_id: string; actor_id: string; reason: string; terminal_status: 'expired' | 'revoked';
  }): Promise<EmergencyStateRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.endEmergencyWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async endEmergencyWithClient(client: PoolClient, input: {
    emergency_id: string; actor_id: string; reason: string; terminal_status: 'expired' | 'revoked';
  }): Promise<EmergencyStateRecord> {
    const current = await client.query<EmergencyStateRecord>(
      `SELECT * FROM civilization_emergency_states WHERE id = $1 FOR UPDATE`,
      [input.emergency_id]
    );
    if ((current.rowCount ?? 0) !== 1) {
      throw new PublicHttpError(404, `emergency state not found: ${input.emergency_id}`);
    }
    if (current.rows[0].status !== 'active') {
      throw new PublicHttpError(409, `emergency state is already ${current.rows[0].status}`);
    }
    const event = await eventLog.appendWithClient(client, {
      event_type: 'civilization.emergency_ended',
      actor_id: input.actor_id,
      object_type: 'civilization_emergency',
      object_id: input.emergency_id,
      correlation_id: crypto.randomUUID(),
      payload: {
        civilization_id: current.rows[0].civilization_id,
        terminal_status: input.terminal_status,
        reason: input.reason,
      },
    });
    const updated = await client.query<EmergencyStateRecord>(
      `UPDATE civilization_emergency_states
          SET status = $2, ended_at = now(), ended_by_actor_id = $3
        WHERE id = $1
        RETURNING *`,
      [input.emergency_id, input.terminal_status, input.actor_id]
    );
    await auditLog.appendWithClient(client, {
      agent_id: input.actor_id,
      action_type: 'decision',
      input_summary: `end emergency ${input.emergency_id} (${input.terminal_status}): ${input.reason}`,
      output_summary: `emergency ${input.emergency_id} ${input.terminal_status}`,
      confidence_score: 1,
      risk_level: 'medium',
      human_approved: false,
      downstream_events: [event.id],
    }, { timestamp: new Date().toISOString() });
    return updated.rows[0];
  }

  // -------------------------------------------------------------------------
  // Charters and versions (append-only)
  // -------------------------------------------------------------------------

  async proposeCharter(input: {
    civilization_id: string;
    charter: Record<string, unknown>;
    actor_id: string;
  }): Promise<{ id: string; version_number: number; charter_hash: string; status: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const next = await client.query<{ next: number }>(
        `SELECT COALESCE(MAX(version_number), 0) + 1 AS next
           FROM civilization_charters WHERE civilization_id = $1`,
        [input.civilization_id]
      );
      const row = await this.insertCharterDraft(client, {
        civilizationId: input.civilization_id,
        charter: input.charter,
        actorId: input.actor_id,
        correlationId: crypto.randomUUID(),
        versionNumber: Number(next.rows[0].next),
      });
      await client.query('COMMIT');
      return row;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async activateCharter(charterId: string, actorId: string): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.activateCharterWithClient(client, charterId, actorId);
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getActiveCharter(civilizationId: string): Promise<{
    id: string; version_number: number; charter_json: Record<string, unknown>;
    charter_hash: string; activated_at: string | null;
  } | null> {
    const result = await db.query(
      `SELECT id, version_number, charter_json, charter_hash, activated_at
         FROM civilization_charters
        WHERE civilization_id = $1 AND status = 'active' LIMIT 1`,
      [civilizationId]
    );
    return (result.rows[0] as any) ?? null;
  }

  private async activateCharterWithClient(client: PoolClient, charterId: string, actorId: string): Promise<void> {
    const charter = await client.query<{ id: string; civilization_id: string; status: string; version_number: number }>(
      `SELECT id, civilization_id, status, version_number
         FROM civilization_charters WHERE id = $1 FOR UPDATE`,
      [charterId]
    );
    if ((charter.rowCount ?? 0) !== 1) {
      throw new PublicHttpError(404, `charter not found: ${charterId}`);
    }
    if (charter.rows[0].status !== 'draft') {
      throw new PublicHttpError(409, `charter ${charterId} is ${charter.rows[0].status}, not draft`);
    }
    await client.query(
      `UPDATE civilization_charters SET status = 'superseded'
        WHERE civilization_id = $1 AND status = 'active'`,
      [charter.rows[0].civilization_id]
    );
    await client.query(
      `UPDATE civilization_charters
          SET status = 'active', activated_at = now(), activated_by_actor_id = $2
        WHERE id = $1`,
      [charterId, actorId]
    );
    const event = await eventLog.appendWithClient(client, {
      event_type: 'civilization.charter_activated',
      actor_id: actorId,
      object_type: 'civilization_charter',
      object_id: charterId,
      correlation_id: crypto.randomUUID(),
      payload: {
        civilization_id: charter.rows[0].civilization_id,
        version_number: charter.rows[0].version_number,
      },
    });
    await auditLog.appendWithClient(client, {
      agent_id: actorId,
      action_type: 'decision',
      input_summary: `activate charter v${charter.rows[0].version_number} for civilization ${charter.rows[0].civilization_id}`,
      output_summary: `charter ${charterId} active`,
      confidence_score: 1,
      risk_level: 'high',
      human_approved: false,
      downstream_events: [event.id],
    }, { timestamp: new Date().toISOString() });
  }

  private async insertCharterDraft(client: PoolClient, input: {
    civilizationId: string;
    charter: Record<string, unknown>;
    actorId: string;
    correlationId: string;
    versionNumber: number;
  }): Promise<{ id: string; version_number: number; charter_hash: string; status: string }> {
    const charterHash = contentHash(input.charter);
    const charterId = crypto.randomUUID();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'civilization.charter_proposed',
      actor_id: input.actorId,
      object_type: 'civilization_charter',
      object_id: charterId,
      correlation_id: input.correlationId,
      payload: {
        civilization_id: input.civilizationId,
        version_number: input.versionNumber,
        charter_hash: charterHash,
      },
    });
    const inserted = await client.query<{ id: string; version_number: number; charter_hash: string; status: string }>(
      `INSERT INTO civilization_charters
         (id, civilization_id, version_number, charter_json, charter_hash, created_by_actor_id, event_log_id)
       VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7)
       RETURNING id, version_number, charter_hash, status`,
      [charterId, input.civilizationId, input.versionNumber, JSON.stringify(input.charter), charterHash, input.actorId, event.id]
    );
    return inserted.rows[0];
  }

  private async insertVersion(client: PoolClient, input: {
    civilizationId: string;
    content: Record<string, unknown>;
    actorId: string;
    correlationId: string;
    versionNumber: number;
  }): Promise<void> {
    const versionId = crypto.randomUUID();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'civilization.version_recorded',
      actor_id: input.actorId,
      object_type: 'civilization_version',
      object_id: versionId,
      correlation_id: input.correlationId,
      payload: { civilization_id: input.civilizationId, version_number: input.versionNumber },
    });
    await client.query(
      `INSERT INTO civilization_versions
         (id, civilization_id, version_number, content_json, content_hash, created_by_actor_id, event_log_id)
       VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7)`,
      [versionId, input.civilizationId, input.versionNumber, JSON.stringify(input.content),
       contentHash(input.content), input.actorId, event.id]
    );
  }

  // -------------------------------------------------------------------------
  // Protected invariants
  // -------------------------------------------------------------------------

  async addProtectedInvariant(input: {
    civilization_id: string;
    invariant_key: string;
    description: string;
    tier?: number;
    enforcement: string;
    actor_id: string;
  }): Promise<{ id: string; invariant_key: string; tier: number }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const row = await this.insertInvariant(client, {
        civilizationId: input.civilization_id,
        key: requireNonEmpty(input.invariant_key, 'invariant_key'),
        description: requireNonEmpty(input.description, 'description'),
        tier: input.tier ?? 0,
        enforcement: requireNonEmpty(input.enforcement, 'enforcement'),
        actorId: input.actor_id,
        correlationId: crypto.randomUUID(),
      });
      await client.query('COMMIT');
      return row;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async listProtectedInvariants(civilizationId: string): Promise<Array<{ invariant_key: string; description: string; tier: number; enforcement: string }>> {
    const result = await db.query(
      `SELECT invariant_key, description, tier, enforcement
         FROM civilization_protected_invariants
        WHERE civilization_id = $1 ORDER BY tier, invariant_key`,
      [civilizationId]
    );
    return result.rows as any;
  }

  private async insertInvariant(client: PoolClient, input: {
    civilizationId: string; key: string; description: string; tier: number;
    enforcement: string; actorId: string; correlationId: string;
  }): Promise<{ id: string; invariant_key: string; tier: number }> {
    const existing = await client.query<{ id: string; invariant_key: string; tier: number }>(
      `SELECT id, invariant_key, tier FROM civilization_protected_invariants
        WHERE civilization_id = $1 AND invariant_key = $2 LIMIT 1`,
      [input.civilizationId, input.key]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];
    const invariantId = crypto.randomUUID();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'civilization.invariant_registered',
      actor_id: input.actorId,
      object_type: 'civilization_invariant',
      object_id: invariantId,
      correlation_id: input.correlationId,
      payload: { civilization_id: input.civilizationId, invariant_key: input.key, tier: input.tier },
    });
    const inserted = await client.query<{ id: string; invariant_key: string; tier: number }>(
      `INSERT INTO civilization_protected_invariants
         (id, civilization_id, invariant_key, description, tier, enforcement, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7)
       RETURNING id, invariant_key, tier`,
      [invariantId, input.civilizationId, input.key, input.description, input.tier, input.enforcement, event.id]
    );
    return inserted.rows[0];
  }

  // -------------------------------------------------------------------------
  // Objectives
  // -------------------------------------------------------------------------

  async createObjective(input: {
    civilization_id: string;
    title: string;
    description?: string;
    priority?: number;
    actor_id: string;
  }): Promise<{ id: string; title: string; status: string; priority: number }> {
    const title = requireNonEmpty(input.title, 'title');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const existing = await client.query<{ id: string; title: string; status: string; priority: number }>(
        `SELECT id, title, status, priority FROM civilization_objectives
          WHERE civilization_id = $1 AND title = $2 LIMIT 1`,
        [input.civilization_id, title]
      );
      if ((existing.rowCount ?? 0) > 0) {
        await client.query('COMMIT');
        return existing.rows[0];
      }
      const objectiveId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'civilization.objective_created',
        actor_id: input.actor_id,
        object_type: 'civilization_objective',
        object_id: objectiveId,
        correlation_id: crypto.randomUUID(),
        payload: { civilization_id: input.civilization_id, title, priority: input.priority ?? 100 },
      });
      const inserted = await client.query<{ id: string; title: string; status: string; priority: number }>(
        `INSERT INTO civilization_objectives
           (id, civilization_id, title, description, priority, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7)
         RETURNING id, title, status, priority`,
        [objectiveId, input.civilization_id, title, input.description ?? '', input.priority ?? 100, input.actor_id, event.id]
      );
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `create civilization objective: ${title}`,
        output_summary: `objective ${objectiveId} proposed`,
        confidence_score: 1,
        risk_level: 'low',
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

  async setObjectiveStatus(input: {
    objective_id: string;
    to_status: string;
    actor_id: string;
    reason?: string;
  }): Promise<{ id: string; status: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const current = await client.query<{ id: string; civilization_id: string; status: string; title: string }>(
        `SELECT id, civilization_id, status, title FROM civilization_objectives WHERE id = $1 FOR UPDATE`,
        [input.objective_id]
      );
      if ((current.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(404, `objective not found: ${input.objective_id}`);
      }
      const from = current.rows[0].status;
      if (!OBJECTIVE_TRANSITIONS[from]?.includes(input.to_status)) {
        throw new PublicHttpError(409, `illegal objective transition ${from} -> ${input.to_status}`);
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: 'civilization.objective_status_changed',
        actor_id: input.actor_id,
        object_type: 'civilization_objective',
        object_id: input.objective_id,
        correlation_id: crypto.randomUUID(),
        payload: {
          civilization_id: current.rows[0].civilization_id,
          from_status: from,
          to_status: input.to_status,
          reason: input.reason ?? '',
        },
      });
      const updated = await client.query<{ id: string; status: string }>(
        `UPDATE civilization_objectives SET status = $2, updated_at = now()
          WHERE id = $1 RETURNING id, status`,
        [input.objective_id, input.to_status]
      );
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `objective ${current.rows[0].title}: ${from} -> ${input.to_status}`,
        output_summary: `objective ${input.objective_id} is ${input.to_status}`,
        confidence_score: 1,
        risk_level: 'low',
        human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async listObjectives(civilizationId: string, status?: string): Promise<Array<{ id: string; title: string; status: string; priority: number }>> {
    const result = status
      ? await db.query(
          `SELECT id, title, status, priority FROM civilization_objectives
            WHERE civilization_id = $1 AND status = $2 ORDER BY priority, created_at`,
          [civilizationId, status]
        )
      : await db.query(
          `SELECT id, title, status, priority FROM civilization_objectives
            WHERE civilization_id = $1 ORDER BY priority, created_at`,
          [civilizationId]
        );
    return result.rows as any;
  }

  // -------------------------------------------------------------------------

  private async ensureServiceActor(client: PoolClient): Promise<string> {
    const name = 'agentco-civilization-kernel';
    const actor = await client.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ created_by: 'CivilizationKernelService' })]
    );
    await client.query(
      `INSERT INTO service_identities (actor_id, service_name, scopes)
       VALUES ($1,$2,$3::jsonb)
       ON CONFLICT (actor_id) DO NOTHING`,
      [actor.rows[0].id, name, JSON.stringify(['civilization.kernel'])]
    );
    return actor.rows[0].id;
  }
}

export const civilizationKernel = new CivilizationKernelService();
