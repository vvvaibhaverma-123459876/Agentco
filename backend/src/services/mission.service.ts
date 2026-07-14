import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { PublicHttpError } from '../http-errors';

/**
 * Objectives, goals, missions, and work (build phase C5).
 *
 * Hierarchy: civilization objective -> strategic goal -> mission -> workstream
 *            -> task -> action attempt.
 *
 * The mission lifecycle is state-machine enforced. Completion is GATED:
 * `completeMission` refuses while any required workstream is incomplete, the
 * evidence bundle is empty, settlement is unrecorded, or the audit chain has
 * no mission decision rows. The terminal completion writes a full attestation
 * (goal, task graph, actions, evidence, resource use, failures, outcome).
 */

export type MissionStatus =
  | 'proposed' | 'triaged' | 'approved' | 'funded' | 'planned' | 'assigned'
  | 'executing' | 'waiting_for_evidence' | 'waiting_for_review' | 'blocked'
  | 'evaluating' | 'completed' | 'failed' | 'cancelled' | 'escalated'
  | 'settled' | 'archived';

const MISSION_TRANSITIONS: Record<MissionStatus, MissionStatus[]> = {
  proposed: ['triaged', 'cancelled'],
  triaged: ['approved', 'cancelled', 'escalated'],
  approved: ['funded', 'cancelled'],
  funded: ['planned', 'cancelled'],
  planned: ['assigned', 'cancelled'],
  assigned: ['executing', 'cancelled'],
  executing: ['waiting_for_evidence', 'waiting_for_review', 'blocked', 'evaluating', 'failed', 'escalated'],
  waiting_for_evidence: ['executing', 'evaluating', 'blocked', 'failed'],
  waiting_for_review: ['executing', 'evaluating', 'blocked', 'failed'],
  blocked: ['executing', 'failed', 'cancelled', 'escalated'],
  evaluating: ['completed', 'failed', 'waiting_for_evidence', 'escalated'],
  completed: ['settled'],
  failed: ['settled'],
  cancelled: ['archived'],
  escalated: ['executing', 'failed', 'cancelled'],
  settled: ['archived'],
  archived: [],
};

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`);
  return `{${entries.join(',')}}`;
}

export interface MissionRecord {
  id: string;
  civilization_id: string;
  strategic_goal_id: string | null;
  title: string;
  origin: 'internal' | 'external';
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  requires_review: boolean;
  status: MissionStatus;
  lead_institution_id: string | null;
  coalition_id: string | null;
  created_by_actor_id: string;
  created_at: string;
  updated_at: string;
}

const MISSION_COLUMNS =
  'id, civilization_id, strategic_goal_id, title, origin, risk_level, requires_review, status, lead_institution_id, coalition_id, created_by_actor_id, created_at, updated_at';

export class MissionService {
  // -------------------------------------------------------------------------
  // Strategic goals
  // -------------------------------------------------------------------------

  async createStrategicGoal(input: {
    title: string; description?: string; objective_id?: string; society_id?: string;
    priority?: number; actor_id: string; civilization_id?: string;
  }): Promise<{ id: string; title: string; status: string }> {
    if (!input.title || input.title.trim().length === 0) throw new PublicHttpError(400, 'title is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.requireRootId(client));
      const goalId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'strategic_goal.created',
        actor_id: input.actor_id,
        object_type: 'strategic_goal',
        object_id: goalId,
        correlation_id: crypto.randomUUID(),
        payload: { title: input.title.trim(), objective_id: input.objective_id ?? null },
      });
      const inserted = await client.query<{ id: string; title: string; status: string }>(
        `INSERT INTO strategic_goals
           (id, civilization_id, objective_id, society_id, title, description, priority, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
         RETURNING id, title, status`,
        [goalId, civilizationId, input.objective_id ?? null, input.society_id ?? null,
         input.title.trim(), input.description ?? '', input.priority ?? 100, input.actor_id, event.id]
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
  // Missions
  // -------------------------------------------------------------------------

  async createMission(input: {
    title: string;
    description?: string;
    strategic_goal_id?: string;
    origin?: 'internal' | 'external';
    submitted_by?: string;
    lead_institution_id?: string;
    coalition_id?: string;
    risk_level?: 'low' | 'medium' | 'high' | 'critical';
    depends_on_mission_ids?: string[];
    actor_id: string;
    civilization_id?: string;
  }): Promise<MissionRecord> {
    if (!input.title || input.title.trim().length === 0) throw new PublicHttpError(400, 'title is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.requireRootId(client));
      const risk = input.risk_level ?? 'low';
      const requiresReview = risk === 'high' || risk === 'critical';
      const missionId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'mission.created',
        actor_id: input.actor_id,
        object_type: 'mission',
        object_id: missionId,
        correlation_id: crypto.randomUUID(),
        payload: { title: input.title.trim(), origin: input.origin ?? 'internal', risk_level: risk },
      });
      const inserted = await client.query<MissionRecord>(
        `INSERT INTO missions
           (id, civilization_id, strategic_goal_id, title, description, origin, submitted_by,
            lead_institution_id, coalition_id, risk_level, requires_review, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
         RETURNING ${MISSION_COLUMNS}`,
        [missionId, civilizationId, input.strategic_goal_id ?? null, input.title.trim(),
         input.description ?? '', input.origin ?? 'internal', input.submitted_by ?? null,
         input.lead_institution_id ?? null, input.coalition_id ?? null, risk, requiresReview,
         input.actor_id, event.id]
      );

      for (const dep of input.depends_on_mission_ids ?? []) {
        await this.addDependencyWithClient(client, missionId, dep);
      }

      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `create mission ${input.title.trim()} (risk ${risk})`,
        output_summary: `mission ${missionId} proposed`,
        confidence_score: 1,
        risk_level: risk === 'critical' ? 'critical' : risk === 'high' ? 'high' : 'medium',
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

  private async addDependencyWithClient(client: PoolClient, missionId: string, dependsOn: string): Promise<void> {
    if (missionId === dependsOn) throw new PublicHttpError(400, 'a mission cannot depend on itself');
    // Cycle check: dependsOn must not (transitively) depend on missionId.
    const wouldCycle = await client.query<{ cycles: boolean }>(
      `WITH RECURSIVE reach AS (
         SELECT depends_on_mission_id AS m FROM mission_dependencies WHERE mission_id = $1
         UNION
         SELECT d.depends_on_mission_id FROM mission_dependencies d JOIN reach r ON d.mission_id = r.m
       )
       SELECT EXISTS (SELECT 1 FROM reach WHERE m = $2) AS cycles`,
      [dependsOn, missionId]
    );
    if (wouldCycle.rows[0].cycles) {
      throw new PublicHttpError(409, 'mission dependency would create a cycle');
    }
    await client.query(
      `INSERT INTO mission_dependencies (mission_id, depends_on_mission_id)
       VALUES ($1,$2) ON CONFLICT DO NOTHING`,
      [missionId, dependsOn]
    );
  }

  async addDependency(missionId: string, dependsOn: string): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.addDependencyWithClient(client, missionId, dependsOn);
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async transitionMission(input: {
    mission_id: string; to_status: MissionStatus; actor_id: string; reason: string; block_reason?: string;
  }): Promise<MissionRecord> {
    if (input.to_status === 'completed') {
      throw new PublicHttpError(400, 'use completeMission — completion is gated on evidence, settlement, and audit');
    }
    if (input.to_status === 'settled') {
      throw new PublicHttpError(400, 'use settleMission');
    }
    if (!input.reason || input.reason.trim().length === 0) throw new PublicHttpError(400, 'reason is required');
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
    mission_id: string; to_status: MissionStatus; actor_id: string; reason: string; block_reason?: string;
  }): Promise<MissionRecord> {
    const current = await client.query<MissionRecord>(
      `SELECT ${MISSION_COLUMNS} FROM missions WHERE id = $1 FOR UPDATE`,
      [input.mission_id]
    );
    if ((current.rowCount ?? 0) !== 1) throw new PublicHttpError(404, `mission not found: ${input.mission_id}`);
    const from = current.rows[0].status;
    if (!MISSION_TRANSITIONS[from]?.includes(input.to_status)) {
      throw new PublicHttpError(409, `illegal mission transition ${from} -> ${input.to_status}`);
    }
    // Dependencies must be complete/settled before a mission may start executing.
    if (input.to_status === 'executing' || input.to_status === 'assigned') {
      const blocking = await client.query<{ count: string }>(
        `SELECT COUNT(*)::int AS count FROM mission_dependencies d
           JOIN missions m ON m.id = d.depends_on_mission_id
          WHERE d.mission_id = $1 AND m.status NOT IN ('completed','settled','archived')`,
        [input.mission_id]
      );
      if (Number(blocking.rows[0].count) > 0) {
        throw new PublicHttpError(409, 'mission has unfinished dependencies');
      }
    }
    const event = await eventLog.appendWithClient(client, {
      event_type: 'mission.status_changed',
      actor_id: input.actor_id,
      object_type: 'mission',
      object_id: input.mission_id,
      correlation_id: crypto.randomUUID(),
      payload: { from_status: from, to_status: input.to_status, reason: input.reason },
    });
    await client.query(`SELECT set_config('civilization.mission_transition_authorized', 'true', true)`);
    const updated = await client.query<MissionRecord>(
      `UPDATE missions SET status = $2, block_reason = $3 WHERE id = $1 RETURNING ${MISSION_COLUMNS}`,
      [input.mission_id, input.to_status, input.to_status === 'blocked' ? (input.block_reason ?? input.reason) : null]
    );
    await client.query(`SELECT set_config('civilization.mission_transition_authorized', 'false', true)`);
    await client.query(
      `INSERT INTO mission_state_transitions (mission_id, from_status, to_status, reason, actor_id, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6)`,
      [input.mission_id, from, input.to_status, input.reason, input.actor_id, event.id]
    );
    await auditLog.appendWithClient(client, {
      agent_id: input.actor_id,
      action_type: 'decision',
      input_summary: `mission ${input.mission_id} ${from} -> ${input.to_status}: ${input.reason}`,
      output_summary: `mission status is now ${input.to_status}`,
      confidence_score: 1,
      risk_level: ['failed', 'cancelled', 'escalated'].includes(input.to_status) ? 'high' : 'medium',
      human_approved: false,
      downstream_events: [event.id],
    }, { timestamp: new Date().toISOString() });
    return updated.rows[0];
  }

  // -------------------------------------------------------------------------
  // Workstreams / tasks / actions
  // -------------------------------------------------------------------------

  async addWorkstream(input: {
    mission_id: string; title: string; assigned_institution_id?: string; required?: boolean; actor_id: string;
  }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const workstreamId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'workstream.created',
        actor_id: input.actor_id,
        object_type: 'workstream',
        object_id: workstreamId,
        correlation_id: crypto.randomUUID(),
        payload: { mission_id: input.mission_id, title: input.title },
      });
      const inserted = await client.query<{ id: string }>(
        `INSERT INTO workstreams (id, mission_id, title, assigned_institution_id, required, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id`,
        [workstreamId, input.mission_id, input.title, input.assigned_institution_id ?? null,
         input.required ?? true, input.actor_id, event.id]
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

  async addTask(input: {
    workstream_id: string; title: string; agent_id?: string; task_type?: string;
    reversible?: boolean; actor_id: string;
  }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const ws = await client.query<{ mission_id: string }>(
        `SELECT mission_id FROM workstreams WHERE id = $1 LIMIT 1`, [input.workstream_id]
      );
      if ((ws.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'workstream not found');
      const taskId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'mission_task.created',
        actor_id: input.actor_id,
        object_type: 'mission_task',
        object_id: taskId,
        correlation_id: crypto.randomUUID(),
        payload: { workstream_id: input.workstream_id, title: input.title },
      });
      const inserted = await client.query<{ id: string }>(
        `INSERT INTO mission_tasks (id, workstream_id, mission_id, title, agent_id, task_type, reversible, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id`,
        [taskId, input.workstream_id, ws.rows[0].mission_id, input.title,
         input.agent_id ?? null, input.task_type ?? null, input.reversible ?? false, event.id]
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

  /** Record an action attempt (success/failure/compensation) with attempt counting. */
  async recordActionAttempt(input: {
    mission_task_id: string; actor_id: string; outcome: 'succeeded' | 'failed' | 'compensated';
    detail?: Record<string, unknown>; workflow_task_id?: string;
  }): Promise<{ attempt_number: number; task_status: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const task = await client.query<{ mission_id: string; attempts: number; reversible: boolean }>(
        `SELECT mission_id, attempts, reversible FROM mission_tasks WHERE id = $1 FOR UPDATE`,
        [input.mission_task_id]
      );
      if ((task.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'mission task not found');
      const attemptNumber = task.rows[0].attempts + 1;
      const event = await eventLog.appendWithClient(client, {
        event_type: `mission_action.${input.outcome}`,
        actor_id: input.actor_id,
        object_type: 'mission_action_attempt',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { mission_task_id: input.mission_task_id, attempt_number: attemptNumber, outcome: input.outcome },
      });
      await client.query(
        `INSERT INTO mission_action_attempts
           (mission_task_id, mission_id, attempt_number, outcome, detail_json, event_log_id)
         VALUES ($1,$2,$3,$4,$5::jsonb,$6)`,
        [input.mission_task_id, task.rows[0].mission_id, attemptNumber, input.outcome,
         JSON.stringify(input.detail ?? {}), event.id]
      );
      const taskStatus = input.outcome === 'succeeded' ? 'completed'
        : input.outcome === 'compensated' ? 'failed' : 'failed';
      await client.query(
        `UPDATE mission_tasks
            SET attempts = $2, status = $3,
                compensated = CASE WHEN $4 THEN true ELSE compensated END,
                workflow_task_id = COALESCE($5, workflow_task_id),
                updated_at = now()
          WHERE id = $1`,
        [input.mission_task_id, attemptNumber, taskStatus, input.outcome === 'compensated', input.workflow_task_id ?? null]
      );
      await client.query('COMMIT');
      return { attempt_number: attemptNumber, task_status: taskStatus };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async completeWorkstream(input: { workstream_id: string; actor_id: string; status?: 'completed' | 'failed' }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const status = input.status ?? 'completed';
      if (status === 'completed') {
        const incomplete = await client.query<{ count: string }>(
          `SELECT COUNT(*)::int AS count FROM mission_tasks
            WHERE workstream_id = $1 AND status NOT IN ('completed')`,
          [input.workstream_id]
        );
        if (Number(incomplete.rows[0].count) > 0) {
          throw new PublicHttpError(409, 'workstream has incomplete tasks');
        }
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: `workstream.${status}`,
        actor_id: input.actor_id,
        object_type: 'workstream',
        object_id: input.workstream_id,
        correlation_id: crypto.randomUUID(),
        payload: { status },
      });
      const updated = await client.query(
        `UPDATE workstreams SET status = $2, updated_at = now() WHERE id = $1 AND status NOT IN ('completed','failed','cancelled')`,
        [input.workstream_id, status]
      );
      if ((updated.rowCount ?? 0) !== 1) throw new PublicHttpError(409, 'workstream is not in a completable state');
      void event;
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // -------------------------------------------------------------------------
  // Evidence, settlement, completion (gated), attestation
  // -------------------------------------------------------------------------

  async linkEvidence(input: { mission_id: string; evidence_id: string; actor_id: string }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const evidence = await client.query(`SELECT id FROM autonomy_evidence WHERE id = $1`, [input.evidence_id]);
      if ((evidence.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'evidence not found');
      const linkId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'mission.evidence_linked',
        actor_id: input.actor_id,
        object_type: 'mission_evidence_bundle',
        object_id: linkId,
        correlation_id: crypto.randomUUID(),
        payload: { mission_id: input.mission_id, evidence_id: input.evidence_id },
      });
      await client.query(
        `INSERT INTO mission_evidence_bundle (id, mission_id, evidence_id, linked_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5) ON CONFLICT (mission_id, evidence_id) DO NOTHING`,
        [linkId, input.mission_id, input.evidence_id, input.actor_id, event.id]
      );
      await client.query('COMMIT');
      return { id: linkId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async recordSettlement(input: { mission_id: string; settlement: Record<string, unknown>; actor_id: string }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const event = await eventLog.appendWithClient(client, {
        event_type: 'mission.settlement_recorded',
        actor_id: input.actor_id,
        object_type: 'mission_settlement',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { mission_id: input.mission_id },
      });
      await client.query(
        `INSERT INTO mission_settlements (mission_id, settlement_json, recorded_by_actor_id, event_log_id)
         VALUES ($1,$2::jsonb,$3,$4) ON CONFLICT (mission_id) DO NOTHING`,
        [input.mission_id, JSON.stringify(input.settlement), input.actor_id, event.id]
      );
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Return the completion readiness of a mission: which gates are satisfied.
   * A mission may only be completed when every check passes.
   */
  async completionReadiness(missionId: string): Promise<{
    ready: boolean;
    required_workstreams_complete: boolean;
    has_evidence: boolean;
    has_settlement: boolean;
    has_audit: boolean;
    has_outcome: boolean;
    blocking: string[];
  }> {
    const [workstreams, evidence, settlement, audit, outcome] = await Promise.all([
      db.query<{ count: string }>(
        `SELECT COUNT(*)::int AS count FROM workstreams
          WHERE mission_id = $1 AND required = true AND status NOT IN ('completed','cancelled')`, [missionId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM mission_evidence_bundle WHERE mission_id = $1`, [missionId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM mission_settlements WHERE mission_id = $1`, [missionId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM decision_log WHERE input_summary LIKE $1`, [`%mission ${missionId}%`]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM mission_outcomes WHERE mission_id = $1`, [missionId]),
    ]);
    const requiredWorkstreamsComplete = Number(workstreams.rows[0].count) === 0;
    const hasEvidence = Number(evidence.rows[0].count) > 0;
    const hasSettlement = Number(settlement.rows[0].count) > 0;
    const hasAudit = Number(audit.rows[0].count) > 0;
    const hasOutcome = Number(outcome.rows[0].count) > 0;
    const blocking: string[] = [];
    if (!requiredWorkstreamsComplete) blocking.push('required workstreams incomplete');
    if (!hasEvidence) blocking.push('no evidence linked');
    if (!hasSettlement) blocking.push('no settlement recorded');
    if (!hasAudit) blocking.push('no audit records');
    if (!hasOutcome) blocking.push('no outcome recorded');
    return {
      ready: requiredWorkstreamsComplete && hasEvidence && hasSettlement && hasAudit && hasOutcome,
      required_workstreams_complete: requiredWorkstreamsComplete,
      has_evidence: hasEvidence, has_settlement: hasSettlement, has_audit: hasAudit, has_outcome: hasOutcome,
      blocking,
    };
  }

  async recordOutcome(input: {
    mission_id: string; result: 'success' | 'partial' | 'failure'; summary: string;
    detail?: Record<string, unknown>; actor_id: string;
  }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const event = await eventLog.appendWithClient(client, {
        event_type: 'mission.outcome_recorded',
        actor_id: input.actor_id,
        object_type: 'mission_outcome',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { mission_id: input.mission_id, result: input.result },
      });
      await client.query(
        `INSERT INTO mission_outcomes (mission_id, result, summary, detail_json, recorded_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4::jsonb,$5,$6) ON CONFLICT (mission_id) DO NOTHING`,
        [input.mission_id, input.result, input.summary, JSON.stringify(input.detail ?? {}), input.actor_id, event.id]
      );
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Complete a mission. Fails closed unless every completion gate is satisfied.
   * Writes the mission attestation bundle within the transition transaction.
   */
  async completeMission(input: { mission_id: string; actor_id: string; reason: string }): Promise<{ mission: MissionRecord; attestation_id: string }> {
    const readiness = await this.completionReadiness(input.mission_id);
    if (!readiness.ready) {
      throw new PublicHttpError(409, `mission completion blocked: ${readiness.blocking.join('; ')}`);
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const current = await client.query<MissionRecord>(
        `SELECT ${MISSION_COLUMNS} FROM missions WHERE id = $1 FOR UPDATE`, [input.mission_id]
      );
      if ((current.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'mission not found');
      if (current.rows[0].status !== 'evaluating') {
        throw new PublicHttpError(409, `mission must be evaluating to complete (is ${current.rows[0].status})`);
      }
      const mission = await this.transitionWithClient(client, {
        mission_id: input.mission_id, to_status: 'completed', actor_id: input.actor_id, reason: input.reason,
      } as any);
      const attestationId = await this.writeAttestationWithClient(client, input.mission_id, input.actor_id);
      await client.query('COMMIT');
      return { mission, attestation_id: attestationId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async settleMission(input: { mission_id: string; actor_id: string; reason: string }): Promise<MissionRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.transitionWithClient(client, {
        mission_id: input.mission_id, to_status: 'settled', actor_id: input.actor_id, reason: input.reason,
      } as any);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async writeAttestationWithClient(client: PoolClient, missionId: string, actorId: string): Promise<string> {
    const bundle = await this.buildAttestationBundle(client, missionId);
    const attestationHash = crypto.createHash('sha256').update(stableStringify(bundle)).digest('hex');
    const attestationId = crypto.randomUUID();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'mission.attested',
      actor_id: actorId,
      object_type: 'mission_attestation',
      object_id: attestationId,
      correlation_id: crypto.randomUUID(),
      payload: { mission_id: missionId, attestation_hash: attestationHash },
    });
    await client.query(
      `INSERT INTO mission_attestations (id, mission_id, attestation_json, attestation_hash, recorded_by_actor_id, event_log_id)
       VALUES ($1,$2,$3::jsonb,$4,$5,$6) ON CONFLICT (mission_id) DO NOTHING`,
      [attestationId, missionId, JSON.stringify(bundle), attestationHash, actorId, event.id]
    );
    return attestationId;
  }

  private async buildAttestationBundle(client: PoolClient, missionId: string): Promise<Record<string, unknown>> {
    const [mission, goal, workstreams, tasks, actions, evidence, outcome, settlement, transitions] = await Promise.all([
      client.query(`SELECT ${MISSION_COLUMNS} FROM missions WHERE id = $1`, [missionId]),
      client.query(`SELECT sg.id, sg.title FROM strategic_goals sg JOIN missions m ON m.strategic_goal_id = sg.id WHERE m.id = $1`, [missionId]),
      client.query(`SELECT id, title, status, required FROM workstreams WHERE mission_id = $1 ORDER BY created_at`, [missionId]),
      client.query(`SELECT id, workstream_id, title, status, attempts, compensated FROM mission_tasks WHERE mission_id = $1 ORDER BY created_at`, [missionId]),
      client.query(`SELECT mission_task_id, attempt_number, outcome FROM mission_action_attempts WHERE mission_id = $1 ORDER BY created_at`, [missionId]),
      client.query(`SELECT evidence_id FROM mission_evidence_bundle WHERE mission_id = $1`, [missionId]),
      client.query(`SELECT result, summary FROM mission_outcomes WHERE mission_id = $1`, [missionId]),
      client.query(`SELECT settlement_json FROM mission_settlements WHERE mission_id = $1`, [missionId]),
      client.query(`SELECT from_status, to_status, reason FROM mission_state_transitions WHERE mission_id = $1 ORDER BY created_at`, [missionId]),
    ]);
    const failures = actions.rows.filter((a: any) => a.outcome === 'failed');
    const compensations = actions.rows.filter((a: any) => a.outcome === 'compensated');
    return {
      mission: mission.rows[0],
      strategic_goal: goal.rows[0] ?? null,
      task_graph: {
        workstreams: workstreams.rows,
        tasks: tasks.rows,
      },
      actions: actions.rows,
      evidence_ids: evidence.rows.map((e: any) => e.evidence_id),
      governance_transitions: transitions.rows,
      resource_use: settlement.rows[0]?.settlement_json ?? {},
      failures,
      compensations,
      outcome: outcome.rows[0] ?? null,
      attested_at_transition_count: transitions.rowCount,
    };
  }

  async getMission(missionId: string): Promise<(MissionRecord & {
    workstreams: number; evidence: number; readiness: Awaited<ReturnType<MissionService['completionReadiness']>>;
    attested: boolean;
  }) | null> {
    const mission = await db.query<MissionRecord>(`SELECT ${MISSION_COLUMNS} FROM missions WHERE id = $1`, [missionId]);
    if ((mission.rowCount ?? 0) !== 1) return null;
    const [workstreams, evidence, readiness, attestation] = await Promise.all([
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM workstreams WHERE mission_id = $1`, [missionId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM mission_evidence_bundle WHERE mission_id = $1`, [missionId]),
      this.completionReadiness(missionId),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM mission_attestations WHERE mission_id = $1`, [missionId]),
    ]);
    return {
      ...mission.rows[0],
      workstreams: Number(workstreams.rows[0].count),
      evidence: Number(evidence.rows[0].count),
      readiness,
      attested: Number(attestation.rows[0].count) > 0,
    };
  }

  async getAttestation(missionId: string): Promise<Record<string, unknown> | null> {
    const result = await db.query<{ attestation_json: Record<string, unknown>; attestation_hash: string }>(
      `SELECT attestation_json, attestation_hash FROM mission_attestations WHERE mission_id = $1`, [missionId]
    );
    if ((result.rowCount ?? 0) !== 1) return null;
    return { ...result.rows[0].attestation_json, attestation_hash: result.rows[0].attestation_hash };
  }

  private async requireRootId(client: PoolClient): Promise<string> {
    await civilizationKernel.ensureCivilizationRoot();
    const root = await client.query<{ id: string }>(`SELECT id FROM civilizations WHERE status = 'active' LIMIT 1`);
    if ((root.rowCount ?? 0) !== 1) throw new PublicHttpError(409, 'no active civilization root');
    return root.rows[0].id;
  }
}

export const missionService = new MissionService();
