/**
 * Skill Retrieval Service
 * =======================
 * Consumer side of the skill promotion pipeline. Promotion writes
 * `skill_library_entries` / `skill_library_versions` rows and records a
 * `skill_promotion_loop_runs` row; retrieval surfaces only skills that
 * cleared the full promotion path so they can influence subsequent planning.
 *
 * A skill is retrievable only when ALL of the following hold:
 *   - the library entry is `active` (not suspended/retired)
 *   - the version is the entry's current version (not superseded)
 *   - the version is not retired
 *   - a `promoted` skill_promotion_loop_runs row exists for the version
 *   - a proof_of_competence row exists whose aggregate score cleared its
 *     threshold
 *   - the skill's declared risk tier does not exceed the run's permitted tier
 *
 * Skills are advisory context for the planner. They must never override
 * evidence-grounding or safety constraints; the planner prompt states this
 * explicitly and asks the model to cite skill ids it actually used so the
 * usage trail in `skill_usage_events` is honest.
 */

import { db } from '../db/client';
import { eventLog } from './event-log.service';

export type SkillRiskTier = 'low' | 'medium' | 'high' | 'critical';

const RISK_ORDER: Record<SkillRiskTier, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

export interface RetrievedSkill {
  skillVersionId: string;
  skillId: string;
  skillKey: string;
  displayName: string;
  version: string;
  domain: string | null;
  description: string;
  skillType: string;
  actionTypes: string[];
  riskTier: SkillRiskTier;
  proofScore: number;
  proofThreshold: number;
  usageConstraints: string | null;
  expectedBenefit: string | null;
  candidateId: string;
  artifactHash: string;
}

export interface SkillRetrievalQuery {
  goalText: string;
  domain?: string;
  taskType?: string;
  actionType?: string;
  agentRole?: string;
  maxRiskTier?: SkillRiskTier;
  limit?: number;
}

export interface SkillUsageRecord {
  skillVersionId: string;
  usage: 'used' | 'ignored' | 'rejected';
  goalId?: string;
  runId?: string;
  agentId?: string;
  actionId?: string;
  reason?: string;
  confidenceDelta?: number;
  outcome?: string;
}

type SkillRow = {
  skill_version_id: string;
  skill_id: string;
  skill_key: string;
  display_name: string;
  version: string;
  contract_json: Record<string, unknown>;
  artifact_hash: string;
  candidate_id: string;
  proof_score: string;
  proof_threshold: string;
};

function contractString(contract: Record<string, unknown>, key: string): string | null {
  const value = contract[key];
  return typeof value === 'string' && value.trim() !== '' ? value : null;
}

function contractStringArray(contract: Record<string, unknown>, key: string): string[] {
  const value = contract[key];
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === 'string');
}

function normalizeRiskTier(value: string | null): SkillRiskTier {
  if (value === 'medium' || value === 'high' || value === 'critical') return value;
  return 'low';
}

export class SkillRetrievalService {
  /**
   * Retrieve promoted, proven skills relevant to a planning step.
   * Ranking: domain match, then full-text relevance of the goal text against
   * the skill name/description, then proof score, then recency.
   */
  async retrieveForPlanning(query: SkillRetrievalQuery): Promise<RetrievedSkill[]> {
    const limit = Math.max(1, Math.min(query.limit ?? 5, 20));
    const maxRisk = RISK_ORDER[query.maxRiskTier ?? 'low'];

    const result = await db.query<SkillRow>(
      `SELECT v.id AS skill_version_id,
              e.id AS skill_id,
              e.skill_key,
              e.display_name,
              v.version,
              v.contract_json,
              v.artifact_hash,
              v.candidate_id,
              p.aggregate_score AS proof_score,
              p.threshold AS proof_threshold
         FROM skill_library_entries e
         JOIN skill_library_versions v
           ON v.id = e.current_version_id
         JOIN LATERAL (
              SELECT aggregate_score, threshold
                FROM proof_of_competence
               WHERE skill_version_id = v.id
                 AND aggregate_score >= threshold
               ORDER BY minted_at DESC
               LIMIT 1
         ) p ON TRUE
        WHERE e.status = 'active'
          AND v.status <> 'retired'
          AND EXISTS (
                SELECT 1 FROM skill_promotion_loop_runs r
                 WHERE r.skill_version_id = v.id
                   AND r.status = 'promoted'
          )
          AND (
                ($2::text IS NOT NULL AND v.contract_json->>'domain' = $2)
             OR to_tsvector('english', e.display_name || ' ' || COALESCE(v.contract_json->>'description', ''))
                @@ plainto_tsquery('english', $1)
          )
        ORDER BY
          (CASE WHEN $2::text IS NOT NULL AND v.contract_json->>'domain' = $2 THEN 1 ELSE 0 END) DESC,
          ts_rank(
            to_tsvector('english', e.display_name || ' ' || COALESCE(v.contract_json->>'description', '')),
            plainto_tsquery('english', $1)
          ) DESC,
          p.aggregate_score DESC,
          v.created_at DESC
        LIMIT $3`,
      [query.goalText, query.domain ?? null, limit * 3]
    );

    const skills: RetrievedSkill[] = [];
    for (const row of result.rows) {
      const contract = row.contract_json ?? {};
      const riskTier = normalizeRiskTier(contractString(contract, 'risk_tier'));
      const actionTypes = contractStringArray(contract, 'action_types');

      if (RISK_ORDER[riskTier] > maxRisk) {
        // Above the run's permitted tier: record honest rejection, do not surface.
        await this.recordUsage({
          skillVersionId: row.skill_version_id,
          usage: 'rejected',
          reason: `risk tier ${riskTier} exceeds permitted ${query.maxRiskTier ?? 'low'}`,
        });
        continue;
      }
      if (query.actionType && actionTypes.length > 0 && !actionTypes.includes(query.actionType)) {
        continue;
      }
      if (query.taskType) {
        const taskTypes = contractStringArray(contract, 'task_types');
        if (taskTypes.length > 0 && !taskTypes.includes(query.taskType)) continue;
      }
      if (query.agentRole) {
        const roles = contractStringArray(contract, 'agent_roles');
        if (roles.length > 0 && !roles.includes(query.agentRole)) continue;
      }

      skills.push({
        skillVersionId: row.skill_version_id,
        skillId: row.skill_id,
        skillKey: row.skill_key,
        displayName: row.display_name,
        version: row.version,
        domain: contractString(contract, 'domain'),
        description: contractString(contract, 'description') ?? row.display_name,
        skillType: contractString(contract, 'skill_type') ?? 'planner_prompt_strategy',
        actionTypes,
        riskTier,
        proofScore: Number(row.proof_score),
        proofThreshold: Number(row.proof_threshold),
        usageConstraints: contractString(contract, 'usage_constraints'),
        expectedBenefit: contractString(contract, 'expected_benefit'),
        candidateId: row.candidate_id,
        artifactHash: row.artifact_hash,
      });
      if (skills.length >= limit) break;
    }
    return skills;
  }

  /**
   * Format retrieved skills as an advisory prompt block. Empty string when
   * there is nothing to inject.
   */
  formatForPrompt(skills: RetrievedSkill[]): string {
    if (skills.length === 0) return '';
    const lines = skills.map((skill, index) => {
      const domain = skill.domain ? ` [${skill.domain}]` : '';
      const constraints = skill.usageConstraints ? ` Constraints: ${skill.usageConstraints}` : '';
      return (
        `${index + 1}. skill_id=${skill.skillVersionId} "${skill.displayName}" v${skill.version}` +
        `${domain} (type ${skill.skillType}, proof ${skill.proofScore.toFixed(2)}): ${skill.description}.${constraints}`
      );
    });
    return (
      `PROMOTED SKILLS (advisory strategies proven in prior runs):\n${lines.join('\n')}\n` +
      `Skill rules:\n` +
      `- Skills are ADVISORY. They must NOT override evidence requirements or safety rules.\n` +
      `- If a skill influenced your decision, include its skill_id in a "used_skill_ids" array in your JSON.\n` +
      `- Ignore skills that are not relevant to the current goal.`
    );
  }

  /**
   * Persist a skill usage decision with event-log provenance.
   * Failures here must not break planning; callers may fire-and-forget, but
   * the write itself is transactional and honest.
   */
  async recordUsage(record: SkillUsageRecord): Promise<string> {
    const event = await eventLog.append({
      event_type: 'skill.usage_recorded',
      actor_id: await this.ensureUsageActor(),
      object_type: 'skill_usage_event',
      object_id: record.skillVersionId,
      payload: {
        usage: record.usage,
        goal_id: record.goalId ?? null,
        run_id: record.runId ?? null,
        action_id: record.actionId ?? null,
        reason: record.reason ?? null,
      },
    });
    const inserted = await db.query<{ id: string }>(
      `INSERT INTO skill_usage_events
         (skill_version_id, goal_id, run_id, agent_id, action_id, usage, reason,
          confidence_delta, outcome, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
       RETURNING id`,
      [
        record.skillVersionId,
        record.goalId ?? null,
        record.runId ?? null,
        record.agentId ?? null,
        record.actionId ?? null,
        record.usage,
        record.reason ?? null,
        record.confidenceDelta ?? null,
        record.outcome ?? null,
        event.id,
      ]
    );
    return inserted.rows[0].id;
  }

  /**
   * Backfill the measured outcome on a usage event once the action resolves.
   */
  async recordOutcome(usageEventId: string, outcome: string, confidenceDelta?: number): Promise<void> {
    await db.query(
      `UPDATE skill_usage_events
          SET outcome = $2,
              confidence_delta = COALESCE($3, confidence_delta)
        WHERE id = $1`,
      [usageEventId, outcome, confidenceDelta ?? null]
    );
  }

  private usageActorId: string | null = null;

  private async ensureUsageActor(): Promise<string> {
    if (this.usageActorId) return this.usageActorId;
    const { ledgerResolutionService } = await import('./resolution-service.service');
    this.usageActorId = await ledgerResolutionService.ensureServiceActor('agentco-skill-retrieval', [
      'skill.usage.record',
    ]);
    return this.usageActorId;
  }
}

export const skillRetrieval = new SkillRetrievalService();
