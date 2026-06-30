import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface RegressionTestCase {
  id: string;
  candidate_id: string;
  learner_run_id: string;
  case_name: string;
  test_type: string;
  assertion_json: Record<string, unknown>;
  source_metrics_json: Record<string, unknown>;
  artifact_hash: string;
  event_log_id: string | null;
}

type CandidateRow = {
  id: string;
  learner_run_id: string;
  candidate_type: string;
  artifact_id: string;
  artifact_hash: string;
  metrics_before_json: Record<string, unknown> | string;
  metrics_after_json: Record<string, unknown> | string;
  expected_improvement_json: Record<string, unknown> | string;
  simulation_trained: boolean;
  status: string;
};

function asObject(value: Record<string, unknown> | string | null | undefined): Record<string, unknown> {
  if (!value) return {};
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return {};
    }
  }
  return value;
}

function metricNumber(metrics: Record<string, unknown>, key: string, fallback = 0): number {
  const value = metrics[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export class RegressionTestGeneratorService {
  async generateForCandidate(candidateId: string): Promise<RegressionTestCase[]> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const cases = await this.generateForCandidateWithClient(client, candidateId);
      await client.query('COMMIT');
      return cases;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async generateForCandidateWithClient(client: PoolClient, candidateId: string): Promise<RegressionTestCase[]> {
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(candidateId)) {
      throw new Error('candidateId must be a UUID');
    }

    const candidateResult = await client.query<CandidateRow>(
      `SELECT id, learner_run_id, candidate_type, artifact_id, artifact_hash,
              metrics_before_json, metrics_after_json, expected_improvement_json,
              simulation_trained, status
         FROM learner_candidates
        WHERE id = $1
        LIMIT 1`,
      [candidateId]
    );
    if ((candidateResult.rowCount ?? 0) !== 1) {
      throw new Error(`learner candidate not found: ${candidateId}`);
    }

    const candidate = candidateResult.rows[0];
    const metricsBefore = asObject(candidate.metrics_before_json);
    const metricsAfter = asObject(candidate.metrics_after_json);
    const expectedImprovement = asObject(candidate.expected_improvement_json);
    const casesToCreate = this.deriveCases(candidate, metricsBefore, metricsAfter, expectedImprovement);
    const inserted: RegressionTestCase[] = [];

    for (const testCase of casesToCreate) {
      const existing = await client.query<RegressionTestCase>(
        `SELECT id, candidate_id, learner_run_id, case_name, test_type, assertion_json,
                source_metrics_json, artifact_hash, event_log_id
           FROM candidate_regression_tests
          WHERE candidate_id = $1 AND case_name = $2
          LIMIT 1`,
        [candidate.id, testCase.case_name]
      );
      if ((existing.rowCount ?? 0) > 0) {
        inserted.push(existing.rows[0]);
        continue;
      }

      const event = await eventLog.appendWithClient(client, {
        event_type: 'regression_test.generated',
        actor_id: await this.ensureServiceActor(),
        object_type: 'learner_candidate',
        object_id: candidate.id,
        payload: {
          learner_run_id: candidate.learner_run_id,
          case_name: testCase.case_name,
          test_type: testCase.test_type,
          artifact_hash: candidate.artifact_hash,
        },
      });

      const row = await client.query<RegressionTestCase>(
        `INSERT INTO candidate_regression_tests
           (id, candidate_id, learner_run_id, case_name, test_type, assertion_json,
            source_metrics_json, artifact_hash, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb,$8,$9)
         RETURNING id, candidate_id, learner_run_id, case_name, test_type,
                   assertion_json, source_metrics_json, artifact_hash, event_log_id`,
        [
          crypto.randomUUID(),
          candidate.id,
          candidate.learner_run_id,
          testCase.case_name,
          testCase.test_type,
          JSON.stringify(testCase.assertion_json),
          JSON.stringify({ before: metricsBefore, after: metricsAfter, expected: expectedImprovement }),
          candidate.artifact_hash,
          event.id,
        ]
      );
      inserted.push(row.rows[0]);
    }

    return inserted;
  }

  private deriveCases(
    candidate: CandidateRow,
    metricsBefore: Record<string, unknown>,
    metricsAfter: Record<string, unknown>,
    expectedImprovement: Record<string, unknown>
  ): Array<{ case_name: string; test_type: string; assertion_json: Record<string, unknown> }> {
    const baselineSuccessRate = metricNumber(metricsBefore, 'success_rate', 0);
    const projectedScore = metricNumber(expectedImprovement, 'projectedScore', metricNumber(metricsAfter, 'projectedScore', 0));
    const baselineScore = metricNumber(metricsBefore, 'baseline_score', 0);

    return [
      {
        case_name: 'preserve_baseline_success_rate',
        test_type: 'metric_floor',
        assertion_json: {
          metric: 'success_rate',
          operator: '>=',
          threshold: baselineSuccessRate,
          source: 'metrics_before_json.success_rate',
        },
      },
      {
        case_name: 'projected_score_not_below_baseline',
        test_type: 'metric_floor',
        assertion_json: {
          metric: 'projectedScore',
          operator: '>=',
          threshold: baselineScore,
          observed_projected_score: projectedScore,
        },
      },
      {
        case_name: 'artifact_hash_stability',
        test_type: 'artifact_integrity',
        assertion_json: {
          artifact_id: candidate.artifact_id,
          artifact_hash: candidate.artifact_hash,
          candidate_type: candidate.candidate_type,
        },
      },
      {
        case_name: 'simulation_training_guard',
        test_type: 'simulation_guard',
        assertion_json: {
          simulation_trained: candidate.simulation_trained,
          requires_explicit_simulation_label: candidate.simulation_trained,
        },
      },
    ];
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-regression-test-generator', [
      'learning.regression_test.generate',
    ]);
  }
}

export const regressionTestGenerator = new RegressionTestGeneratorService();
