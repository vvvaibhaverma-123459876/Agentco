import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface RegisterSkillInput {
  skill_key: string;
  display_name?: string;
  version: string;
  candidate_id: string;
  contract: Record<string, unknown>;
  metrics?: Record<string, unknown>;
  correlation_id?: string;
}

export interface SkillVersionRecord {
  id: string;
  skill_id: string;
  skill_key: string;
  display_name: string;
  version: string;
  candidate_id: string;
  learner_run_id: string;
  artifact_id: string;
  artifact_hash: string;
  contract_json: Record<string, unknown>;
  regression_test_ids: string[];
  metrics_json: Record<string, unknown>;
  simulation_trained: boolean;
  status: string;
  event_log_id: string | null;
}

type CandidateRow = {
  id: string;
  learner_run_id: string;
  artifact_id: string;
  artifact_hash: string;
  candidate_type: string;
  status: string;
  simulation_trained: boolean;
};

function normalizeSkillKey(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/\s+/g, '_');
  if (!/^[a-z0-9][a-z0-9_-]{2,80}$/.test(normalized)) {
    throw new Error('skill_key must be 3-81 chars of lowercase letters, numbers, underscores, or hyphens');
  }
  return normalized;
}

function normalizeVersion(value: string): string {
  const normalized = value.trim();
  if (!/^[0-9]+(\.[0-9]+){0,2}([+-][a-zA-Z0-9._-]+)?$/.test(normalized)) {
    throw new Error('version must be a numeric semantic version such as 1.0.0');
  }
  return normalized;
}

function requireUuid(value: string, field: string): void {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error(`${field} must be a UUID`);
  }
}

export class SkillLibraryService {
  async registerSkillVersion(input: RegisterSkillInput): Promise<SkillVersionRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.registerSkillVersionWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async registerSkillVersionWithClient(client: PoolClient, input: RegisterSkillInput): Promise<SkillVersionRecord> {
    const skillKey = normalizeSkillKey(input.skill_key);
    const version = normalizeVersion(input.version);
    requireUuid(input.candidate_id, 'candidate_id');

    const existing = await client.query<SkillVersionRecord>(
      `SELECT v.id, v.skill_id, e.skill_key, e.display_name, v.version, v.candidate_id,
              v.learner_run_id, v.artifact_id, v.artifact_hash, v.contract_json,
              v.regression_test_ids, v.metrics_json, v.simulation_trained, v.status,
              v.event_log_id
         FROM skill_library_versions v
         JOIN skill_library_entries e ON e.id = v.skill_id
        WHERE v.candidate_id = $1
        LIMIT 1`,
      [input.candidate_id]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];

    const candidate = await this.requireCandidate(client, input.candidate_id);
    const regressionTestIds = await this.requireRegressionCoverage(client, candidate.id);
    const actorId = await this.ensureServiceActor();
    const skill = await this.ensureSkillEntry(client, {
      skillKey,
      displayName: input.display_name ?? skillKey.replace(/[_-]+/g, ' '),
      actorId,
    });

    const id = crypto.randomUUID();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'skill.version_registered',
      actor_id: actorId,
      object_type: 'skill_version',
      object_id: id,
      correlation_id: input.correlation_id,
      payload: {
        skill_key: skillKey,
        version,
        candidate_id: candidate.id,
        learner_run_id: candidate.learner_run_id,
        artifact_id: candidate.artifact_id,
        artifact_hash: candidate.artifact_hash,
        regression_test_count: regressionTestIds.length,
        simulation_trained: candidate.simulation_trained,
      },
    });

    const inserted = await client.query<SkillVersionRecord>(
      `INSERT INTO skill_library_versions
         (id, skill_id, version, candidate_id, learner_run_id, artifact_id, artifact_hash,
          contract_json, regression_test_ids, metrics_json, simulation_trained, status, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9::uuid[],$10::jsonb,$11,'candidate',$12)
       RETURNING id, skill_id, version, candidate_id, learner_run_id, artifact_id,
                 artifact_hash, contract_json, regression_test_ids, metrics_json,
                 simulation_trained, status, event_log_id`,
      [
        id,
        skill.id,
        version,
        candidate.id,
        candidate.learner_run_id,
        candidate.artifact_id,
        candidate.artifact_hash,
        JSON.stringify(input.contract),
        regressionTestIds,
        JSON.stringify(input.metrics ?? {}),
        candidate.simulation_trained,
        event.id,
      ]
    );

    await client.query(
      `UPDATE skill_library_entries
          SET current_version_id = $1,
              updated_at = now()
        WHERE id = $2`,
      [id, skill.id]
    );

    return {
      ...inserted.rows[0],
      skill_key: skillKey,
      display_name: skill.display_name,
    };
  }

  async getSkill(skillKey: string): Promise<SkillVersionRecord | null> {
    const result = await db.query<SkillVersionRecord>(
      `SELECT v.id, v.skill_id, e.skill_key, e.display_name, v.version, v.candidate_id,
              v.learner_run_id, v.artifact_id, v.artifact_hash, v.contract_json,
              v.regression_test_ids, v.metrics_json, v.simulation_trained, v.status,
              v.event_log_id
         FROM skill_library_entries e
         JOIN skill_library_versions v ON v.id = e.current_version_id
        WHERE e.skill_key = $1
        LIMIT 1`,
      [normalizeSkillKey(skillKey)]
    );
    return result.rows[0] ?? null;
  }

  private async requireCandidate(client: PoolClient, candidateId: string): Promise<CandidateRow> {
    const result = await client.query<CandidateRow>(
      `SELECT id, learner_run_id, artifact_id, artifact_hash, candidate_type, status, simulation_trained
         FROM learner_candidates
        WHERE id = $1
        LIMIT 1`,
      [candidateId]
    );
    if ((result.rowCount ?? 0) !== 1) {
      throw new Error(`learner candidate not found: ${candidateId}`);
    }
    const candidate = result.rows[0];
    if (!candidate.simulation_trained) {
      throw new Error('skill versions require simulation-trained candidates before competence evaluation');
    }
    if (!candidate.artifact_id || !candidate.artifact_hash) {
      throw new Error('learner candidate is missing artifact provenance');
    }
    return candidate;
  }

  private async requireRegressionCoverage(client: PoolClient, candidateId: string): Promise<string[]> {
    const result = await client.query<{ id: string; test_type: string }>(
      `SELECT id, test_type
         FROM candidate_regression_tests
        WHERE candidate_id = $1
        ORDER BY test_type, case_name`,
      [candidateId]
    );
    const testTypes = new Set(result.rows.map((row) => row.test_type));
    for (const required of ['metric_floor', 'artifact_integrity', 'simulation_guard']) {
      if (!testTypes.has(required)) {
        throw new Error(`skill version requires ${required} regression coverage`);
      }
    }
    return result.rows.map((row) => row.id);
  }

  private async ensureSkillEntry(
    client: PoolClient,
    input: { skillKey: string; displayName: string; actorId: string }
  ): Promise<{ id: string; display_name: string }> {
    const result = await client.query<{ id: string; display_name: string }>(
      `INSERT INTO skill_library_entries
         (skill_key, display_name, status, created_by_actor_id)
       VALUES ($1,$2,'active',$3)
       ON CONFLICT (skill_key) DO UPDATE
         SET display_name = skill_library_entries.display_name
       RETURNING id, display_name`,
      [input.skillKey, input.displayName, input.actorId]
    );
    return result.rows[0];
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-skill-library', [
      'learning.skill_library.register',
    ]);
  }
}

export const skillLibrary = new SkillLibraryService();
