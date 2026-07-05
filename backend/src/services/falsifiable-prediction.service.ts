/**
 * Falsifiable Predictions (G2)
 * ============================
 * Replaces the tautological prediction path (constant probability 0.8,
 * outcome hardcoded true, resolved instantly from the claim's own snippet).
 * A prediction produced here:
 *
 *   - forecasts something NOT derivable from the evidence in hand: that an
 *     INDEPENDENT source (different host, different evidence row) will
 *     corroborate the claim's core assertion by a future due time;
 *   - carries a probability DERIVED from context (support depth, claim
 *     specificity, the producing agent's own calibration history) — never a
 *     constant;
 *   - records machine-checkable constraints in confidence_basis: disallowed
 *     source ids/hosts (the claim's own), the success pattern (core assertion
 *     tokens), an optional failure pattern, minimum overlap, and a due time;
 *   - can resolve TRUE (independent corroboration found), FALSE (failure
 *     pattern matched, or due time passed without corroboration), or stay
 *     OPEN — the resolver, not the producer, decides
 *     (independent-resolver.service.ts).
 *
 * Prediction types:
 *   independent_corroboration — an independent source will support the claim
 *   source_consistency        — a different fetch will repeat the assertion
 *   time_delayed_verification — a later check (after due time) will confirm
 * All three share the same constraint machinery; they differ in horizon and
 * in whether pre-registration evidence may count (time_delayed requires
 * evidence fetched AFTER registration).
 */

import crypto from 'crypto';
import { db } from '../db/client';
import { ledgerResolutionService } from './resolution-service.service';

export type FalsifiablePredictionType =
  | 'independent_corroboration'
  | 'source_consistency'
  | 'time_delayed_verification';

export interface FalsifiableConstraints {
  prediction_type: FalsifiablePredictionType;
  claim_id: string;
  /** evidence rows that produced the claim — may NEVER resolve it */
  disallowed_source_ids: string[];
  /** hosts of the producing evidence — an independent source needs a new host */
  disallowed_hosts: string[];
  /** normalized core-assertion tokens that qualifying evidence must cover */
  success_pattern: string[];
  /** optional normalized token phrase that resolves the prediction FALSE */
  failure_pattern: string[] | null;
  /** fraction of success_pattern tokens a snippet must contain */
  min_overlap: number;
  /** ISO time the prediction was registered (independence-in-time checks) */
  registered_at: string;
  /** evidence must postdate registration (time_delayed_verification only) */
  requires_post_registration_evidence: boolean;
}

export interface RegisterFalsifiableInput {
  claimId: string;
  claimText: string;
  supportSourceIds: string[];
  producingAgentId: string;
  domain: string;
  runId: string;
  predictionType?: FalsifiablePredictionType;
  /** milliseconds until the prediction is due (default 24h; may be negative in tests) */
  dueInMs?: number;
  failurePhrase?: string;
  correlationId?: string;
  historicalRegistrationReason?: string;
}

export const STOPWORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'with', 'is',
  'are', 'was', 'were', 'be', 'been', 'that', 'this', 'these', 'those', 'it',
  'its', 'as', 'at', 'by', 'from', 'has', 'have', 'had', 'will', 'can', 'not',
  // question/instruction words — they carry no subject matter, and keeping
  // them starved queries of salient tail tokens (G4)
  'what', 'how', 'why', 'when', 'where', 'who', 'whom', 'which', 'does', 'do',
  'did', 'say', 'says', 'said', 'about', 'into', 'over', 'under', 'their',
  'there', 'they', 'them', 'you', 'your', 'our', 'summarize', 'describe',
  'explain', 'research', 'investigate', 'analyze', 'report', 'review', 'find',
  'list', 'tell',
]);

export function normalizeTokens(value: string): string[] {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

/** Content-bearing tokens of a claim: its core assertion for matching. */
export function coreAssertionTokens(claimText: string, max = 12): string[] {
  const tokens = normalizeTokens(claimText).filter(t => !STOPWORDS.has(t) && t.length > 2);
  return tokens.slice(0, max);
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return url.toLowerCase();
  }
}

const DEFAULT_DUE_MS = 24 * 60 * 60 * 1000;

export class FalsifiablePredictionService {
  /**
   * Probability is a documented heuristic prior adjusted by the agent's own
   * calibration history — context-derived, never constant (G2):
   *   base 0.45
   *   + 0.08 per distinct supporting source (max 3)
   *   + 0.08 if the claim is specific (>= 8 content tokens)
   *   +/- up to 0.15 from the agent's latest brier_mean in this domain
   *   clamped to [0.15, 0.9]
   */
  async deriveProbability(input: {
    claimText: string;
    supportSourceCount: number;
    producingAgentId: string;
    domain: string;
  }): Promise<{ probability: number; basis: Record<string, unknown> }> {
    const specific = coreAssertionTokens(input.claimText, 40).length >= 8;
    let probability =
      0.45 + 0.08 * Math.min(input.supportSourceCount, 3) + (specific ? 0.08 : 0);

    let historyAdjustment = 0;
    const history = await db.query<{ brier_mean: string | null; n_resolved: number }>(
      `SELECT brier_mean, n_resolved FROM trust_scores
        WHERE subject_id = $1 AND domain = $2
        ORDER BY window_end DESC, computed_at DESC LIMIT 1`,
      [input.producingAgentId, input.domain]
    );
    const row = history.rows[0];
    if (row && row.brier_mean !== null && row.n_resolved > 0) {
      // brier_mean 0 (perfect) => +0.15; 0.25 (chance-ish) => 0; worse => negative
      historyAdjustment = Math.max(-0.15, Math.min(0.15, (0.25 - Number(row.brier_mean)) * 0.6));
      probability += historyAdjustment;
    }

    probability = Math.max(0.15, Math.min(0.9, Number(probability.toFixed(4))));
    return {
      probability,
      basis: {
        heuristic: 'v1',
        support_source_count: input.supportSourceCount,
        claim_specific: specific,
        history_adjustment: historyAdjustment,
      },
    };
  }

  /**
   * Register a falsifiable prediction for a grounded claim. The resolution
   * criterion is external to the claim's own evidence and has a real due
   * time; nothing in this call resolves anything.
   */
  async registerForClaim(input: RegisterFalsifiableInput): Promise<{
    predictionId: string;
    probability: number;
    constraints: FalsifiableConstraints;
    resolutionDate: Date;
  }> {
    const predictionType = input.predictionType ?? 'independent_corroboration';
    const dueInMs = input.dueInMs ?? DEFAULT_DUE_MS;
    const resolutionDate = new Date(Date.now() + dueInMs);

    const evidence = await db.query<{ source_id: string; url: string }>(
      `SELECT source_id, url FROM autonomy_evidence WHERE source_id = ANY($1::text[])`,
      [input.supportSourceIds]
    );
    const disallowedHosts = [...new Set(evidence.rows.map(r => hostOf(r.url)))];

    const successPattern = coreAssertionTokens(input.claimText);
    if (successPattern.length === 0) {
      throw new Error('claim has no content-bearing tokens; cannot form a falsifiable criterion');
    }

    const constraints: FalsifiableConstraints = {
      prediction_type: predictionType,
      claim_id: input.claimId,
      disallowed_source_ids: input.supportSourceIds,
      disallowed_hosts: disallowedHosts,
      success_pattern: successPattern,
      failure_pattern: input.failurePhrase ? normalizeTokens(input.failurePhrase) : null,
      min_overlap: 0.6,
      registered_at: new Date().toISOString(),
      requires_post_registration_evidence: predictionType === 'time_delayed_verification',
    };

    const { probability, basis } = await this.deriveProbability({
      claimText: input.claimText,
      supportSourceCount: input.supportSourceIds.length,
      producingAgentId: input.producingAgentId,
      domain: input.domain,
    });

    const predictionId = await ledgerResolutionService.registerPrediction({
      claim: `An independent source (host not in [${disallowedHosts.join(', ')}]) will corroborate: ${input.claimText}`,
      probability,
      confidence_basis: { ...basis, falsifiable: constraints },
      producing_agent_id: input.producingAgentId,
      producing_prompt_version: 'falsifiable-v1',
      resolution_criterion:
        `at maturity (${resolutionDate.toISOString()}): TRUE if evidence from a host outside ` +
        `[${disallowedHosts.join(', ')}] and outside the claim's own source rows contains ` +
        `>= ${constraints.min_overlap * 100}% of the claim's core assertion tokens; ` +
        `FALSE if the failure pattern matched or no such corroboration exists at maturity`,
      resolution_date: resolutionDate,
      ground_truth_source: `agentco://independent-resolver/${input.runId}`,
      horizon_class: dueInMs <= 60 * 60 * 1000 ? 'short' : 'medium',
      domain: input.domain,
      claim_type: predictionType,
      correlation_id: input.correlationId ?? crypto.randomUUID(),
      historical_registration_reason: input.historicalRegistrationReason,
    });

    return { predictionId, probability, constraints, resolutionDate };
  }
}

export const falsifiablePrediction = new FalsifiablePredictionService();
