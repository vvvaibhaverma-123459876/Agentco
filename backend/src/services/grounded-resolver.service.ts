/**
 * Grounded Resolver (B4 / GA3)
 * ============================
 * Resolves an open prediction against REAL fetched evidence instead of a
 * seeded outcome. The resolution justification MUST itself pass the grounding
 * gate (token-subsequence of registered evidence) — an ungrounded
 * justification cannot resolve anything. Resolution always goes through the
 * existing `resolution_service` DB-trigger firewall (this service never
 * writes prediction outcomes directly), so the firewall stays the only write
 * path. If the outcome cannot be grounded, the prediction STAYS OPEN
 * (unresolvable != false).
 *
 * The caller supplies the resolution_service DB client (the role the firewall
 * requires); this service does not smuggle a privileged connection.
 */

import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { claimGrounding } from './claim-grounding.service';
import { ledgerResolutionService } from './resolution-service.service';
import { persistentTrustScorer } from './persistent-trust-scorer.service';

export interface GroundedResolutionInput {
  predictionId: string;
  /** registered evidence source ids the justification must be grounded in */
  evidenceSourceIds: string[];
  /** the boolean outcome the evidence supports */
  resolvedOutcome: boolean;
  /** a snippet asserting the outcome; must be a token-subsequence of evidence */
  justification: string;
  /** resolution_service-role client (the firewall requires this role) */
  serviceClient: PoolClient;
  correlationId?: string;
}

export interface GroundedResolutionResult {
  predictionId: string;
  resolved: boolean;
  resolvedOutcome: boolean | null;
  reason: string;
  trustFactor: number | null;
}

export class GroundedResolverService {
  async resolveFromEvidence(input: GroundedResolutionInput): Promise<GroundedResolutionResult> {
    // Prediction must exist and be open.
    const pred = await db.query<{ resolved: boolean; producing_agent_id: string; domain: string; claim_type: string }>(
      `SELECT resolved, producing_agent_id, domain, claim_type FROM prediction_ledger WHERE prediction_id = $1`,
      [input.predictionId]
    );
    if ((pred.rowCount ?? 0) !== 1) {
      return { predictionId: input.predictionId, resolved: false, resolvedOutcome: null, reason: 'prediction not found', trustFactor: null };
    }
    if (pred.rows[0].resolved) {
      return { predictionId: input.predictionId, resolved: false, resolvedOutcome: null, reason: 'prediction already resolved', trustFactor: null };
    }

    // The justification MUST be grounded in registered evidence. This is the
    // gate that stops fabricated resolutions — an outcome cannot be asserted
    // unless the fetched evidence actually contains the supporting text.
    const grounding = await claimGrounding.validate({
      claimText: input.justification,
      supportSourceIds: input.evidenceSourceIds,
      supportSnippets: [input.justification],
    });
    if (!grounding.valid) {
      // Unresolvable from this evidence — prediction stays OPEN.
      return {
        predictionId: input.predictionId,
        resolved: false,
        resolvedOutcome: null,
        reason: `justification not grounded in evidence: ${grounding.errors.join('; ')}`,
        trustFactor: null,
      };
    }

    // Resolve through the existing firewall (resolution_service role client).
    const correlationId = input.correlationId ?? crypto.randomUUID();
    const resolution = await ledgerResolutionService.resolveWithClient(input.serviceClient, {
      prediction_id: input.predictionId,
      resolved_outcome: input.resolvedOutcome,
      correlation_id: correlationId,
    });
    await ledgerResolutionService.recordResolutionEvent(resolution, correlationId);

    // Update calibration/trust from this REAL outcome.
    const trust = await persistentTrustScorer.computeForPrediction(input.predictionId, correlationId);

    return {
      predictionId: input.predictionId,
      resolved: true,
      resolvedOutcome: input.resolvedOutcome,
      reason: 'resolved from grounded evidence',
      trustFactor: Number(trust.trust_factor),
    };
  }
}

export const groundedResolver = new GroundedResolverService();
