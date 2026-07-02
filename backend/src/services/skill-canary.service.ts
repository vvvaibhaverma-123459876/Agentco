/**
 * Skill Canary Service
 * ====================
 * Bounded canary execution for evaluated candidates. Before any promotion,
 * the candidate's strategy is executed against a FRESH seed of the
 * deterministic benchmark (different tasks than evaluation used) under
 * explicit iteration and risk-tier bounds. Every canary run is persisted
 * with per-task usage logs and event lineage, and can fail honestly.
 *
 * Promotion elsewhere (SkillDeploymentService) requires a passed canary run;
 * a candidate cannot be promoted system-wide on evaluation results alone.
 */

import crypto from 'crypto';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';
import { deterministicBenchmark, TaskFamily } from './deterministic-benchmark.service';

export interface CanaryRun {
  id: string;
  candidateId: string;
  evaluationId: string | null;
  taskFamily: string;
  strategy: string;
  riskTier: string;
  maxIterations: number;
  iterationsUsed: number;
  baselineScore: number;
  canaryScore: number;
  improvement: number;
  passed: boolean;
  status: 'completed' | 'aborted';
  eventLogId: string | null;
}

const RISK_ITERATION_CAPS: Record<string, number> = {
  low: 50,
  medium: 25,
  high: 10,
  critical: 0, // critical-risk candidates may not canary without human approval
};

export class SkillCanaryService {
  async runCanary(input: {
    candidateId: string;
    maxIterations?: number;
    riskTier?: 'low' | 'medium' | 'high' | 'critical';
    seed?: number;
  }): Promise<CanaryRun> {
    const riskTier = input.riskTier ?? 'low';
    const cap = RISK_ITERATION_CAPS[riskTier] ?? 0;
    if (cap === 0) {
      throw new Error(`risk tier '${riskTier}' may not run an automated canary; human approval required`);
    }
    const maxIterations = Math.max(1, Math.min(input.maxIterations ?? 20, cap));

    const candidate = await db.query<{
      id: string;
      status: string;
      artifact_json: Record<string, unknown> | string;
      artifact_hash: string;
    }>(
      `SELECT id, status, artifact_json, artifact_hash
         FROM learner_candidates
        WHERE id = $1`,
      [input.candidateId]
    );
    if ((candidate.rowCount ?? 0) !== 1) {
      throw new Error(`learner candidate not found: ${input.candidateId}`);
    }
    if (candidate.rows[0].status !== 'evaluated') {
      throw new Error(
        `candidate ${input.candidateId} has status '${candidate.rows[0].status}'; only evaluated candidates may canary`
      );
    }

    const evaluation = await db.query<{ id: string; passed: boolean }>(
      `SELECT id, passed FROM candidate_evaluations
        WHERE candidate_id = $1
        ORDER BY created_at DESC
        LIMIT 1`,
      [input.candidateId]
    );
    if ((evaluation.rowCount ?? 0) !== 1 || !evaluation.rows[0].passed) {
      throw new Error(`candidate ${input.candidateId} has no passing evaluation; canary refused`);
    }

    const artifactRaw = candidate.rows[0].artifact_json;
    const artifact: Record<string, unknown> =
      typeof artifactRaw === 'string' ? JSON.parse(artifactRaw) : artifactRaw ?? {};
    const strategy = typeof artifact.strategy === 'string' ? artifact.strategy : null;
    const taskFamily =
      typeof artifact.taskFamily === 'string' ? (artifact.taskFamily as TaskFamily) : null;
    if (!strategy || !taskFamily) {
      throw new Error(`candidate ${input.candidateId} carries no executable strategy; canary refused`);
    }

    // Fresh seed distinct from evaluation (which seeds from the artifact hash
    // alone) so the canary is not a replay of the evaluation tasks.
    const seed =
      input.seed ??
      parseInt(
        crypto.createHash('sha256').update(`canary:${candidate.rows[0].artifact_hash}`).digest('hex').slice(0, 8),
        16
      );
    const benchmark = deterministicBenchmark.runBenchmark({
      family: taskFamily,
      strategy,
      iterations: maxIterations,
      seed,
    });

    const passed = benchmark.improvement > 0;
    const actorId = await this.ensureServiceActor();
    const event = await eventLog.append({
      event_type: passed ? 'skill.canary_passed' : 'skill.canary_failed',
      actor_id: actorId,
      object_type: 'skill_canary_run',
      object_id: input.candidateId,
      payload: {
        task_family: taskFamily,
        strategy,
        risk_tier: riskTier,
        iterations: benchmark.iterations,
        baseline_score: benchmark.baselineScore,
        canary_score: benchmark.strategyScore,
        improvement: benchmark.improvement,
        source: 'deterministic_benchmark',
      },
    });

    const inserted = await db.query<{ id: string }>(
      `INSERT INTO skill_canary_runs
         (candidate_id, evaluation_id, task_family, strategy, risk_tier,
          max_iterations, iterations_used, baseline_score, canary_score,
          improvement, passed, status, usage_log_json, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'completed',$12::jsonb,$13)
       RETURNING id`,
      [
        input.candidateId,
        evaluation.rows[0].id,
        taskFamily,
        strategy,
        riskTier,
        maxIterations,
        benchmark.iterations,
        benchmark.baselineScore,
        benchmark.strategyScore,
        benchmark.improvement,
        passed,
        JSON.stringify(benchmark.perTask),
        event.id,
      ]
    );

    return {
      id: inserted.rows[0].id,
      candidateId: input.candidateId,
      evaluationId: evaluation.rows[0].id,
      taskFamily,
      strategy,
      riskTier,
      maxIterations,
      iterationsUsed: benchmark.iterations,
      baselineScore: benchmark.baselineScore,
      canaryScore: benchmark.strategyScore,
      improvement: benchmark.improvement,
      passed,
      status: 'completed',
      eventLogId: event.id,
    };
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-skill-canary', [
      'learning.skill.canary',
    ]);
  }
}

export const skillCanary = new SkillCanaryService();
