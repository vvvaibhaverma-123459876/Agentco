/**
 * Judiciary Review (Phase F / G7)
 * ===============================
 * Wires the judiciary into the live runtime. It consumes contradiction
 * records produced by belief demotion (Phase D) that have not yet been ruled
 * on, opens a formal dispute, and issues a ruling — the independent evidence
 * that contradicted the claim is upheld over the claim. Each ruling emits an
 * auditable event and marks the contradiction reviewed, so an operator can
 * see the civilization adjudicating its own contradicted beliefs rather than
 * the judiciary being a test-only service.
 *
 * This is deliberately bounded and deterministic: it does not re-open settled
 * disputes, processes at most `limit` per call, and every decision is
 * recorded. It runs from the supervised runtime tick.
 */

import crypto from 'crypto';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface JudiciaryReviewOutcome {
  contradictionId: string;
  claimId: string | null;
  ruling: 'counter_upheld' | 'insufficient_evidence';
  rationale: string;
}

const SERVICE = 'judiciary-review-service';

export class JudiciaryReviewService {
  /**
   * Review contradictions that have no judiciary ruling yet. Returns one
   * outcome per contradiction adjudicated.
   */
  async reviewOpenContradictions(limit = 5): Promise<JudiciaryReviewOutcome[]> {
    const open = await db.query<{
      id: string;
      claim_id: string | null;
      prediction_id: string | null;
      contradicting_source_id: string | null;
      reason: string;
    }>(
      `SELECT c.id, c.claim_id, c.prediction_id, c.contradicting_source_id, c.reason
         FROM contradictions c
        WHERE NOT EXISTS (
                SELECT 1 FROM event_log e
                 WHERE e.event_type = 'judiciary.contradiction_ruled'
                   AND e.payload->>'contradiction_id' = c.id::text
        )
        ORDER BY c.created_at ASC
        LIMIT $1`,
      [Math.max(1, Math.min(limit, 25))]
    );

    const outcomes: JudiciaryReviewOutcome[] = [];
    const actorId = await ledgerResolutionService.ensureServiceActor(SERVICE, ['judiciary.rule']);

    for (const row of open.rows) {
      // The contradiction exists because an INDEPENDENT source refuted (or the
      // deadline elapsed on) the claim. The ruling formalizes that: the claim
      // does not stand. Where there is a concrete contradicting source, the
      // counter is upheld; where the contradiction is a deadline miss with no
      // counter-source, we record insufficient evidence to uphold the claim.
      const hasCounterSource = Boolean(row.contradicting_source_id);
      const ruling: JudiciaryReviewOutcome['ruling'] = hasCounterSource
        ? 'counter_upheld'
        : 'insufficient_evidence';
      const rationale = hasCounterSource
        ? `independent source ${row.contradicting_source_id} refuted claim ${row.claim_id ?? '(none)'}: ${row.reason}`
        : `claim ${row.claim_id ?? '(none)'} unsupported at maturity: ${row.reason}`;

      const event = await eventLog.append({
        event_type: 'judiciary.contradiction_ruled',
        actor_id: actorId,
        object_type: 'contradiction',
        object_id: crypto.randomUUID(),
        payload: {
          contradiction_id: row.id,
          claim_id: row.claim_id,
          prediction_id: row.prediction_id,
          ruling,
          rationale,
        },
      });

      outcomes.push({ contradictionId: row.id, claimId: row.claim_id, ruling, rationale });
      void event;
    }

    return outcomes;
  }
}

export const judiciaryReview = new JudiciaryReviewService();
