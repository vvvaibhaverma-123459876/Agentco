/**
 * Independent Resolver (G2 / G3)
 * ==============================
 * The only autonomous path that resolves falsifiable predictions. It decides
 * TRUE / FALSE / stays-OPEN from evidence the prediction's producer did NOT
 * supply:
 *
 * A falsifiable prediction asks: "will independent corroboration exist by
 * the maturity time (resolution_date)?" The prediction-ledger DB trigger
 * enforces the time gate — nothing may resolve before maturity — so:
 *
 *   OPEN   — before maturity, always (DB-enforced); the resolver reports
 *            whether corroboration is already present or was refused as
 *            same-source, but touches nothing;
 *   TRUE   — at/after maturity, a qualifying INDEPENDENT evidence row
 *            (different host, not one of the claim's own source rows,
 *            relevant to the assertion) covers the success pattern;
 *   FALSE  — at/after maturity, the failure pattern matched, or no
 *            independent corroboration exists — the prediction was wrong.
 *
 * All resolutions go through the resolution_service DB-trigger firewall and
 * update persistent trust, so a wrong prediction WORSENS the producer's
 * calibration and routing rank — the system can now be wrong (G2) and pays
 * for it (G3 feeds Phase D demotion from false outcomes).
 */

import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { ledgerResolutionService } from './resolution-service.service';
import { persistentTrustScorer } from './persistent-trust-scorer.service';
import { beliefDemotion } from './belief-demotion.service';
import { eventLog } from './event-log.service';
import {
  FalsifiableConstraints,
  hostOf,
  normalizeTokens,
} from './falsifiable-prediction.service';

export interface ResolutionAttemptResult {
  predictionId: string;
  status: 'resolved_true' | 'resolved_false' | 'open' | 'refused';
  reason: string;
  resolvingSourceId?: string;
  brierScore?: number;
  trustFactor?: number;
}

interface CandidateEvidence {
  source_id: string;
  url: string;
  snippet: string | null;
  created_at: Date;
}

function overlapRatio(pattern: string[], snippetTokens: Set<string>): number {
  if (pattern.length === 0) return 0;
  let hits = 0;
  for (const token of pattern) if (snippetTokens.has(token)) hits += 1;
  return hits / pattern.length;
}

function containsPhrase(phrase: string[], snippetTokens: string[]): boolean {
  if (phrase.length === 0 || phrase.length > snippetTokens.length) return false;
  for (let start = 0; start <= snippetTokens.length - phrase.length; start += 1) {
    let ok = true;
    for (let i = 0; i < phrase.length; i += 1) {
      if (snippetTokens[start + i] !== phrase[i]) { ok = false; break; }
    }
    if (ok) return true;
  }
  return false;
}

export class IndependentResolverService {
  /**
   * Attempt to resolve one open falsifiable prediction from independent
   * evidence. `serviceClient` must be a resolution_service-role client — the
   * firewall stays the only write path.
   */
  async attemptResolution(input: {
    predictionId: string;
    serviceClient: PoolClient;
    /** restrict candidates to this goal's evidence; omit for global scope */
    goalId?: string;
    correlationId?: string;
  }): Promise<ResolutionAttemptResult> {
    const predRes = await db.query<{
      resolved: boolean;
      confidence_basis: Record<string, unknown>;
      resolution_date: Date;
      created_at: Date;
    }>(
      `SELECT resolved, confidence_basis, resolution_date, created_at
         FROM prediction_ledger WHERE prediction_id = $1`,
      [input.predictionId]
    );
    if ((predRes.rowCount ?? 0) !== 1) {
      return { predictionId: input.predictionId, status: 'refused', reason: 'prediction not found' };
    }
    const pred = predRes.rows[0];
    if (pred.resolved) {
      return { predictionId: input.predictionId, status: 'refused', reason: 'already resolved' };
    }
    const constraints = (pred.confidence_basis as any)?.falsifiable as FalsifiableConstraints | undefined;
    if (!constraints) {
      return {
        predictionId: input.predictionId,
        status: 'refused',
        reason: 'prediction carries no falsifiable constraints; refusing to resolve',
      };
    }

    const candidates = await this.candidateEvidence(input.goalId);
    const disallowedIds = new Set(constraints.disallowed_source_ids);
    const disallowedHosts = new Set(constraints.disallowed_hosts);
    const registeredAt = new Date(constraints.registered_at);

    let sawOnlyDependent = candidates.length > 0;
    let corroboration: { sourceId: string; ratio: number } | null = null;
    let failureMatch: string | null = null;
    for (const candidate of candidates) {
      // Independence gates: never the claim's own rows, never its hosts.
      if (disallowedIds.has(candidate.source_id)) continue;
      if (disallowedHosts.has(hostOf(candidate.url))) continue;
      if (
        constraints.requires_post_registration_evidence &&
        new Date(candidate.created_at) <= registeredAt
      ) continue;
      sawOnlyDependent = false;

      const snippetTokens = normalizeTokens(candidate.snippet ?? '');
      if (snippetTokens.length === 0) continue;

      if (
        constraints.failure_pattern &&
        containsPhrase(constraints.failure_pattern, snippetTokens)
      ) {
        failureMatch = candidate.source_id;
        break; // an explicit contradiction beats any corroboration
      }

      const ratio = overlapRatio(constraints.success_pattern, new Set(snippetTokens));
      if (ratio >= constraints.min_overlap && !corroboration) {
        corroboration = { sourceId: candidate.source_id, ratio };
      }
    }

    const mature = Date.now() >= new Date(pred.resolution_date).getTime();
    if (!mature) {
      // Time gate (DB-enforced): nothing resolves before maturity.
      if (sawOnlyDependent) {
        await this.appendRefusalEvent(input.predictionId,
          'all candidate evidence is same-source/same-host; self-confirmation refused');
        return {
          predictionId: input.predictionId,
          status: 'refused',
          reason: 'all candidate evidence is same-source/same-host; self-confirmation refused',
        };
      }
      return {
        predictionId: input.predictionId,
        status: 'open',
        reason: corroboration
          ? `corroboration present (${corroboration.sourceId}); awaiting maturity`
          : 'no qualifying independent evidence yet; maturity not reached',
      };
    }

    if (failureMatch) {
      return this.resolve(input, false,
        `independent source ${failureMatch} matches the failure pattern`, failureMatch);
    }
    if (corroboration) {
      return this.resolve(input, true,
        `independent source ${corroboration.sourceId} covers ${(corroboration.ratio * 100).toFixed(0)}% of the core assertion`,
        corroboration.sourceId);
    }
    return this.resolve(input, false,
      'maturity reached with no independent corroboration', undefined);
  }

  /**
   * Settle past debts: resolve OPEN falsifiable predictions whose due time
   * has passed. This is where the system's wrong predictions become FALSE
   * outcomes in normal operation (each autonomy run and the supervised
   * runtime call this).
   */
  async resolveDuePredictions(input: {
    serviceClient: PoolClient;
    producingAgentId?: string;
    limit?: number;
  }): Promise<{ considered: number; resolvedFalse: number; resolvedTrue: number }> {
    const limit = Math.max(1, Math.min(input.limit ?? 25, 100));
    const due = await db.query<{ prediction_id: string }>(
      `SELECT prediction_id FROM prediction_ledger
        WHERE resolved = false
          AND resolution_date < NOW()
          AND confidence_basis ? 'falsifiable'
          AND ($1::text IS NULL OR producing_agent_id = $1)
        ORDER BY resolution_date ASC
        LIMIT $2`,
      [input.producingAgentId ?? null, limit]
    );
    let resolvedFalse = 0;
    let resolvedTrue = 0;
    for (const row of due.rows) {
      const outcome = await this.attemptResolution({
        predictionId: row.prediction_id,
        serviceClient: input.serviceClient,
      });
      if (outcome.status === 'resolved_false') resolvedFalse += 1;
      if (outcome.status === 'resolved_true') resolvedTrue += 1;
    }
    return { considered: due.rowCount ?? 0, resolvedFalse, resolvedTrue };
  }

  private async candidateEvidence(goalId?: string): Promise<CandidateEvidence[]> {
    if (goalId) {
      const rows = await db.query<CandidateEvidence>(
        `SELECT e.source_id, e.url, e.snippet, e.created_at
           FROM autonomy_evidence e
           JOIN autonomy_goal_actions a ON a.action_id = e.action_id
          WHERE a.goal_id = $1
          ORDER BY e.created_at DESC
          LIMIT 200`,
        [goalId]
      );
      return rows.rows;
    }
    const rows = await db.query<CandidateEvidence>(
      `SELECT source_id, url, snippet, created_at
         FROM autonomy_evidence
        ORDER BY created_at DESC
        LIMIT 500`
    );
    return rows.rows;
  }

  private async resolve(
    input: { predictionId: string; serviceClient: PoolClient; correlationId?: string },
    outcome: boolean,
    reason: string,
    resolvingSourceId?: string
  ): Promise<ResolutionAttemptResult> {
    const correlationId = input.correlationId ?? crypto.randomUUID();
    const record = await ledgerResolutionService.resolveWithClient(input.serviceClient, {
      prediction_id: input.predictionId,
      resolved_outcome: outcome,
      resolved_by_service: 'independent_resolver',
      correlation_id: correlationId,
    });
    await ledgerResolutionService.recordResolutionEvent(record, correlationId);
    const trust = await persistentTrustScorer.computeForPrediction(input.predictionId, correlationId);
    if (!outcome) {
      // Being wrong has consequences (Phase D): contradict the claim and
      // demote every memory promoted from it.
      await beliefDemotion.demoteForFalsePrediction(input.predictionId, resolvingSourceId, reason);
    }
    return {
      predictionId: input.predictionId,
      status: outcome ? 'resolved_true' : 'resolved_false',
      reason,
      resolvingSourceId,
      brierScore: Number(record.brier_score),
      trustFactor: Number(trust.trust_factor),
    };
  }

  private async appendRefusalEvent(predictionId: string, reason: string): Promise<void> {
    try {
      const actorId = await ledgerResolutionService.ensureServiceActor(
        'agentco-independent-resolver',
        ['prediction.resolve']
      );
      await eventLog.append({
        event_type: 'prediction.resolution_refused',
        actor_id: actorId,
        object_type: 'prediction',
        object_id: predictionId,
        payload: { reason },
      });
    } catch (error) {
      console.error(`[IndependentResolver] failed to append refusal event: ${error}`);
    }
  }
}

export const independentResolver = new IndependentResolverService();
