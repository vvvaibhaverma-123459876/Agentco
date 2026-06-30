import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { capabilityExpansionGate, EvaluateCapabilityExpansionInput } from './capability-expansion-gate.service';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';
import { validateProtectedSurfaces } from './protected-surface-validator.service';

export interface PromoteSkillInput extends EvaluateCapabilityExpansionInput {}

export interface SkillPromotionRun {
  id: string;
  skill_version_id: string;
  capability_expansion_decision_id: string;
  protected_surface_result_json: Record<string, unknown>;
  status: string;
  event_log_id: string | null;
}

type SkillArtifactRow = {
  skill_version_id: string;
  candidate_id: string;
  artifact_json: Record<string, unknown>;
};

export class SkillPromotionLoopService {
  async promote(input: PromoteSkillInput): Promise<SkillPromotionRun> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const run = await this.promoteWithClient(client, input);
      await client.query('COMMIT');
      return run;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async promoteWithClient(client: PoolClient, input: PromoteSkillInput): Promise<SkillPromotionRun> {
    const skillArtifact = await this.loadCurrentSkillArtifact(client, input.skill_key);
    const protectedSurfaceResult = await validateProtectedSurfaces(
      skillArtifact.candidate_id,
      skillArtifact.artifact_json
    );
    const decision = await capabilityExpansionGate.evaluateWithClient(client, input);

    const existing = await client.query<SkillPromotionRun>(
      `SELECT id, skill_version_id, capability_expansion_decision_id,
              protected_surface_result_json, status, event_log_id
         FROM skill_promotion_loop_runs
        WHERE skill_version_id = $1
          AND capability_expansion_decision_id = $2
        LIMIT 1`,
      [skillArtifact.skill_version_id, decision.id]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];

    const runId = crypto.randomUUID();
    const actorId = await this.ensureServiceActor();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'vca.skill_promoted',
      actor_id: actorId,
      object_type: 'skill_promotion_loop_run',
      object_id: runId,
      correlation_id: input.correlation_id,
      payload: {
        skill_key: input.skill_key,
        domain_key: input.domain_key,
        skill_version_id: skillArtifact.skill_version_id,
        capability_expansion_decision_id: decision.id,
        protected_surface_valid: protectedSurfaceResult.valid,
      },
    });

    const inserted = await client.query<SkillPromotionRun>(
      `INSERT INTO skill_promotion_loop_runs
         (id, skill_version_id, capability_expansion_decision_id,
          protected_surface_result_json, status, event_log_id)
       VALUES ($1,$2,$3,$4::jsonb,'promoted',$5)
       RETURNING id, skill_version_id, capability_expansion_decision_id,
                 protected_surface_result_json, status, event_log_id`,
      [
        runId,
        skillArtifact.skill_version_id,
        decision.id,
        JSON.stringify(protectedSurfaceResult),
        event.id,
      ]
    );
    return inserted.rows[0];
  }

  private async loadCurrentSkillArtifact(client: PoolClient, skillKey: string): Promise<SkillArtifactRow> {
    const result = await client.query<SkillArtifactRow>(
      `SELECT v.id AS skill_version_id, v.candidate_id, a.artifact_json
         FROM skill_library_entries e
         JOIN skill_library_versions v ON v.id = e.current_version_id
         JOIN artifacts a ON a.id = v.artifact_id
        WHERE e.skill_key = $1
          AND e.status = 'active'
        LIMIT 1`,
      [skillKey.trim().toLowerCase().replace(/\s+/g, '_')]
    );
    if ((result.rowCount ?? 0) !== 1) {
      throw new Error(`active skill artifact not found: ${skillKey}`);
    }
    return result.rows[0];
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-skill-promotion-loop', [
      'vca.skill.promote',
    ]);
  }
}

export const skillPromotionLoop = new SkillPromotionLoopService();
