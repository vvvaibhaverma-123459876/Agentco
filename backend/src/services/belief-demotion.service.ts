/**
 * Belief Demotion (G3 / Phase D)
 * ==============================
 * Closes the "learning from being wrong" half of the loop. When independent
 * evidence proves a prediction FALSE:
 *
 *   1. a contradiction record is appended (claim, prediction, evidence, why);
 *   2. the contradicted claim's status moves supported -> contradicted;
 *   3. every promoted memory built on that claim's predictions is demoted —
 *      appended to memory_demotions, never deleted — so default retrieval
 *      stops feeding it to the planner (memory-retrieval.service.ts);
 *   4. events are emitted for the judiciary and audit trail.
 *
 * History is preserved end-to-end: an auditor can reconstruct what was
 * believed, when it was contradicted, by which evidence, and what stopped
 * being used as a result.
 */

import crypto from 'crypto';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface DemotionOutcome {
  contradictionId: string | null;
  claimId: string | null;
  demotedMemoryIds: string[];
  claimContradicted: boolean;
}

const SERVICE = 'belief-demotion-service';

export class BeliefDemotionService {
  /**
   * React to a falsifiable prediction that resolved FALSE: contradict its
   * claim and demote all memories promoted from that claim's predictions.
   */
  async demoteForFalsePrediction(
    predictionId: string,
    contradictingSourceId?: string,
    reason = 'falsifiable prediction resolved false'
  ): Promise<DemotionOutcome> {
    const pred = await db.query<{ confidence_basis: Record<string, unknown> }>(
      `SELECT confidence_basis FROM prediction_ledger
        WHERE prediction_id = $1 AND resolved = true AND resolved_outcome = false`,
      [predictionId]
    );
    if ((pred.rowCount ?? 0) !== 1) {
      return { contradictionId: null, claimId: null, demotedMemoryIds: [], claimContradicted: false };
    }
    const claimId =
      ((pred.rows[0].confidence_basis as any)?.falsifiable?.claim_id as string | undefined) ?? null;

    const actorId = await ledgerResolutionService.ensureServiceActor(SERVICE, ['belief.demote']);
    const event = await eventLog.append({
      event_type: 'belief.contradicted',
      actor_id: actorId,
      object_type: 'prediction',
      object_id: predictionId,
      payload: { claim_id: claimId, contradicting_source_id: contradictingSourceId ?? null, reason },
    });

    const contradiction = await db.query<{ id: string }>(
      `INSERT INTO contradictions
         (claim_id, prediction_id, contradicting_source_id, reason, detected_by, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6)
       RETURNING id`,
      [claimId, predictionId, contradictingSourceId ?? null, reason, SERVICE, event.id]
    );
    const contradictionId = contradiction.rows[0].id;

    let claimContradicted = false;
    if (claimId) {
      const updated = await db.query(
        `UPDATE autonomy_claims SET status = 'contradicted'
          WHERE claim_id = $1 AND status = 'supported'`,
        [claimId]
      );
      claimContradicted = (updated.rowCount ?? 0) > 0;
    }

    // Every prediction ever registered for this claim, and the memories
    // promoted from them.
    const predictionIds = claimId
      ? (
          await db.query<{ prediction_id: string }>(
            `SELECT prediction_id FROM prediction_ledger
              WHERE confidence_basis->'falsifiable'->>'claim_id' = $1`,
            [claimId]
          )
        ).rows.map(r => r.prediction_id)
      : [predictionId];

    const demotedMemoryIds = await this.demoteMemoriesForPredictions(
      predictionIds,
      contradictionId,
      reason,
      actorId
    );

    return { contradictionId, claimId, demotedMemoryIds, claimContradicted };
  }

  /** Demote one memory directly (used by the judiciary). Idempotent. */
  async demoteMemory(input: {
    memoryId: string;
    reason: string;
    contradictionId?: string;
    demotedBy?: string;
  }): Promise<boolean> {
    const actorId = await ledgerResolutionService.ensureServiceActor(
      input.demotedBy ?? SERVICE,
      ['belief.demote']
    );
    const event = await eventLog.append({
      event_type: 'memory.demoted',
      actor_id: actorId,
      object_type: 'agent_memory',
      object_id: input.memoryId,
      payload: { reason: input.reason, contradiction_id: input.contradictionId ?? null },
    });
    const inserted = await db.query(
      `INSERT INTO memory_demotions (memory_id, contradiction_id, reason, demoted_by, event_log_id)
       VALUES ($1,$2,$3,$4,$5)
       ON CONFLICT (memory_id) DO NOTHING`,
      [input.memoryId, input.contradictionId ?? null, input.reason, input.demotedBy ?? SERVICE, event.id]
    );
    return (inserted.rowCount ?? 0) > 0;
  }

  /** Recent demotions relevant to a domain — planner warning context. */
  async recentDemotions(domain: string | null, limit = 3): Promise<
    Array<{ memoryId: string; summary: string; reason: string; demotedAt: Date }>
  > {
    const rows = await db.query<{
      memory_id: string;
      summary: string;
      reason: string;
      created_at: Date;
    }>(
      `SELECT d.memory_id, m.summary, d.reason, d.created_at
         FROM memory_demotions d
         JOIN agent_memories m ON m.id = d.memory_id
        WHERE $1::text IS NULL OR m.domain = $1
        ORDER BY d.created_at DESC
        LIMIT $2`,
      [domain, Math.max(1, Math.min(limit, 10))]
    );
    return rows.rows.map(r => ({
      memoryId: r.memory_id,
      summary: r.summary,
      reason: r.reason,
      demotedAt: r.created_at,
    }));
  }

  private async demoteMemoriesForPredictions(
    predictionIds: string[],
    contradictionId: string,
    reason: string,
    actorId: string
  ): Promise<string[]> {
    if (predictionIds.length === 0) return [];
    const memories = await db.query<{ id: string }>(
      `SELECT id FROM agent_memories WHERE prediction_id = ANY($1::text[])`,
      [predictionIds]
    );
    const demoted: string[] = [];
    for (const memory of memories.rows) {
      const event = await eventLog.append({
        event_type: 'memory.demoted',
        actor_id: actorId,
        object_type: 'agent_memory',
        object_id: memory.id,
        payload: { reason, contradiction_id: contradictionId },
      });
      const inserted = await db.query(
        `INSERT INTO memory_demotions (memory_id, contradiction_id, reason, demoted_by, event_log_id)
         VALUES ($1,$2,$3,$4,$5)
         ON CONFLICT (memory_id) DO NOTHING`,
        [memory.id, contradictionId, reason, SERVICE, event.id]
      );
      if ((inserted.rowCount ?? 0) > 0) demoted.push(memory.id);
    }
    return demoted;
  }
}

export const beliefDemotion = new BeliefDemotionService();
