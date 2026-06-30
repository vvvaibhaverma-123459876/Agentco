import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface RegressionEvaluationResult {
  regression_test_id: string;
  passed: boolean;
  score: number;
  evidence?: Record<string, unknown>;
}

export interface MintProofInput {
  skill_key: string;
  version?: string;
  evaluation_label: string;
  threshold?: number;
  results: RegressionEvaluationResult[];
  correlation_id?: string;
}

export interface CompetenceProofRecord {
  id: string;
  skill_version_id: string;
  skill_id: string;
  evaluation_label: string;
  threshold: string | number;
  aggregate_score: string | number;
  passed: boolean;
  proof_hash: string;
  evaluation_json: Record<string, unknown>;
  event_log_id: string | null;
}

type SkillVersionRow = {
  id: string;
  skill_id: string;
  skill_key: string;
  version: string;
  artifact_hash: string;
  contract_json: Record<string, unknown>;
  regression_test_ids: string[];
};

function normalizeSkillKey(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/\s+/g, '_');
  if (!/^[a-z0-9][a-z0-9_-]{2,80}$/.test(normalized)) {
    throw new Error('skill_key must be 3-81 chars of lowercase letters, numbers, underscores, or hyphens');
  }
  return normalized;
}

function validateScore(value: number, field: string): void {
  if (!Number.isFinite(value) || value < 0 || value > 1) {
    throw new Error(`${field} must be between 0 and 1`);
  }
}

function stable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, nested]) => [key, stable(nested)])
    );
  }
  return value;
}

export class ProofOfCompetenceService {
  async mintProof(input: MintProofInput): Promise<CompetenceProofRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.mintProofWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async mintProofWithClient(client: PoolClient, input: MintProofInput): Promise<CompetenceProofRecord> {
    const skillKey = normalizeSkillKey(input.skill_key);
    const evaluationLabel = input.evaluation_label.trim();
    if (!evaluationLabel) throw new Error('evaluation_label is required');
    const threshold = input.threshold ?? 0.8;
    validateScore(threshold, 'threshold');
    if (!Array.isArray(input.results) || input.results.length === 0) {
      throw new Error('proof requires regression evaluation results');
    }

    const skillVersion = await this.requireSkillVersion(client, skillKey, input.version);
    const existing = await client.query<CompetenceProofRecord>(
      `SELECT id, skill_version_id, skill_id, evaluation_label, threshold,
              aggregate_score, passed, proof_hash, evaluation_json, event_log_id
         FROM proof_of_competence
        WHERE skill_version_id = $1
          AND evaluation_label = $2
        LIMIT 1`,
      [skillVersion.id, evaluationLabel]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];

    const normalizedResults = this.validateResults(skillVersion.regression_test_ids, input.results);
    const aggregateScore = normalizedResults.reduce((sum, result) => sum + result.score, 0) / normalizedResults.length;
    const passed = normalizedResults.every((result) => result.passed) && aggregateScore >= threshold;
    if (!passed) {
      throw new Error('proof of competence requires all regression results to pass and meet threshold');
    }

    const evaluation = {
      skill_key: skillKey,
      version: skillVersion.version,
      artifact_hash: skillVersion.artifact_hash,
      threshold,
      aggregate_score: Number(aggregateScore.toFixed(6)),
      results: normalizedResults,
    };
    const proofHash = crypto
      .createHash('sha256')
      .update(JSON.stringify(stable(evaluation)))
      .digest('hex');
    const proofId = crypto.randomUUID();
    const actorId = await this.ensureServiceActor();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'competence.proof_minted',
      actor_id: actorId,
      object_type: 'proof_of_competence',
      object_id: proofId,
      correlation_id: input.correlation_id,
      payload: {
        skill_key: skillKey,
        version: skillVersion.version,
        skill_version_id: skillVersion.id,
        threshold,
        aggregate_score: Number(aggregateScore.toFixed(6)),
        proof_hash: proofHash,
      },
    });

    const inserted = await client.query<CompetenceProofRecord>(
      `INSERT INTO proof_of_competence
         (id, skill_version_id, skill_id, evaluation_label, threshold, aggregate_score,
          passed, proof_hash, evaluation_json, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,true,$7,$8::jsonb,$9)
       RETURNING id, skill_version_id, skill_id, evaluation_label, threshold,
                 aggregate_score, passed, proof_hash, evaluation_json, event_log_id`,
      [
        proofId,
        skillVersion.id,
        skillVersion.skill_id,
        evaluationLabel,
        threshold,
        Number(aggregateScore.toFixed(6)),
        proofHash,
        JSON.stringify(evaluation),
        event.id,
      ]
    );
    return inserted.rows[0];
  }

  private async requireSkillVersion(client: PoolClient, skillKey: string, version?: string): Promise<SkillVersionRow> {
    const params: unknown[] = [skillKey];
    let versionClause = 'v.id = e.current_version_id';
    if (version) {
      params.push(version);
      versionClause = `v.version = $${params.length}`;
    }
    const result = await client.query<SkillVersionRow>(
      `SELECT v.id, v.skill_id, e.skill_key, v.version, v.artifact_hash,
              v.contract_json, v.regression_test_ids
         FROM skill_library_entries e
         JOIN skill_library_versions v ON v.skill_id = e.id
        WHERE e.skill_key = $1
          AND ${versionClause}
        LIMIT 1`,
      params
    );
    if ((result.rowCount ?? 0) !== 1) {
      throw new Error(`skill version not found: ${skillKey}${version ? `@${version}` : ''}`);
    }
    if (!Array.isArray(result.rows[0].regression_test_ids) || result.rows[0].regression_test_ids.length === 0) {
      throw new Error('skill version has no regression coverage');
    }
    return result.rows[0];
  }

  private validateResults(
    requiredTestIds: string[],
    results: RegressionEvaluationResult[]
  ): Array<Required<RegressionEvaluationResult>> {
    const required = new Set(requiredTestIds);
    const seen = new Set<string>();
    const normalized: Array<Required<RegressionEvaluationResult>> = [];
    for (const result of results) {
      if (!required.has(result.regression_test_id)) {
        throw new Error(`unexpected regression_test_id: ${result.regression_test_id}`);
      }
      if (seen.has(result.regression_test_id)) {
        throw new Error(`duplicate regression_test_id: ${result.regression_test_id}`);
      }
      validateScore(result.score, `score for ${result.regression_test_id}`);
      seen.add(result.regression_test_id);
      normalized.push({
        regression_test_id: result.regression_test_id,
        passed: result.passed,
        score: result.score,
        evidence: result.evidence ?? {},
      });
    }

    const missing = requiredTestIds.filter((id) => !seen.has(id));
    if (missing.length > 0) {
      throw new Error(`missing regression evaluation results: ${missing.join(', ')}`);
    }
    return normalized.sort((left, right) => left.regression_test_id.localeCompare(right.regression_test_id));
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-proof-of-competence', [
      'competence.proof.mint',
    ]);
  }
}

export const proofOfCompetence = new ProofOfCompetenceService();
