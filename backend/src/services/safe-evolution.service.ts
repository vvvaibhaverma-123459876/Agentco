import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { PublicHttpError } from '../http-errors';

/**
 * Learning and safe evolution (build phase C10).
 *
 * Connects failures to improvements through one governed lifecycle:
 * observed -> candidate -> analysed -> test_generated -> sandboxed ->
 * evaluated -> approved -> canary -> promoted | rejected -> monitored ->
 * retained | rolled_back. Independent evaluation is enforced (evaluator actor
 * <> proposer actor). Canary breach forces rollback. Promotion requires
 * non-regression across safety, calibration, and evidence metrics, generated
 * regression cases that all pass, and (Tier-2/3) is not auto-promotable.
 */

export type LearningSource =
  | 'resolved_prediction' | 'task_failure' | 'benchmark' | 'audit' | 'dispute'
  | 'user_feedback' | 'near_miss' | 'safety_incident' | 'resource_inefficiency' | 'calibration_regression';
export type LearningForm =
  | 'skill' | 'tool' | 'prompt' | 'policy' | 'routing' | 'planning'
  | 'memory_policy' | 'calibration_threshold' | 'institution_process';
export type CandidateStatus =
  | 'observed' | 'candidate' | 'analysed' | 'test_generated' | 'sandboxed' | 'evaluated'
  | 'approved' | 'rejected' | 'canary' | 'promoted' | 'monitored' | 'retained' | 'rolled_back';

const TRANSITIONS: Record<CandidateStatus, CandidateStatus[]> = {
  observed: ['candidate', 'rejected'],
  candidate: ['analysed', 'rejected'],
  analysed: ['test_generated', 'rejected'],
  test_generated: ['sandboxed', 'rejected'],
  sandboxed: ['evaluated', 'rejected'],
  evaluated: ['approved', 'rejected'],
  approved: ['canary', 'rejected'],
  canary: ['promoted', 'rolled_back', 'rejected'],
  promoted: ['monitored', 'rolled_back'],
  monitored: ['retained', 'rolled_back'],
  rejected: [],
  retained: [],
  rolled_back: [],
};

export interface CandidateRecord {
  id: string; civilization_id: string; source: LearningSource; learning_form: LearningForm;
  title: string; hypothesis: string; proposer_actor_id: string; tier: number;
  source_mission_id: string | null; status: CandidateStatus;
}

const CANDIDATE_COLUMNS =
  'id, civilization_id, source, learning_form, title, hypothesis, proposer_actor_id, tier, source_mission_id, status';

export class SafeEvolutionService {
  async createCandidate(input: {
    source: LearningSource; learning_form: LearningForm; title: string; hypothesis: string;
    proposer_actor_id: string; tier?: number; source_mission_id?: string; civilization_id?: string;
  }): Promise<CandidateRecord> {
    if (!input.title || !input.hypothesis) throw new PublicHttpError(400, 'title and hypothesis are required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.rootId());
      const candidateId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'learning.candidate_created',
        actor_id: input.proposer_actor_id,
        object_type: 'civ_learning_candidate',
        object_id: candidateId,
        correlation_id: crypto.randomUUID(),
        payload: { source: input.source, learning_form: input.learning_form, title: input.title },
      });
      const inserted = await client.query<CandidateRecord>(
        `INSERT INTO civ_learning_candidates
           (id, civilization_id, source, learning_form, title, hypothesis, proposer_actor_id, tier, source_mission_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
         RETURNING ${CANDIDATE_COLUMNS}`,
        [candidateId, civilizationId, input.source, input.learning_form, input.title, input.hypothesis,
         input.proposer_actor_id, input.tier ?? 2, input.source_mission_id ?? null, event.id]
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

  /** Auto-create a task_failure candidate from a failed mission. Idempotent per mission. */
  async candidateFromMissionFailure(missionId: string, actorId: string): Promise<CandidateRecord | null> {
    const existing = await db.query<CandidateRecord>(
      `SELECT ${CANDIDATE_COLUMNS} FROM civ_learning_candidates WHERE source_mission_id = $1 AND source = 'task_failure' LIMIT 1`,
      [missionId]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];
    const mission = await db.query<{ title: string; civilization_id: string }>(
      `SELECT title, civilization_id FROM missions WHERE id = $1`, [missionId]
    );
    if ((mission.rowCount ?? 0) !== 1) return null;
    return this.createCandidate({
      source: 'task_failure', learning_form: 'planning',
      title: `Learn from failed mission: ${mission.rows[0].title}`,
      hypothesis: 'Adjust planning to avoid the failure mode observed in this mission',
      proposer_actor_id: actorId, tier: 2, source_mission_id: missionId,
      civilization_id: mission.rows[0].civilization_id,
    });
  }

  async recordFailureAnalysis(input: {
    candidate_id: string; failure_summary: string; root_cause: string; detail?: Record<string, unknown>; analysed_by_actor_id: string;
  }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lock(client, input.candidate_id);
      if (c.status !== 'observed' && c.status !== 'candidate') {
        throw new PublicHttpError(409, `failure analysis requires an observed/candidate item (is ${c.status})`);
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: 'learning.failure_analysed',
        actor_id: input.analysed_by_actor_id,
        object_type: 'civ_failure_analysis',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { candidate_id: input.candidate_id },
      });
      await client.query(
        `INSERT INTO civ_failure_analyses (candidate_id, failure_summary, root_cause, detail_json, analysed_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4::jsonb,$5,$6) ON CONFLICT (candidate_id) DO NOTHING`,
        [input.candidate_id, input.failure_summary, input.root_cause, JSON.stringify(input.detail ?? {}), input.analysed_by_actor_id, event.id]
      );
      if (c.status === 'observed') await this.setStatus(client, input.candidate_id, 'candidate', input.analysed_by_actor_id, 'candidate created');
      await this.setStatus(client, input.candidate_id, 'analysed', input.analysed_by_actor_id, 'failure analysed');
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Deterministically generate regression cases (metric floor, safety
   * invariant, held-out, calibration non-regression) from the candidate. Same
   * candidate → same case set.
   */
  async generateRegressions(input: { candidate_id: string; actor_id: string }): Promise<{ count: number }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lock(client, input.candidate_id);
      if (c.status !== 'analysed') throw new PublicHttpError(409, `regressions require an analysed candidate (is ${c.status})`);
      const cases: Array<{ key: string; kind: string; held_out: boolean; spec: Record<string, unknown> }> = [
        { key: 'metric_floor', kind: 'metric_floor', held_out: false, spec: { metric: 'success_rate', floor: 0.6 } },
        { key: 'safety_invariant', kind: 'safety_invariant', held_out: false, spec: { invariant: 'no_self_approval' } },
        { key: 'held_out_1', kind: 'held_out', held_out: true, spec: { partition: 'held_out', seed: c.id.slice(0, 8) } },
        { key: 'calibration_non_regression', kind: 'calibration_non_regression', held_out: false, spec: { metric: 'ece', max: 0.1 } },
      ];
      for (const cs of cases) {
        await client.query(
          `INSERT INTO civ_regression_cases (candidate_id, case_key, case_kind, spec_json, held_out)
           VALUES ($1,$2,$3,$4::jsonb,$5) ON CONFLICT (candidate_id, case_key) DO NOTHING`,
          [input.candidate_id, cs.key, cs.kind, JSON.stringify(cs.spec), cs.held_out]
        );
      }
      await this.setStatus(client, input.candidate_id, 'test_generated', input.actor_id, 'regression cases generated');
      await client.query('COMMIT');
      return { count: cases.length };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async markSandboxed(input: { candidate_id: string; actor_id: string }): Promise<void> {
    await this.simpleAdvance(input.candidate_id, 'test_generated', 'sandboxed', input.actor_id, 'sandbox pass');
  }

  /**
   * Independent evaluation. The evaluator MUST differ from the proposer. All
   * generated regression cases must pass; safety/calibration/evidence must not
   * regress. Records the result and advances to evaluated.
   */
  async evaluate(input: {
    candidate_id: string; evaluator_actor_id: string;
    cases_passed: number; safety_non_regression: boolean; calibration_non_regression: boolean; evidence_non_regression: boolean;
    detail?: Record<string, unknown>;
  }): Promise<{ passed: boolean }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lock(client, input.candidate_id);
      if (c.status !== 'sandboxed') throw new PublicHttpError(409, `evaluation requires a sandboxed candidate (is ${c.status})`);
      if (c.proposer_actor_id === input.evaluator_actor_id) {
        throw new PublicHttpError(409, 'independent evaluation required: the evaluator cannot be the proposer');
      }
      const cases = await client.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM civ_regression_cases WHERE candidate_id = $1`, [input.candidate_id]);
      const total = Number(cases.rows[0].count);
      const passed = input.cases_passed >= total
        && input.safety_non_regression && input.calibration_non_regression && input.evidence_non_regression;
      const event = await eventLog.appendWithClient(client, {
        event_type: 'learning.evaluated',
        actor_id: input.evaluator_actor_id,
        object_type: 'civ_evaluation',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { candidate_id: input.candidate_id, passed, cases_passed: input.cases_passed, cases_total: total },
      });
      await client.query(
        `INSERT INTO civ_evaluations
           (candidate_id, evaluator_actor_id, passed, cases_total, cases_passed, safety_non_regression, calibration_non_regression, evidence_non_regression, detail_json, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10) ON CONFLICT (candidate_id) DO NOTHING`,
        [input.candidate_id, input.evaluator_actor_id, passed, total, input.cases_passed,
         input.safety_non_regression, input.calibration_non_regression, input.evidence_non_regression,
         JSON.stringify(input.detail ?? {}), event.id]
      );
      await this.setStatus(client, input.candidate_id, 'evaluated', input.evaluator_actor_id, `evaluated: ${passed ? 'pass' : 'fail'}`);
      if (passed) {
        await this.setStatus(client, input.candidate_id, 'approved', input.evaluator_actor_id, 'evaluation passed');
      } else {
        await this.setStatus(client, input.candidate_id, 'rejected', input.evaluator_actor_id, 'evaluation failed');
      }
      await auditLog.appendWithClient(client, {
        agent_id: input.evaluator_actor_id,
        action_type: 'decision',
        input_summary: `independent evaluation of candidate ${input.candidate_id}`,
        output_summary: `candidate ${passed ? 'approved' : 'rejected'} (${input.cases_passed}/${total} cases)`,
        confidence_score: 1, risk_level: 'high', human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return { passed };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async startCanary(input: { candidate_id: string; actor_id: string }): Promise<{ canary_id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lock(client, input.candidate_id);
      if (c.status !== 'approved') throw new PublicHttpError(409, `canary requires an approved candidate (is ${c.status})`);
      const canaryId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'learning.canary_started',
        actor_id: input.actor_id,
        object_type: 'civ_canary_run',
        object_id: canaryId,
        correlation_id: crypto.randomUUID(),
        payload: { candidate_id: input.candidate_id },
      });
      await client.query(
        `INSERT INTO civ_canary_runs (id, candidate_id, run_by_actor_id, event_log_id) VALUES ($1,$2,$3,$4)`,
        [canaryId, input.candidate_id, input.actor_id, event.id]
      );
      await this.setStatus(client, input.candidate_id, 'canary', input.actor_id, 'canary started');
      await client.query('COMMIT');
      return { canary_id: canaryId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** Report canary metrics. A breach forces rollback; a clean canary allows promotion. */
  async reportCanary(input: { canary_id: string; actor_id: string; clean: boolean; metric?: Record<string, unknown>; breach_reason?: string }): Promise<{ status: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const canary = await client.query<{ candidate_id: string; status: string }>(
        `SELECT candidate_id, status FROM civ_canary_runs WHERE id = $1 FOR UPDATE`, [input.canary_id]
      );
      if ((canary.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'canary not found');
      if (canary.rows[0].status !== 'running') throw new PublicHttpError(409, `canary already ${canary.rows[0].status}`);
      const status = input.clean ? 'clean' : 'breached';
      await client.query(
        `UPDATE civ_canary_runs SET status = $2, metric_json = $3::jsonb, breach_reason = $4, ended_at = now() WHERE id = $1`,
        [input.canary_id, status, JSON.stringify(input.metric ?? {}), input.breach_reason ?? null]
      );
      if (!input.clean) {
        await this.rollbackWithClient(client, canary.rows[0].candidate_id, input.actor_id, `canary breached: ${input.breach_reason ?? 'metric regression'}`);
      }
      await client.query('COMMIT');
      return { status };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Promote a candidate after a clean canary. Tier-1 may auto-promote; Tier-2/3
   * require a human approver distinct from the proposer.
   */
  async promote(input: { candidate_id: string; actor_id: string; artifact_hash: string; human_approved?: boolean }): Promise<{ version: number }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lock(client, input.candidate_id);
      if (c.status !== 'canary') throw new PublicHttpError(409, `promotion requires a canary candidate (is ${c.status})`);
      const cleanCanary = await client.query<{ count: string }>(
        `SELECT COUNT(*)::int AS count FROM civ_canary_runs WHERE candidate_id = $1 AND status = 'clean'`, [input.candidate_id]
      );
      if (Number(cleanCanary.rows[0].count) === 0) throw new PublicHttpError(409, 'promotion requires a clean canary run');
      if (c.tier >= 2) {
        if (!input.human_approved) throw new PublicHttpError(409, `Tier-${c.tier} changes require human approval to promote`);
        if (input.actor_id === c.proposer_actor_id) throw new PublicHttpError(409, 'the proposer cannot approve their own promotion');
      }
      const prev = await client.query<{ version: number }>(
        `SELECT COALESCE(MAX(version),0) AS version FROM civ_improvement_lineage WHERE candidate_id = $1`, [input.candidate_id]
      );
      const version = Number(prev.rows[0].version) + 1;
      const event = await eventLog.appendWithClient(client, {
        event_type: 'learning.promoted',
        actor_id: input.actor_id,
        object_type: 'civ_improvement_lineage',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { candidate_id: input.candidate_id, version, artifact_hash: input.artifact_hash },
      });
      await client.query(
        `INSERT INTO civ_improvement_lineage (candidate_id, version, artifact_hash, previous_version, decision, actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,'promoted',$5,$6)`,
        [input.candidate_id, version, input.artifact_hash, version > 1 ? version - 1 : null, input.actor_id, event.id]
      );
      await this.setStatus(client, input.candidate_id, 'promoted', input.actor_id, `promoted v${version}`);
      await this.setStatus(client, input.candidate_id, 'monitored', input.actor_id, 'post-promotion monitoring');
      await client.query('COMMIT');
      return { version };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async retain(input: { candidate_id: string; actor_id: string }): Promise<void> {
    await this.simpleAdvance(input.candidate_id, 'monitored', 'retained', input.actor_id, 'monitoring clean; retained');
  }

  /** Executable rollback: records the rollback lineage and terminates the candidate. */
  async rollback(input: { candidate_id: string; actor_id: string; reason: string }): Promise<{ version: number }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const version = await this.rollbackWithClient(client, input.candidate_id, input.actor_id, input.reason);
      await client.query('COMMIT');
      return { version };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async rollbackWithClient(client: PoolClient, candidateId: string, actorId: string, reason: string): Promise<number> {
    const c = await this.lock(client, candidateId);
    if (!['canary', 'promoted', 'monitored'].includes(c.status)) {
      throw new PublicHttpError(409, `rollback requires a canary/promoted/monitored candidate (is ${c.status})`);
    }
    const prev = await client.query<{ version: number }>(
      `SELECT COALESCE(MAX(version),0) AS version FROM civ_improvement_lineage WHERE candidate_id = $1`, [candidateId]
    );
    const version = Number(prev.rows[0].version) + 1;
    const event = await eventLog.appendWithClient(client, {
      event_type: 'learning.rolled_back',
      actor_id: actorId,
      object_type: 'civ_improvement_lineage',
      object_id: crypto.randomUUID(),
      correlation_id: crypto.randomUUID(),
      payload: { candidate_id: candidateId, version, reason },
    });
    await client.query(
      `INSERT INTO civ_improvement_lineage (candidate_id, version, artifact_hash, previous_version, decision, actor_id, event_log_id)
       VALUES ($1,$2,$3,$4,'rolled_back',$5,$6)`,
      [candidateId, version, `rollback-${reason.slice(0, 16)}`, version > 1 ? version - 1 : null, actorId, event.id]
    );
    await this.setStatus(client, candidateId, 'rolled_back', actorId, `rolled back: ${reason}`);
    await auditLog.appendWithClient(client, {
      agent_id: actorId,
      action_type: 'decision',
      input_summary: `rollback candidate ${candidateId}: ${reason}`,
      output_summary: `candidate rolled back at v${version}`,
      confidence_score: 1, risk_level: 'high', human_approved: false,
      downstream_events: [event.id],
    }, { timestamp: new Date().toISOString() });
    return version;
  }

  async getCandidate(candidateId: string): Promise<(CandidateRecord & { regression_cases: number; canary_runs: number; lineage: number }) | null> {
    const c = await db.query<CandidateRecord>(`SELECT ${CANDIDATE_COLUMNS} FROM civ_learning_candidates WHERE id = $1`, [candidateId]);
    if ((c.rowCount ?? 0) !== 1) return null;
    const [cases, canaries, lineage] = await Promise.all([
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM civ_regression_cases WHERE candidate_id = $1`, [candidateId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM civ_canary_runs WHERE candidate_id = $1`, [candidateId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM civ_improvement_lineage WHERE candidate_id = $1`, [candidateId]),
    ]);
    return {
      ...c.rows[0],
      regression_cases: Number(cases.rows[0].count),
      canary_runs: Number(canaries.rows[0].count),
      lineage: Number(lineage.rows[0].count),
    };
  }

  // -------------------------------------------------------------------------

  private async simpleAdvance(candidateId: string, from: CandidateStatus, to: CandidateStatus, actorId: string, reason: string): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lock(client, candidateId);
      if (c.status !== from) throw new PublicHttpError(409, `candidate must be ${from} (is ${c.status})`);
      await this.setStatus(client, candidateId, to, actorId, reason);
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async setStatus(client: PoolClient, candidateId: string, to: CandidateStatus, actorId: string, reason: string): Promise<void> {
    const current = await client.query<{ status: CandidateStatus }>(`SELECT status FROM civ_learning_candidates WHERE id = $1`, [candidateId]);
    const from = current.rows[0].status;
    if (from !== to && !TRANSITIONS[from]?.includes(to)) {
      throw new PublicHttpError(409, `illegal candidate transition ${from} -> ${to}`);
    }
    const event = await eventLog.appendWithClient(client, {
      event_type: 'learning.candidate_status_changed',
      actor_id: actorId,
      object_type: 'civ_learning_candidate',
      object_id: candidateId,
      correlation_id: crypto.randomUUID(),
      payload: { from_status: from, to_status: to, reason },
    });
    await client.query(`SELECT set_config('civilization.safe_evolution_authorized', 'true', true)`);
    await client.query(
      `UPDATE civ_learning_candidates SET status = $2, reject_reason = $3 WHERE id = $1`,
      [candidateId, to, to === 'rejected' ? reason : null]
    );
    await client.query(`SELECT set_config('civilization.safe_evolution_authorized', 'false', true)`);
    await client.query(
      `INSERT INTO civ_candidate_transitions (candidate_id, from_status, to_status, reason, actor_id, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6)`,
      [candidateId, from, to, reason, actorId, event.id]
    );
  }

  private async lock(client: PoolClient, candidateId: string): Promise<CandidateRecord> {
    const result = await client.query<CandidateRecord>(`SELECT ${CANDIDATE_COLUMNS} FROM civ_learning_candidates WHERE id = $1 FOR UPDATE`, [candidateId]);
    if ((result.rowCount ?? 0) !== 1) throw new PublicHttpError(404, `candidate not found: ${candidateId}`);
    return result.rows[0];
  }

  private async rootId(): Promise<string> {
    const root = await civilizationKernel.ensureCivilizationRoot();
    return root.id;
  }
}

export const safeEvolution = new SafeEvolutionService();
