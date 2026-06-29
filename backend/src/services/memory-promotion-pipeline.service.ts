import crypto from 'crypto';
import { db } from '../db/client';
import { auditLog } from './audit-log.service';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface MemoryPromotionResult {
  memory_id: string;
  prediction_id: string;
  agent_id: string;
  promoted: boolean;
}

export class MemoryPromotionPipelineService {
  async promoteResolvedPrediction(predictionId: string, correlationId: string = crypto.randomUUID()): Promise<MemoryPromotionResult> {
    const prediction = await db.query<{
      prediction_id: string;
      claim: string;
      probability: string | number;
      producing_agent_id: string;
      domain: string;
      claim_type: string;
      resolved_outcome: boolean;
      brier_score: string | number;
    }>(
      `SELECT prediction_id, claim, probability, producing_agent_id, domain, claim_type,
              resolved_outcome, brier_score
         FROM prediction_ledger
        WHERE prediction_id = $1 AND resolved = true AND post_hoc = false`,
      [predictionId]
    );
    if ((prediction.rowCount ?? 0) !== 1) {
      throw new Error(`resolved non-post-hoc prediction not found: ${predictionId}`);
    }

    const trust = await db.query<{ trust_factor: string | number; force_downgrade: boolean; downgrade_reason: string | null }>(
      `SELECT trust_factor, force_downgrade, downgrade_reason
         FROM trust_scores
        WHERE subject_id = $1
          AND domain = $2
          AND claim_type = $3
        ORDER BY computed_at DESC
        LIMIT 1`,
      [prediction.rows[0].producing_agent_id, prediction.rows[0].domain, prediction.rows[0].claim_type]
    );
    if ((trust.rowCount ?? 0) !== 1) throw new Error(`trust score missing for prediction: ${predictionId}`);

    const row = prediction.rows[0];
    const trustRow = trust.rows[0];
    const correct = row.resolved_outcome ? Number(row.probability) >= 0.5 : Number(row.probability) < 0.5;
    const memoryId = crypto.randomUUID();
    const summary = `Prediction ${predictionId} resolved ${correct ? 'correctly' : 'incorrectly'} in ${row.domain}`;
    const content = {
      claim: row.claim,
      probability: Number(row.probability),
      resolved_outcome: row.resolved_outcome,
      brier_score: Number(row.brier_score),
      trust_factor: Number(trustRow.trust_factor),
      force_downgrade: trustRow.force_downgrade,
      downgrade_reason: trustRow.downgrade_reason,
    };

    await db.query(
      `INSERT INTO agent_memories
         (id, agent_id, memory_type, namespace, prediction_id, domain, summary, content, importance)
       VALUES ($1,$2,'prediction_lesson','calibration',$3,$4,$5,$6::jsonb,$7)`,
      [
        memoryId,
        row.producing_agent_id,
        predictionId,
        row.domain,
        summary,
        JSON.stringify(content),
        correct ? 0.7 : 0.9,
      ]
    );

    const actorId = await ledgerResolutionService.ensureServiceActor('agentco-memory-promotion', ['memory.promote']);
    const event = await eventLog.append({
      event_type: 'memory.promoted',
      actor_id: actorId,
      object_type: 'agent_memory',
      object_id: memoryId,
      correlation_id: correlationId,
      payload: { prediction_id: predictionId, agent_id: row.producing_agent_id, memory_type: 'prediction_lesson' },
    });
    await auditLog.append({
      agent_id: actorId,
      action_type: 'event_published',
      input_summary: `promote resolved prediction ${predictionId}`,
      output_summary: `memory_id=${memoryId}`,
      confidence_score: 1,
      risk_level: 'low',
      downstream_events: [event.id],
      session_id: correlationId,
    });

    return { memory_id: memoryId, prediction_id: predictionId, agent_id: row.producing_agent_id, promoted: true };
  }
}

export const memoryPromotionPipeline = new MemoryPromotionPipelineService();
