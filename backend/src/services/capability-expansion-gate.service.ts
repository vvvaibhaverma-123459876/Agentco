import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { generalityMetricTracker } from './generality-metric-tracker.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface EvaluateCapabilityExpansionInput {
  domain_key: string;
  skill_key: string;
  baseline_score: number;
  benchmark_name: string;
  evaluation_label?: string;
  metadata?: Record<string, unknown>;
  correlation_id?: string;
}

export interface CapabilityExpansionDecision {
  id: string;
  domain_id: string;
  domain_key: string;
  skill_id: string;
  skill_version_id: string;
  proof_id: string;
  generality_run_id: string;
  baseline_score: string | number;
  proof_score: string | number;
  decision: string;
  reason: string;
  event_log_id: string | null;
}

type DomainRow = { id: string; domain_key: string };
type SkillRow = { skill_id: string; skill_version_id: string; skill_key: string; version: string };
type ProofRow = { id: string; aggregate_score: string | number; evaluation_label: string };

function normalizeKey(value: string, field: string): string {
  const normalized = value.trim().toLowerCase().replace(/\s+/g, '_');
  if (!/^[a-z0-9][a-z0-9_-]{2,80}$/.test(normalized)) {
    throw new Error(`${field} must be 3-81 chars of lowercase letters, numbers, underscores, or hyphens`);
  }
  return normalized;
}

function validateScore(value: number, field: string): void {
  if (!Number.isFinite(value) || value < 0 || value > 1) {
    throw new Error(`${field} must be between 0 and 1`);
  }
}

export class CapabilityExpansionGateService {
  async evaluate(input: EvaluateCapabilityExpansionInput): Promise<CapabilityExpansionDecision> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.evaluateWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async evaluateWithClient(client: PoolClient, input: EvaluateCapabilityExpansionInput): Promise<CapabilityExpansionDecision> {
    const domainKey = normalizeKey(input.domain_key, 'domain_key');
    const skillKey = normalizeKey(input.skill_key, 'skill_key');
    if (!input.benchmark_name.trim()) throw new Error('benchmark_name is required');
    validateScore(input.baseline_score, 'baseline_score');

    const domain = await this.requireActiveDomain(client, domainKey);
    const skill = await this.requireCurrentSkill(client, skillKey);
    const proof = await this.requireProof(client, skill.skill_version_id, input.evaluation_label);
    const proofScore = Number(proof.aggregate_score);
    if (proofScore <= input.baseline_score) {
      throw new Error('capability expansion requires proof score above baseline');
    }

    const existing = await client.query<CapabilityExpansionDecision>(
      `SELECT id, domain_id, domain_key, skill_id, skill_version_id, proof_id,
              generality_run_id, baseline_score, proof_score, decision, reason, event_log_id
         FROM capability_expansion_decisions
        WHERE domain_id = $1
          AND skill_version_id = $2
          AND proof_id = $3
        LIMIT 1`,
      [domain.id, skill.skill_version_id, proof.id]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];

    const generality = await generalityMetricTracker.recordRunWithClient(client, {
      benchmark_name: input.benchmark_name,
      mode: 'proof_of_competence',
      baseline_score: input.baseline_score,
      domains: [{
        domain_key: domainKey,
        score: proofScore,
        evidence: {
          proof_id: proof.id,
          skill_key: skillKey,
          skill_version_id: skill.skill_version_id,
          evaluation_label: proof.evaluation_label,
        },
      }],
      metadata: {
        ...(input.metadata ?? {}),
        capability_expansion_gate: true,
      },
      correlation_id: input.correlation_id,
    });

    const decisionId = crypto.randomUUID();
    const actorId = await this.ensureServiceActor();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'capability.expansion_approved',
      actor_id: actorId,
      object_type: 'capability_expansion_decision',
      object_id: decisionId,
      correlation_id: input.correlation_id,
      payload: {
        domain_key: domainKey,
        skill_key: skillKey,
        skill_version_id: skill.skill_version_id,
        proof_id: proof.id,
        proof_score: proofScore,
        baseline_score: input.baseline_score,
        generality_run_id: generality.id,
      },
    });

    const inserted = await client.query<CapabilityExpansionDecision>(
      `INSERT INTO capability_expansion_decisions
         (id, domain_id, domain_key, skill_id, skill_version_id, proof_id, generality_run_id,
          baseline_score, proof_score, decision, reason, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'approved',$10,$11)
       RETURNING id, domain_id, domain_key, skill_id, skill_version_id, proof_id,
                 generality_run_id, baseline_score, proof_score, decision, reason, event_log_id`,
      [
        decisionId,
        domain.id,
        domainKey,
        skill.skill_id,
        skill.skill_version_id,
        proof.id,
        generality.id,
        input.baseline_score,
        proofScore,
        'verified competence proof beats baseline in active domain',
        event.id,
      ]
    );
    return inserted.rows[0];
  }

  private async requireActiveDomain(client: PoolClient, domainKey: string): Promise<DomainRow> {
    const result = await client.query<DomainRow>(
      `SELECT id, domain_key
         FROM domain_registry
        WHERE domain_key = $1
          AND status = 'active'
        LIMIT 1`,
      [domainKey]
    );
    if ((result.rowCount ?? 0) !== 1) {
      throw new Error(`active domain not found: ${domainKey}`);
    }
    return result.rows[0];
  }

  private async requireCurrentSkill(client: PoolClient, skillKey: string): Promise<SkillRow> {
    const result = await client.query<SkillRow>(
      `SELECT e.id AS skill_id, v.id AS skill_version_id, e.skill_key, v.version
         FROM skill_library_entries e
         JOIN skill_library_versions v ON v.id = e.current_version_id
        WHERE e.skill_key = $1
          AND e.status = 'active'
        LIMIT 1`,
      [skillKey]
    );
    if ((result.rowCount ?? 0) !== 1) {
      throw new Error(`active skill not found: ${skillKey}`);
    }
    return result.rows[0];
  }

  private async requireProof(client: PoolClient, skillVersionId: string, evaluationLabel?: string): Promise<ProofRow> {
    const params: unknown[] = [skillVersionId];
    let labelClause = '';
    if (evaluationLabel) {
      params.push(evaluationLabel);
      labelClause = `AND evaluation_label = $${params.length}`;
    }
    const result = await client.query<ProofRow>(
      `SELECT id, aggregate_score, evaluation_label
         FROM proof_of_competence
        WHERE skill_version_id = $1
          AND passed = true
          ${labelClause}
        ORDER BY minted_at DESC
        LIMIT 1`,
      params
    );
    if ((result.rowCount ?? 0) !== 1) {
      throw new Error('passing proof of competence not found for skill version');
    }
    return result.rows[0];
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-capability-expansion-gate', [
      'capability.expansion.evaluate',
    ]);
  }
}

export const capabilityExpansionGate = new CapabilityExpansionGateService();
