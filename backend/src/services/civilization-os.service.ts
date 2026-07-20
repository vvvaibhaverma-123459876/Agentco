import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { governanceService } from './governance.service';
import { killSwitchService } from './kill-switch.service';
import { civilizationMetrics } from './civilization-metrics.service';
import { judiciaryCaseService } from './judiciary-case.service';
import { safeEvolution } from './safe-evolution.service';
import { domainRegistry } from './domain-registry.service';
import { collectiveKnowledge } from './collective-knowledge.service';
import { PublicHttpError } from '../http-errors';

/**
 * Civilization operating system (build phase C12).
 *
 * The continuous coordinator that integrates every prior layer into one tick
 * loop: source work -> route to institutions -> orchestrate the judiciary,
 * learning, expansion, and knowledge layers as real work -> enforce
 * governance -> sweep emergencies/reservations -> update the civilization
 * status projection. Leader election uses a Postgres advisory lock so only one
 * active scheduler ticks at a time, even across restarts, and re-running a
 * tick never duplicates work (every sourcing and orchestration step is
 * idempotent). The kill switch and pause/drain controls gate protected work.
 */

const OS_ADVISORY_LOCK_KEY = 918_273_645; // stable arbitrary key for the civilization scheduler leader lock
const OS_KILL_SCOPES = ['global', 'civilization.scheduler', 'civilization.os'];

export type OsMode = 'stopped' | 'running' | 'paused' | 'drained';

export interface TickResult {
  tick_number: number;
  was_leader: boolean;
  mode: OsMode;
  work_sourced: number;
  work_routed: number;
  emergencies_expired: number;
  reservations_expired: number;
  status: Record<string, unknown>;
  skipped_reason?: string;
}

const INSTANCE = `os-${crypto.randomBytes(4).toString('hex')}`;

export class CivilizationOsService {
  private timer: NodeJS.Timeout | null = null;
  private intervalMs = 60_000;

  // -------------------------------------------------------------------------
  // Controls
  // -------------------------------------------------------------------------

  async setMode(mode: OsMode, actorId?: string): Promise<void> {
    const root = await civilizationKernel.ensureCivilizationRoot();
    await db.query(
      `INSERT INTO civ_os_state (id, civilization_id, mode, updated_by_actor_id, updated_at)
       VALUES (1,$1,$2,$3, now())
       ON CONFLICT (id) DO UPDATE SET mode = EXCLUDED.mode, civilization_id = EXCLUDED.civilization_id,
         updated_by_actor_id = EXCLUDED.updated_by_actor_id, updated_at = now()`,
      [root.id, mode, actorId ?? null]
    );
  }

  async getMode(): Promise<OsMode> {
    const r = await db.query<{ mode: OsMode }>(`SELECT mode FROM civ_os_state WHERE id = 1`);
    return r.rows[0]?.mode ?? 'stopped';
  }

  async pause(actorId?: string): Promise<void> { await this.setMode('paused', actorId); }
  async resume(actorId?: string): Promise<void> { await this.setMode('running', actorId); }
  async drain(actorId?: string): Promise<void> { await this.setMode('drained', actorId); }

  startDaemon(intervalMs = 60_000, actorId?: string): { running: boolean; intervalMs: number } {
    if (!Number.isFinite(intervalMs) || intervalMs < 1_000) throw new PublicHttpError(400, 'interval must be >= 1000ms');
    this.intervalMs = intervalMs;
    void this.setMode('running', actorId);
    if (this.timer) return { running: true, intervalMs };
    this.timer = setInterval(() => {
      void this.tick().catch(() => { /* errors recorded in the tick log */ });
    }, this.intervalMs);
    this.timer.unref?.();
    return { running: true, intervalMs };
  }

  stopDaemon(actorId?: string): { running: boolean } {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    void this.setMode('stopped', actorId);
    return { running: false };
  }

  // -------------------------------------------------------------------------
  // The tick
  // -------------------------------------------------------------------------

  async tick(): Promise<TickResult> {
    const root = await civilizationKernel.ensureCivilizationRoot();

    // Kill switch gates every protected tick.
    for (const scope of OS_KILL_SCOPES) {
      const active = await killSwitchService.getActive(scope);
      if (active) {
        return this.recordTick(root.id, { was_leader: false, mode: await this.getMode(), skipped_reason: `kill switch '${scope}' active` });
      }
    }

    // Leader election: a single connection holds the advisory lock for the tick.
    const client = await db.connect();
    try {
      const lock = await client.query<{ locked: boolean }>(`SELECT pg_try_advisory_lock($1) AS locked`, [OS_ADVISORY_LOCK_KEY]);
      if (!lock.rows[0].locked) {
        client.release();
        return this.recordTick(root.id, { was_leader: false, mode: await this.getMode(), skipped_reason: 'not leader' });
      }
      try {
        const mode = await this.getMode();
        if (mode === 'paused' || mode === 'stopped') {
          return this.recordTick(root.id, { was_leader: true, mode, skipped_reason: `mode ${mode}` });
        }
        // In 'drained' mode, no NEW work is sourced, but sweeps still run.
        const sourceNew = mode === 'running';

        const routed = sourceNew ? await this.workSourcerAndRouter(root.id) : { sourced: 0, routed: 0 };
        const orchestrated = sourceNew ? await this.layerOrchestrator() : null;
        const emergencies = await this.emergencyController();
        const reservations = await this.expireReservations();
        const status = await this.statusProjection(root.id);

        return this.recordTick(root.id, {
          was_leader: true, mode,
          work_sourced: routed.sourced, work_routed: routed.routed,
          emergencies_expired: emergencies, reservations_expired: reservations,
          status: orchestrated ? { ...status, orchestrated } : status,
        });
      } finally {
        await client.query(`SELECT pg_advisory_unlock($1)`, [OS_ADVISORY_LOCK_KEY]);
        client.release();
      }
    } catch (error) {
      try { client.release(); } catch { /* already released */ }
      throw error;
    }
  }

  /**
   * LayerOrchestrator (brief A.6/B.8): the coordinator drives the judiciary,
   * learning, expansion, and knowledge layers as real work inside the tick —
   * not merely as a status observation. Every step is idempotent, so re-ticks
   * and restart recovery never duplicate effects, and a failing layer is
   * recorded in the tick status without blocking the other layers.
   */
  private async layerOrchestrator(): Promise<Record<string, unknown>> {
    const counts = {
      escalations_routed: 0,
      candidates_retained: 0,
      domains_suspended: 0,
      provenance_reconciled: 0,
    };
    const errors: string[] = [];
    try {
      counts.escalations_routed = await this.routeEscalationsToJudiciary();
    } catch (error) {
      errors.push(`judiciary_routing: ${(error as Error).message}`);
    }
    try {
      counts.candidates_retained = await this.retireMonitoredCandidates();
    } catch (error) {
      errors.push(`learning_retention: ${(error as Error).message}`);
    }
    try {
      counts.domains_suspended = await domainRegistry.suspendBelowThreshold();
    } catch (error) {
      errors.push(`expansion_suspension: ${(error as Error).message}`);
    }
    try {
      counts.provenance_reconciled = await collectiveKnowledge.sweepDanglingProvenance();
    } catch (error) {
      errors.push(`knowledge_reconciliation: ${(error as Error).message}`);
    }
    return errors.length > 0 ? { ...counts, errors } : { ...counts };
  }

  /**
   * Coalition -> judiciary intake: route open escalations that target the
   * judiciary into real cases, keyed by source_dispute_id = escalation id.
   * The `existing` check below is a fast-path optimization, not the real
   * guarantee -- it runs on this transaction's connection while openCase()
   * commits on its own separate one, so it cannot by itself prevent a
   * concurrent duplicate. The actual idempotency backstop is AUD-013's
   * migration 145 partial unique index on judiciary_cases.source_dispute_id,
   * which openCase() catches and resolves to the existing case.
   */
  private async routeEscalationsToJudiciary(): Promise<number> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const pending = await client.query<{
        id: string;
        coalition_id: string;
        escalation_type: 'deadlock' | 'commitment_breach';
        reason: string;
        created_by_actor_id: string;
      }>(
        `SELECT id, coalition_id, escalation_type, reason, created_by_actor_id
           FROM coalition_escalations
          WHERE status = 'open' AND target = 'judiciary'
          ORDER BY created_at
          LIMIT 10
          FOR UPDATE SKIP LOCKED`
      );
      let routed = 0;
      for (const row of pending.rows) {
        const existing = await client.query(
          `SELECT id FROM judiciary_cases WHERE source_dispute_id = $1 LIMIT 1`,
          [row.id]
        );
        if ((existing.rowCount ?? 0) === 0) {
          await judiciaryCaseService.openCase({
            dispute_type: row.escalation_type === 'commitment_breach' ? 'contract_breach' : 'jurisdiction_conflict',
            title: `Coalition escalation: ${row.escalation_type}`,
            complainant_actor_id: row.created_by_actor_id,
            respondent_scope_type: 'coalition',
            respondent_scope_id: row.coalition_id,
            source_dispute_id: row.id,
            body: { reason: row.reason, routed_by: 'civilization-os' },
          });
        }
        await client.query(
          `UPDATE coalition_escalations SET status = 'routed', routed_at = now() WHERE id = $1`,
          [row.id]
        );
        routed++;
      }
      await client.query('COMMIT');
      return routed;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Post-promotion monitoring closeout: candidates that have stayed in
   * 'monitored' beyond the configured window without a rollback are retained
   * through the safe-evolution status machine. Window in minutes via
   * CIV_OS_RETAIN_AFTER_MINUTES (default 15).
   */
  private async retireMonitoredCandidates(): Promise<number> {
    const windowMinutes = Math.max(0, Number(process.env.CIV_OS_RETAIN_AFTER_MINUTES ?? '15'));
    const due = await db.query<{ id: string }>(
      `SELECT c.id
         FROM civ_learning_candidates c
        WHERE c.status = 'monitored'
          AND (SELECT max(t.created_at) FROM civ_candidate_transitions t
                WHERE t.candidate_id = c.id AND t.to_status = 'monitored')
              <= now() - make_interval(mins => $1)
        ORDER BY c.id
        LIMIT 10`,
      [windowMinutes]
    );
    let retained = 0;
    const client = await db.connect();
    let actor: string;
    try {
      actor = await this.learningRetentionActor(client);
    } finally {
      client.release();
    }
    for (const row of due.rows) {
      await safeEvolution.retain({ candidate_id: row.id, actor_id: actor });
      retained++;
    }
    return retained;
  }

  /**
   * WorkSourcer + InstitutionRouter + MissionCoordinator: assign a lead
   * institution to planned/funded missions that lack one, routing by the
   * mission's strategic-goal society when possible. Idempotent — a mission that
   * already has a lead institution is never re-sourced, so re-ticks and restart
   * recovery never duplicate work.
   */
  private async workSourcerAndRouter(civilizationId: string): Promise<{ sourced: number; routed: number }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const pending = await client.query<{ id: string }>(
        `SELECT id FROM missions
          WHERE civilization_id = $1
            AND status IN ('approved','funded','planned')
            AND lead_institution_id IS NULL
          ORDER BY created_at
          LIMIT 25
          FOR UPDATE SKIP LOCKED`,
        [civilizationId]
      );
      let routed = 0;
      for (const mission of pending.rows) {
        // Deterministic institution assignment (first active institution by
        // creation order). Domain-aware routing is enforced separately by the
        // C11 capability-expansion routing check at grant time; this step only
        // makes a single idempotent lead-institution assignment that a re-tick
        // will not repeat.
        const institution = await client.query<{ id: string }>(
          `SELECT i.id FROM institutions i
            WHERE i.entity_type = 'institution' AND i.status = 'active'
            ORDER BY i.created_at LIMIT 1`
        );
        if ((institution.rowCount ?? 0) === 0) continue;
        const event = await eventLog.appendWithClient(client, {
          event_type: 'civilization_os.mission_routed',
          actor_id: await this.workRouterActor(client),
          object_type: 'mission',
          object_id: mission.id,
          correlation_id: crypto.randomUUID(),
          payload: { lead_institution_id: institution.rows[0].id },
        });
        await client.query(
          `UPDATE missions SET lead_institution_id = $2 WHERE id = $1 AND lead_institution_id IS NULL`,
          [mission.id, institution.rows[0].id]
        );
        void event;
        routed += 1;
      }
      await client.query('COMMIT');
      return { sourced: pending.rowCount ?? 0, routed };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** EmergencyController: expire due kernel emergency states and governance emergency powers. */
  private async emergencyController(): Promise<number> {
    const kernel = await civilizationKernel.expireDueEmergencies();
    const governance = await governanceService.expireEmergencyPowers();
    return kernel.expired + governance.expired;
  }

  /** Expire due resource reservations via the canonical ledger. */
  private async expireReservations(): Promise<number> {
    try {
      const { resourceLedger } = await import('./resource-ledger.service');
      return await resourceLedger.expireReservations(100);
    } catch {
      return 0;
    }
  }

  /**
   * GeneralityReporter + LoopSupervisor: the civilization-wide status
   * projection across every layer. This is the read model the operator plane
   * and health surface consume.
   */
  async statusProjection(civilizationId?: string): Promise<Record<string, unknown>> {
    const root = civilizationId ? { id: civilizationId } : (await civilizationKernel.getActiveCivilization());
    if (!root) return { civilization: null };
    const id = root.id;
    const q = async (sql: string, params: unknown[] = []) => {
      try { return Number((await db.query<{ c: string }>(sql, params)).rows[0]?.c ?? 0); }
      catch { return 0; }
    };
    const [
      societies, institutions, citizensActive, coalitionsActive, missionsExecuting, missionsCompleted,
      disputesOpen, candidatesOpen, expansionOpen, activeGrants, activeCivEmergencies, generalityDomains,
    ] = await Promise.all([
      q(`SELECT COUNT(*)::int c FROM societies WHERE civilization_id = $1 AND status = 'active'`, [id]),
      q(`SELECT COUNT(*)::int c FROM institutions WHERE entity_type='institution' AND status='active'`),
      q(`SELECT COUNT(*)::int c FROM citizens WHERE civilization_id = $1 AND status IN ('active','probationary')`, [id]),
      q(`SELECT COUNT(*)::int c FROM institution_coalitions WHERE civilization_id = $1 AND status = 'active'`, [id]),
      q(`SELECT COUNT(*)::int c FROM missions WHERE civilization_id = $1 AND status = 'executing'`, [id]),
      q(`SELECT COUNT(*)::int c FROM missions WHERE civilization_id = $1 AND status IN ('completed','settled','archived')`, [id]),
      q(`SELECT COUNT(*)::int c FROM judiciary_cases WHERE civilization_id = $1 AND status NOT IN ('closed','dismissed','final')`, [id]),
      q(`SELECT COUNT(*)::int c FROM civ_learning_candidates WHERE civilization_id = $1 AND status NOT IN ('rejected','retained','rolled_back')`, [id]),
      q(`SELECT COUNT(*)::int c FROM expansion_proposals WHERE civilization_id = $1 AND status NOT IN ('rejected','revoked','expanded')`, [id]),
      q(`SELECT COUNT(*)::int c FROM capability_grants WHERE status = 'active'`),
      q(`SELECT COUNT(*)::int c FROM civilization_emergency_states WHERE civilization_id = $1 AND status = 'active'`, [id]),
      q(`SELECT COUNT(DISTINCT domain_key)::int c FROM capability_grants WHERE status = 'active'`),
    ]);
    return {
      civilization_id: id,
      societies_active: societies,
      institutions_active: institutions,
      citizens_executable: citizensActive,
      coalitions_active: coalitionsActive,
      missions_executing: missionsExecuting,
      missions_completed: missionsCompleted,
      disputes_open: disputesOpen,
      learning_candidates_open: candidatesOpen,
      expansion_proposals_open: expansionOpen,
      active_capability_grants: activeGrants,
      active_emergencies: activeCivEmergencies,
      generality_domains: generalityDomains,
    };
  }

  /** Restart recovery: report in-flight state without re-creating work. */
  async recoverAndReport(): Promise<{ mode: OsMode; last_tick: number; in_flight_missions: number; status: Record<string, unknown> }> {
    const root = await civilizationKernel.ensureCivilizationRoot();
    const mode = await this.getMode();
    const lastTick = await db.query<{ tick_count: string }>(`SELECT tick_count FROM civ_os_state WHERE id = 1`);
    const inFlight = await db.query<{ c: string }>(
      `SELECT COUNT(*)::int c FROM missions WHERE civilization_id = $1 AND status = 'executing'`, [root.id]
    );
    return {
      mode,
      last_tick: Number(lastTick.rows[0]?.tick_count ?? 0),
      in_flight_missions: Number(inFlight.rows[0].c),
      status: await this.statusProjection(root.id),
    };
  }

  async recentTicks(limit = 20): Promise<Array<Record<string, unknown>>> {
    const r = await db.query(
      `SELECT tick_number, was_leader, mode, work_sourced, work_routed, emergencies_expired, reservations_expired, created_at
         FROM civ_os_ticks ORDER BY tick_number DESC LIMIT $1`, [Math.min(limit, 100)]
    );
    return r.rows as any;
  }

  // -------------------------------------------------------------------------

  private async recordTick(civilizationId: string, input: {
    was_leader: boolean; mode: OsMode; work_sourced?: number; work_routed?: number;
    emergencies_expired?: number; reservations_expired?: number; status?: Record<string, unknown>; skipped_reason?: string;
  }): Promise<TickResult> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const next = await client.query<{ n: string }>(
        `INSERT INTO civ_os_state (id, civilization_id, tick_count, heartbeat_at, last_leader_instance, updated_at)
         VALUES (1,$1,1, now(), $2, now())
         ON CONFLICT (id) DO UPDATE SET tick_count = civ_os_state.tick_count + 1,
           heartbeat_at = now(), last_leader_instance = CASE WHEN $3 THEN $2 ELSE civ_os_state.last_leader_instance END,
           civilization_id = EXCLUDED.civilization_id
         RETURNING tick_count AS n`,
        [civilizationId, INSTANCE, input.was_leader]
      );
      const tickNumber = Number(next.rows[0].n);
      const status = input.status ?? {};
      const event = await eventLog.appendWithClient(client, {
        event_type: 'civilization_os.tick',
        actor_id: await this.schedulerActor(client),
        object_type: 'civ_os_tick',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { tick_number: tickNumber, was_leader: input.was_leader, mode: input.mode, skipped_reason: input.skipped_reason ?? null },
      });
      await client.query(
        `INSERT INTO civ_os_ticks
           (civilization_id, tick_number, was_leader, mode, work_sourced, work_routed, emergencies_expired, reservations_expired,
            disputes_open, learning_candidates_open, expansion_proposals_open, status_json, instance, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13,$14)`,
        [civilizationId, tickNumber, input.was_leader, input.mode,
         input.work_sourced ?? 0, input.work_routed ?? 0, input.emergencies_expired ?? 0, input.reservations_expired ?? 0,
         Number(status.disputes_open ?? 0), Number(status.learning_candidates_open ?? 0), Number(status.expansion_proposals_open ?? 0),
         JSON.stringify(status), INSTANCE, event.id]
      );
      await client.query('COMMIT');
      civilizationMetrics.recordTick({
        was_leader: input.was_leader,
        reservations_expired: input.reservations_expired ?? 0,
        heartbeat_epoch: Math.floor(new Date(event.occurred_at ?? Date.now()).getTime() / 1000) || Math.floor(Date.now() / 1000),
        status,
      });
      return {
        tick_number: tickNumber, was_leader: input.was_leader, mode: input.mode,
        work_sourced: input.work_sourced ?? 0, work_routed: input.work_routed ?? 0,
        emergencies_expired: input.emergencies_expired ?? 0, reservations_expired: input.reservations_expired ?? 0,
        status, skipped_reason: input.skipped_reason,
      };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * AUD-004 M5: narrowly-scoped machine principals, one per autonomous sub-responsibility --
   * NOT one universal service actor with implicit access to everything the orchestrator does.
   * Each is a real `actors` row (service_identities scoped) so its writes are attributable and
   * distinguishable in audit trails; none holds RBAC permissions beyond what its own scope
   * lists (registerActor/service_identities alone grants no permission -- these actors are
   * never assigned governor/task_executor or any human-facing role, so they cannot satisfy
   * conditions 16/25 by relabeling: they simply never appear as evaluator/appellate authority).
   */
  private async scopedServiceActor(client: PoolClient, name: string, scopes: string[]): Promise<string> {
    const actor = await client.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ created_by: 'CivilizationOsService' })]
    );
    await client.query(
      `INSERT INTO service_identities (actor_id, service_name, scopes)
       VALUES ($1,$2,$3::jsonb)
       ON CONFLICT (actor_id) DO NOTHING`,
      [actor.rows[0].id, name, JSON.stringify(scopes)]
    );
    return actor.rows[0].id;
  }

  /** Scheduler/tick bookkeeping actor -- attributes tick heartbeat events only. */
  private async schedulerActor(client: PoolClient): Promise<string> {
    return this.scopedServiceActor(client, 'agentco-civilization-os-scheduler', ['civilization_os.tick.record']);
  }

  /** Work-sourcing/routing actor -- attributes mission lead-institution assignment only. */
  private async workRouterActor(client: PoolClient): Promise<string> {
    return this.scopedServiceActor(client, 'agentco-civilization-os-work-router', ['mission.lead_institution.assign']);
  }

  /** Learning-retention actor -- attributes post-promotion candidate retention only. */
  private async learningRetentionActor(client: PoolClient): Promise<string> {
    return this.scopedServiceActor(client, 'agentco-civilization-os-learning-retention', ['evolution.candidate.retain']);
  }
}

export const civilizationOs = new CivilizationOsService();
