/**
 * Skill Deployment Service
 * ========================
 * Final stage of the self-improvement loop. Promotes a candidate into the
 * skill library ONLY when its evaluation and canary both passed, using the
 * existing regression/proof/capability-expansion/promotion chain (no
 * shortcuts around protected-surface or capability gates). Provides an
 * explicit rollback path that retires the skill version and marks the
 * candidate rolled_back with event lineage.
 */

import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';
import { proofOfCompetence } from './proof-of-competence.service';
import { skillLibrary } from './skill-library.service';
import { skillPromotionLoop } from './skill-promotion-loop.service';

type EvaluationCaseResult = {
  caseName: string;
  testType: string;
  passed: boolean;
  detail: string;
};

export interface DeployResult {
  candidateId: string;
  skillVersionId: string;
  promotionRunId: string;
  status: 'promoted';
}

export interface RollbackResult {
  candidateId: string;
  skillVersionId: string | null;
  status: 'rolled_back';
}

function parseEvaluationCases(value: unknown): EvaluationCaseResult[] {
  const raw = typeof value === 'string' ? JSON.parse(value) : value;
  if (!Array.isArray(raw)) return [];
  return raw.map((row) => row as EvaluationCaseResult);
}

export class SkillDeploymentService {
  /**
   * Promote a canary-passed candidate into the skill library through the
   * full existing promotion chain.
   */
  async promoteCandidate(input: {
    candidateId: string;
    skillKey: string;
    domainKey: string;
    description: string;
    version?: string;
  }): Promise<DeployResult> {
    const gate = await db.query<{
      status: string;
      canary_passed: boolean | null;
      canary_score: number | null;
      baseline_score: number | null;
      artifact_json: Record<string, unknown> | string;
      evaluation_id: string | null;
      evaluation_passed: boolean | null;
      case_results_json: unknown;
    }>(
      `SELECT c.status,
              k.passed AS canary_passed,
              k.canary_score,
              k.baseline_score,
              c.artifact_json,
              e.id AS evaluation_id,
              e.passed AS evaluation_passed,
              e.case_results_json
         FROM learner_candidates c
         LEFT JOIN LATERAL (
              SELECT passed, canary_score, baseline_score
                FROM skill_canary_runs
               WHERE candidate_id = c.id
               ORDER BY created_at DESC
               LIMIT 1
         ) k ON TRUE
         LEFT JOIN LATERAL (
              SELECT id, passed, case_results_json
                FROM candidate_evaluations
               WHERE candidate_id = c.id
               ORDER BY created_at DESC
               LIMIT 1
         ) e ON TRUE
        WHERE c.id = $1`,
      [input.candidateId]
    );
    if ((gate.rowCount ?? 0) !== 1) {
      throw new Error(`learner candidate not found: ${input.candidateId}`);
    }
    const row = gate.rows[0];
    if (row.status !== 'evaluated') {
      throw new Error(`candidate ${input.candidateId} status '${row.status}' is not promotable`);
    }
    if (row.canary_passed !== true) {
      throw new Error(`candidate ${input.candidateId} has no passing canary run; promotion refused`);
    }
    if (row.evaluation_passed !== true || !row.evaluation_id) {
      throw new Error(`candidate ${input.candidateId} has no passing evaluator-owned regression result; promotion refused`);
    }

    const artifact: Record<string, unknown> =
      typeof row.artifact_json === 'string' ? JSON.parse(row.artifact_json) : row.artifact_json ?? {};

    const regressionCases = await db.query<{ id: string; case_name: string; test_type: string }>(
      `SELECT id, case_name, test_type FROM candidate_regression_tests WHERE candidate_id = $1`,
      [input.candidateId]
    );
    if ((regressionCases.rowCount ?? 0) === 0) {
      throw new Error(`candidate ${input.candidateId} has no regression coverage; promotion refused`);
    }
    const evaluationCases = parseEvaluationCases(row.case_results_json);
    const resultsByCase = new Map(evaluationCases.map((result) => [`${result.caseName}:${result.testType}`, result]));
    const proofResults = regressionCases.rows.map(caseRow => {
      const measured = resultsByCase.get(`${caseRow.case_name}:${caseRow.test_type}`);
      if (!measured) {
        throw new Error(`candidate ${input.candidateId} missing evaluator result for ${caseRow.case_name}`);
      }
      return {
        regression_test_id: caseRow.id,
        passed: measured.passed === true,
        score: measured.passed === true ? 1 : 0,
        evidence: {
          evaluator: 'candidate_evaluation_service',
          evaluation_id: row.evaluation_id,
          case_name: measured.caseName,
          test_type: measured.testType,
          detail: measured.detail,
        },
      };
    });
    if (proofResults.some(result => !result.passed)) {
      throw new Error(`candidate ${input.candidateId} has failing evaluator-owned regression results; promotion refused`);
    }

    const version = await skillLibrary.registerSkillVersion({
      skill_key: input.skillKey,
      version: input.version ?? '1.0.0',
      candidate_id: input.candidateId,
      contract: {
        inputs: ['goal'],
        outputs: ['plan'],
        domain: input.domainKey,
        description: input.description,
        skill_type: 'action_selection_policy',
        strategy: artifact.strategy ?? null,
        task_family: artifact.taskFamily ?? null,
        risk_tier: 'low',
        usage_constraints: 'Advisory only; never bypass evidence grounding or safety gates.',
        expected_benefit: `Measured canary improvement ${(Number(row.canary_score) - Number(row.baseline_score)).toFixed(3)} on deterministic benchmark.`,
      },
    });

    await proofOfCompetence.mintProof({
      skill_key: input.skillKey,
      evaluation_label: 'canary_promotion_eval',
      threshold: 1.0,
      results: proofResults,
    });

    const promotion = await skillPromotionLoop.promote({
      domain_key: input.domainKey,
      skill_key: input.skillKey,
      benchmark_name: 'deterministic_benchmark_canary',
      evaluation_label: 'canary_promotion_eval',
      baseline_score: Number(row.baseline_score),
    });
    if (promotion.status !== 'promoted') {
      throw new Error(`promotion loop blocked candidate ${input.candidateId}: ${promotion.status}`);
    }

    await db.query(`UPDATE learner_candidates SET status = 'promoted' WHERE id = $1`, [
      input.candidateId,
    ]);

    return {
      candidateId: input.candidateId,
      skillVersionId: version.id,
      promotionRunId: promotion.id,
      status: 'promoted',
    };
  }

  /**
   * Roll back a candidate (and its skill version, if one was registered).
   * Used when a canary fails after promotion pressure, or when a promoted
   * skill regresses during subsequent use.
   */
  async rollbackCandidate(candidateId: string, reason: string): Promise<RollbackResult> {
    const version = await db.query<{ id: string; skill_id: string }>(
      `SELECT id, skill_id FROM skill_library_versions WHERE candidate_id = $1`,
      [candidateId]
    );
    let skillVersionId: string | null = null;
    if ((version.rowCount ?? 0) === 1) {
      skillVersionId = version.rows[0].id;
      await db.query(`UPDATE skill_library_versions SET status = 'retired' WHERE id = $1`, [
        skillVersionId,
      ]);
      await db.query(
        `UPDATE skill_library_entries
            SET status = 'suspended', current_version_id = NULL, updated_at = NOW()
          WHERE id = $1`,
        [version.rows[0].skill_id]
      );
    }

    await db.query(`UPDATE learner_candidates SET status = 'rolled_back' WHERE id = $1`, [
      candidateId,
    ]);

    const actorId = await ledgerResolutionService.ensureServiceActor('agentco-skill-deployment', [
      'learning.skill.rollback',
    ]);
    await eventLog.append({
      event_type: 'skill.rolled_back',
      actor_id: actorId,
      object_type: 'learner_candidate',
      object_id: candidateId,
      payload: { reason, skill_version_id: skillVersionId },
    });

    return { candidateId, skillVersionId, status: 'rolled_back' };
  }
}

export const skillDeployment = new SkillDeploymentService();
