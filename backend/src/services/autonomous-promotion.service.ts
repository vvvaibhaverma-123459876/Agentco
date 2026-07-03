/**
 * Autonomous Promotion (B3 / GA4)
 * ===============================
 * Closes observe -> promote WITHOUT a human. After an autonomy run, this
 * service finds the run's resolved predictions and invokes the EXISTING
 * memory-promotion pipeline on each — no new promotion logic, no weakened
 * gates. A resolved, scored prediction with a trust score qualifies; anything
 * else is rejected and the rejection is audited. Every decision is recorded in
 * `autonomous_promotions` with event lineage, so a bad run promotes nothing
 * and an auditor can see why.
 *
 * Idempotent: one decision per prediction (UNIQUE), so the post-run hook is
 * safe to re-run.
 */

import crypto from 'crypto';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';
import { MemoryPromotionPipelineService } from './memory-promotion-pipeline.service';

export interface AutonomousPromotionOutcome {
  predictionId: string;
  promoted: boolean;
  memoryId: string | null;
  reason: string;
}

export interface AutonomousPromotionSummary {
  runId: string;
  considered: number;
  promoted: number;
  rejected: number;
  outcomes: AutonomousPromotionOutcome[];
}

export class AutonomousPromotionService {
  private memoryPromotion = new MemoryPromotionPipelineService();

  /**
   * Promote qualifying resolved predictions produced by `agentId` during a run.
   * `agentId` scopes to the run's producer so a run only promotes its own
   * outcomes.
   */
  async promoteResolvedForRun(input: {
    runId: string;
    agentId: string;
    limit?: number;
  }): Promise<AutonomousPromotionSummary> {
    const limit = Math.max(1, Math.min(input.limit ?? 25, 100));
    const candidates = await db.query<{ prediction_id: string; resolved: boolean; brier_score: string | null }>(
      `SELECT prediction_id, resolved, brier_score
         FROM prediction_ledger
        WHERE producing_agent_id = $1
          AND post_hoc = false
          AND NOT EXISTS (
                SELECT 1 FROM autonomous_promotions ap WHERE ap.prediction_id = prediction_ledger.prediction_id
          )
        ORDER BY created_at ASC
        LIMIT $2`,
      [input.agentId, limit]
    );

    const outcomes: AutonomousPromotionOutcome[] = [];
    for (const row of candidates.rows) {
      outcomes.push(await this.evaluateAndRecord(input.runId, row.prediction_id, row.resolved, row.brier_score));
    }

    return {
      runId: input.runId,
      considered: outcomes.length,
      promoted: outcomes.filter(o => o.promoted).length,
      rejected: outcomes.filter(o => !o.promoted).length,
      outcomes,
    };
  }

  private async evaluateAndRecord(
    runId: string,
    predictionId: string,
    resolved: boolean,
    brierScore: string | null
  ): Promise<AutonomousPromotionOutcome> {
    const actorId = await ledgerResolutionService.ensureServiceActor('agentco-autonomous-promotion', [
      'autonomy.promotion.trigger',
    ]);

    // Threshold gate (uses the EXISTING pipeline's preconditions): only a
    // resolved, scored prediction is promotable. A bad/unresolved run promotes
    // nothing.
    if (!resolved || brierScore === null) {
      const reason = !resolved ? 'prediction not resolved' : 'prediction resolved but not scored';
      const event = await eventLog.append({
        event_type: 'autonomy.promotion_rejected',
        actor_id: actorId,
        object_type: 'autonomous_promotion',
        object_id: crypto.randomUUID(),
        payload: { run_id: runId, prediction_id: predictionId, reason },
      });
      await db.query(
        `INSERT INTO autonomous_promotions (run_id, prediction_id, memory_id, promoted, reason, threshold_note, event_log_id)
         VALUES ($1,$2,NULL,false,$3,'requires resolved + scored prediction',$4)
         ON CONFLICT (prediction_id) DO NOTHING`,
        [runId, predictionId, reason, event.id]
      );
      return { predictionId, promoted: false, memoryId: null, reason };
    }

    // Qualifies: invoke the EXISTING promotion pipeline (no manual human call).
    // The pipeline wants a UUID correlation id; the run id is preserved in the
    // audit row and the event payload.
    try {
      const result = await this.memoryPromotion.promoteResolvedPrediction(predictionId, crypto.randomUUID());
      const event = await eventLog.append({
        event_type: 'autonomy.promotion_triggered',
        actor_id: actorId,
        object_type: 'autonomous_promotion',
        object_id: result.memory_id,
        payload: { run_id: runId, prediction_id: predictionId, memory_id: result.memory_id },
      });
      await db.query(
        `INSERT INTO autonomous_promotions (run_id, prediction_id, memory_id, promoted, reason, threshold_note, event_log_id)
         VALUES ($1,$2,$3,true,'resolved+scored prediction auto-promoted','existing memory-promotion pipeline gate',$4)
         ON CONFLICT (prediction_id) DO NOTHING`,
        [runId, predictionId, result.memory_id, event.id]
      );
      return { predictionId, promoted: true, memoryId: result.memory_id, reason: 'auto-promoted' };
    } catch (error) {
      const reason = `promotion pipeline rejected: ${String(error).slice(0, 200)}`;
      const event = await eventLog.append({
        event_type: 'autonomy.promotion_rejected',
        actor_id: actorId,
        object_type: 'autonomous_promotion',
        object_id: crypto.randomUUID(),
        payload: { run_id: runId, prediction_id: predictionId, reason },
      });
      await db.query(
        `INSERT INTO autonomous_promotions (run_id, prediction_id, memory_id, promoted, reason, threshold_note, event_log_id)
         VALUES ($1,$2,NULL,false,$3,'existing pipeline gate rejected',$4)
         ON CONFLICT (prediction_id) DO NOTHING`,
        [runId, predictionId, reason, event.id]
      );
      return { predictionId, promoted: false, memoryId: null, reason };
    }
  }
}

export const autonomousPromotion = new AutonomousPromotionService();
