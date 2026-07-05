import crypto from 'crypto';
import { db } from '../db/client';
import { auditLog } from './audit-log.service';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface TrustScoreWindow {
  trust_id: string;
  subject_id: string;
  domain: string;
  claim_type: string;
  horizon_class: string;
  n_predictions: number;
  n_resolved: number;
  brier_mean: string | number;
  log_mean: string | number;
  ece: string | number | null;
  trust_factor: string | number;
  force_downgrade: boolean;
  downgrade_reason: string | null;
}

function trustFromBrier(brierMean: number, nResolved: number): number {
  const base = Math.max(0, Math.min(1, 1 - brierMean));
  const sampleConfidence = Math.min(1, nResolved / 20);
  return Number((0.5 * (1 - sampleConfidence) + base * sampleConfidence).toFixed(6));
}

async function computeEce(key: {
  producing_agent_id: string;
  domain: string;
  claim_type: string;
  horizon_class: string;
}): Promise<number | null> {
  const result = await db.query<{ ece: string | null; n: string }>(
    `WITH resolved AS (
       SELECT probability::float8 AS probability,
              CASE WHEN resolved_outcome THEN 1.0 ELSE 0.0 END AS actual,
              LEAST(FLOOR(probability::float8 * 10)::int, 9) AS bin
         FROM prediction_ledger
        WHERE producing_agent_id = $1
          AND domain = $2
          AND claim_type = $3
          AND horizon_class = $4
          AND post_hoc = false
          AND resolved = true
          AND resolved_outcome IS NOT NULL
     ),
     bins AS (
       SELECT bin,
              COUNT(*)::float8 AS bin_count,
              AVG(probability) AS mean_stated,
              AVG(actual) AS mean_actual
         FROM resolved
        GROUP BY bin
     ),
     total AS (
       SELECT COUNT(*)::float8 AS n FROM resolved
     )
     SELECT CASE WHEN total.n = 0 THEN NULL
                 ELSE SUM((bins.bin_count / total.n) * ABS(bins.mean_stated - bins.mean_actual))
            END::numeric AS ece,
            total.n::int::text AS n
       FROM bins CROSS JOIN total
      GROUP BY total.n`,
    [key.producing_agent_id, key.domain, key.claim_type, key.horizon_class]
  );
  const value = result.rows[0]?.ece;
  return value === null || value === undefined ? null : Number(value);
}

export class PersistentTrustScorerService {
  async computeForPrediction(predictionId: string, correlationId: string = crypto.randomUUID()): Promise<TrustScoreWindow> {
    const prediction = await db.query<{
      producing_agent_id: string;
      domain: string;
      claim_type: string;
      horizon_class: string;
    }>(
      `SELECT producing_agent_id, domain, claim_type, horizon_class
         FROM prediction_ledger
        WHERE prediction_id = $1 AND resolved = true AND post_hoc = false`,
      [predictionId]
    );
    if ((prediction.rowCount ?? 0) !== 1) {
      throw new Error(`resolved non-post-hoc prediction not found: ${predictionId}`);
    }
    const key = prediction.rows[0];

    const aggregate = await db.query<{
      n_predictions: string;
      n_resolved: string;
      brier_mean: string;
      log_mean: string;
    }>(
      `SELECT COUNT(*)::int AS n_predictions,
              COUNT(*) FILTER (WHERE resolved)::int AS n_resolved,
              AVG(brier_score) FILTER (WHERE resolved)::numeric AS brier_mean,
              AVG(log_score) FILTER (WHERE resolved)::numeric AS log_mean
         FROM prediction_ledger
        WHERE producing_agent_id = $1
          AND domain = $2
          AND claim_type = $3
          AND horizon_class = $4
          AND post_hoc = false`,
      [key.producing_agent_id, key.domain, key.claim_type, key.horizon_class]
    );
    const nResolved = Number(aggregate.rows[0].n_resolved);
    const brierMean = Number(aggregate.rows[0].brier_mean);
    const logMean = Number(aggregate.rows[0].log_mean);
    const ece = await computeEce(key);
    const trustFactor = trustFromBrier(brierMean, nResolved);
    const forceDowngrade = nResolved < 5 || brierMean > 0.25;
    const downgradeReason = nResolved < 5 ? 'sample_size_below_5' : brierMean > 0.25 ? 'brier_mean_above_0.25' : null;

    const inserted = await db.query<TrustScoreWindow>(
      `INSERT INTO trust_scores
         (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
          n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade, downgrade_reason)
       VALUES ($1,'agent',$2,$3,$4,NOW(),NOW(),$5,$6,$7,$8,$9,$10,$11,$12)
       RETURNING trust_id, subject_id, domain, claim_type, horizon_class, n_predictions,
                 n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade, downgrade_reason`,
      [
        key.producing_agent_id,
        key.domain,
        key.claim_type,
        key.horizon_class,
        Number(aggregate.rows[0].n_predictions),
        nResolved,
        brierMean,
        logMean,
        ece,
        trustFactor,
        forceDowngrade,
        downgradeReason,
      ]
    );

    const eventType = brierMean <= 0.25 ? 'accurate_prediction' : 'failed_prediction';
    await db.query(
      `INSERT INTO trust_reputation_ledger
         (entity_type, entity_id, event_type, context, impact_value, impact_confidence,
          source_ref, source_type, evidence_json, trace_id)
       VALUES ('agent',$1,$2,'real_world',$3,$4,$5,'prediction_ledger',$6::jsonb,$7)`,
      [
        key.producing_agent_id,
        eventType,
        brierMean <= 0.25 ? 1 : -1,
        Math.min(1, nResolved / 5),
        predictionId,
        JSON.stringify({ brier_mean: brierMean, ece, trust_factor: trustFactor }),
        correlationId,
      ]
    );

    const actorId = await ledgerResolutionService.ensureServiceActor('agentco-trust-scorer', ['trust.score']);
    const event = await eventLog.append({
      event_type: 'trust.score.computed',
      actor_id: actorId,
      object_type: 'trust_score',
      object_id: inserted.rows[0].trust_id,
      correlation_id: correlationId,
      payload: {
        prediction_id: predictionId,
        subject_id: key.producing_agent_id,
        trust_factor: trustFactor,
        force_downgrade: forceDowngrade,
      },
    });
    await auditLog.append({
      agent_id: actorId,
      action_type: 'event_published',
      input_summary: `compute trust for prediction ${predictionId}`,
      output_summary: `trust_factor=${trustFactor}`,
      confidence_score: 1,
      risk_level: forceDowngrade ? 'medium' : 'low',
      downstream_events: [event.id],
      session_id: correlationId,
    });

    return inserted.rows[0];
  }
}

export const persistentTrustScorer = new PersistentTrustScorerService();
