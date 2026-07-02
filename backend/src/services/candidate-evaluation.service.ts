/**
 * Candidate Evaluation Service
 * ============================
 * Executes the generated regression cases for a ready_for_eval learner
 * candidate and measures the candidate's strategy against the baseline on
 * the deterministic benchmark. Persists a candidate_evaluations row, marks
 * the candidate evaluated/rejected, and emits event-log lineage.
 *
 * Default mode is deterministic (no LLM, no network). Live evaluation is
 * opt-in and refuses to run unless explicitly enabled, mirroring the
 * repo-wide RUN_REAL_LLM_TESTS convention.
 */

import crypto from 'crypto';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';
import {
  deterministicBenchmark,
  TaskFamily,
} from './deterministic-benchmark.service';

export interface CaseResult {
  caseName: string;
  testType: string;
  passed: boolean;
  detail: string;
}

export interface CandidateEvaluation {
  id: string;
  candidateId: string;
  evaluationMode: 'deterministic' | 'live';
  baselineMetrics: Record<string, unknown>;
  candidateMetrics: Record<string, unknown>;
  caseResults: CaseResult[];
  improvementDelta: number | null;
  passed: boolean;
  failureReason: string | null;
  eventLogId: string | null;
}

type CandidateRow = {
  id: string;
  learner_run_id: string;
  artifact_id: string;
  artifact_hash: string;
  artifact_json: Record<string, unknown> | string;
  metrics_before_json: Record<string, unknown>;
  metrics_after_json: Record<string, unknown>;
  expected_improvement_json: Record<string, unknown>;
  simulation_trained: boolean;
  status: string;
};

function parseArtifact(value: Record<string, unknown> | string): Record<string, unknown> {
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return {};
    }
  }
  return value ?? {};
}

function metricNumber(source: Record<string, unknown>, key: string, fallback: number): number {
  const value = source?.[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export class CandidateEvaluationService {
  /**
   * Evaluate all ready_for_eval candidates (bounded). Returns evaluations in
   * candidate creation order.
   */
  async evaluateReadyCandidates(limit = 10): Promise<CandidateEvaluation[]> {
    const rows = await db.query<{ id: string }>(
      `SELECT id FROM learner_candidates
        WHERE status = 'ready_for_eval'
        ORDER BY created_at ASC
        LIMIT $1`,
      [Math.max(1, Math.min(limit, 50))]
    );
    const evaluations: CandidateEvaluation[] = [];
    for (const row of rows.rows) {
      evaluations.push(await this.evaluateCandidate(row.id));
    }
    return evaluations;
  }

  async evaluateCandidate(
    candidateId: string,
    options: { mode?: 'deterministic' | 'live' } = {}
  ): Promise<CandidateEvaluation> {
    const mode = options.mode ?? 'deterministic';
    if (mode === 'live' && process.env.RUN_REAL_LLM_TESTS !== '1') {
      throw new Error(
        'live candidate evaluation is opt-in: set RUN_REAL_LLM_TESTS=1 with provider credentials'
      );
    }

    const candidateResult = await db.query<CandidateRow>(
      `SELECT id, learner_run_id, artifact_id, artifact_hash, artifact_json,
              metrics_before_json, metrics_after_json, expected_improvement_json,
              simulation_trained, status
         FROM learner_candidates
        WHERE id = $1`,
      [candidateId]
    );
    if ((candidateResult.rowCount ?? 0) !== 1) {
      throw new Error(`learner candidate not found: ${candidateId}`);
    }
    const candidate = candidateResult.rows[0];
    if (!['ready_for_eval', 'generated', 'created'].includes(candidate.status)) {
      throw new Error(
        `candidate ${candidateId} has status '${candidate.status}'; only pre-evaluation candidates can be evaluated`
      );
    }

    const artifact = parseArtifact(candidate.artifact_json);
    const caseResults = await this.executeRegressionCases(candidate);

    // Measured benchmark delta: only available when the candidate carries an
    // executable strategy. Projection-only candidates get no measured delta
    // and cannot pass on projections alone.
    let improvementDelta: number | null = null;
    let benchmarkDetail: Record<string, unknown> = {};
    const strategy = typeof artifact.strategy === 'string' ? artifact.strategy : null;
    const taskFamily = typeof artifact.taskFamily === 'string' ? (artifact.taskFamily as TaskFamily) : null;
    if (strategy && taskFamily) {
      const benchmark = deterministicBenchmark.runBenchmark({
        family: taskFamily,
        strategy,
        iterations: 40,
        seed: this.seedFor(candidate.artifact_hash),
      });
      improvementDelta = benchmark.improvement;
      benchmarkDetail = {
        family: benchmark.family,
        strategy: benchmark.strategy,
        baseline_score: benchmark.baselineScore,
        strategy_score: benchmark.strategyScore,
        iterations: benchmark.iterations,
        source: 'deterministic_benchmark',
      };
    }

    const casesPassed = caseResults.every(result => result.passed);
    const measuredImprovement = improvementDelta !== null && improvementDelta > 0;
    const passed = casesPassed && (strategy === null ? false : measuredImprovement);
    const failureReason = passed
      ? null
      : !casesPassed
        ? `regression cases failed: ${caseResults.filter(r => !r.passed).map(r => r.caseName).join(', ')}`
        : strategy === null
          ? 'candidate carries no executable strategy; projected improvements alone do not pass'
          : `measured improvement ${improvementDelta} is not positive`;

    const actorId = await this.ensureServiceActor();
    const event = await eventLog.append({
      event_type: passed ? 'learner.candidate_evaluation_passed' : 'learner.candidate_evaluation_failed',
      actor_id: actorId,
      object_type: 'candidate_evaluation',
      object_id: candidateId,
      payload: {
        mode,
        cases_passed: casesPassed,
        improvement_delta: improvementDelta,
        failure_reason: failureReason,
        ...benchmarkDetail,
      },
    });

    const inserted = await db.query<{ id: string }>(
      `INSERT INTO candidate_evaluations
         (candidate_id, evaluation_mode, baseline_metrics_json, candidate_metrics_json,
          case_results_json, improvement_delta, passed, failure_reason, event_log_id)
       VALUES ($1,$2,$3::jsonb,$4::jsonb,$5::jsonb,$6,$7,$8,$9)
       RETURNING id`,
      [
        candidateId,
        mode,
        JSON.stringify(candidate.metrics_before_json ?? {}),
        JSON.stringify({ ...(candidate.metrics_after_json ?? {}), ...benchmarkDetail }),
        JSON.stringify(caseResults),
        improvementDelta,
        passed,
        failureReason,
        event.id,
      ]
    );

    await db.query(`UPDATE learner_candidates SET status = $1 WHERE id = $2`, [
      passed ? 'evaluated' : 'rejected',
      candidateId,
    ]);

    return {
      id: inserted.rows[0].id,
      candidateId,
      evaluationMode: mode,
      baselineMetrics: candidate.metrics_before_json ?? {},
      candidateMetrics: { ...(candidate.metrics_after_json ?? {}), ...benchmarkDetail },
      caseResults,
      improvementDelta,
      passed,
      failureReason,
      eventLogId: event.id,
    };
  }

  /**
   * Execute the candidate's generated regression cases against current DB
   * state. Each case can fail honestly.
   */
  private async executeRegressionCases(candidate: CandidateRow): Promise<CaseResult[]> {
    const cases = await db.query<{
      case_name: string;
      test_type: string;
      assertion_json: Record<string, unknown>;
    }>(
      `SELECT case_name, test_type, assertion_json
         FROM candidate_regression_tests
        WHERE candidate_id = $1
        ORDER BY case_name`,
      [candidate.id]
    );
    if ((cases.rowCount ?? 0) === 0) {
      return [
        {
          caseName: 'regression_cases_present',
          testType: 'precondition',
          passed: false,
          detail: 'no generated regression cases found for candidate',
        },
      ];
    }

    const results: CaseResult[] = [];
    for (const testCase of cases.rows) {
      const assertion = testCase.assertion_json ?? {};
      if (testCase.test_type === 'metric_floor') {
        const metric = String(assertion.metric ?? '');
        const threshold = metricNumber(assertion, 'threshold', 0);
        const observed =
          metric === 'projectedScore'
            ? metricNumber(candidate.expected_improvement_json ?? {}, 'projectedScore', NaN)
            : metricNumber(candidate.metrics_after_json ?? {}, metric,
                metricNumber(candidate.metrics_before_json ?? {}, metric, NaN));
        const passed = Number.isFinite(observed) && observed >= threshold;
        results.push({
          caseName: testCase.case_name,
          testType: testCase.test_type,
          passed,
          detail: `metric ${metric}: observed ${observed} >= threshold ${threshold} -> ${passed}`,
        });
      } else if (testCase.test_type === 'artifact_integrity') {
        const linked = await db.query<{ artifact_hash: string; status: string }>(
          `SELECT artifact_hash, status FROM artifacts WHERE id = $1`,
          [candidate.artifact_id]
        );
        const expectedHash = String(assertion.artifact_hash ?? '');
        const passed =
          (linked.rowCount ?? 0) === 1 &&
          linked.rows[0].artifact_hash === expectedHash &&
          candidate.artifact_hash === expectedHash;
        results.push({
          caseName: testCase.case_name,
          testType: testCase.test_type,
          passed,
          detail: passed
            ? 'artifact linkage and hash consistent'
            : 'artifact hash mismatch between candidate, artifact row, and assertion',
        });
      } else if (testCase.test_type === 'simulation_guard') {
        const expected = Boolean(assertion.simulation_trained);
        const passed = candidate.simulation_trained === expected;
        results.push({
          caseName: testCase.case_name,
          testType: testCase.test_type,
          passed,
          detail: `simulation_trained persisted=${candidate.simulation_trained} expected=${expected}`,
        });
      } else {
        results.push({
          caseName: testCase.case_name,
          testType: testCase.test_type,
          passed: false,
          detail: `unknown regression test type: ${testCase.test_type}`,
        });
      }
    }
    return results;
  }

  private seedFor(artifactHash: string): number {
    return parseInt(crypto.createHash('sha256').update(artifactHash).digest('hex').slice(0, 8), 16);
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-candidate-evaluation', [
      'learning.candidate.evaluate',
    ]);
  }
}

export const candidateEvaluation = new CandidateEvaluationService();
