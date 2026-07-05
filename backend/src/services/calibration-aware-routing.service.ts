/**
 * Calibration-Aware Routing Service
 * =================================
 * Turns stored calibration history (immutable trust_scores windows) into
 * runtime routing decisions so calibration actually drives planning instead
 * of sitting in the database:
 *
 *   - rank candidate agents for a domain/task by their latest calibration
 *     window (trust factor, Brier mean, ECE, overconfidence penalty,
 *     forced downgrades, recency)
 *   - flag demoted agents (repeated overconfident wrong predictions)
 *   - decide when extra verification is required before claims are trusted
 *
 * Every demotion emits an event-log record so authority changes are
 * auditable, and callers embed the calibration context into decision logs.
 */

import crypto from 'crypto';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface CalibrationProfile {
  agentId: string;
  domain: string;
  hasHistory: boolean;
  trustFactor: number;
  brierMean: number | null;
  ece: number | null;
  nResolved: number;
  forceDowngrade: boolean;
  overconfidencePenalty: number;
  routingScore: number;
  demoted: boolean;
  requiresVerification: boolean;
  reasonCodes: string[];
  windowEnd: Date | null;
}

export interface RankedAgents {
  domain: string;
  ranked: CalibrationProfile[];
  demoted: CalibrationProfile[];
}

const DEFAULT_TRUST = 0.5;
const DEMOTION_TRUST_THRESHOLD = 0.35;
const VERIFICATION_TRUST_THRESHOLD = 0.55;
const OVERCONFIDENT_BRIER_THRESHOLD = 0.35;

export class CalibrationAwareRoutingService {
  /**
   * Assess a single agent's calibration standing in a domain from its latest
   * resolved trust window. Absent history is treated as unproven (median
   * trust, verification required), never as trusted.
   */
  async assessAgent(agentId: string, domain: string): Promise<CalibrationProfile> {
    const result = await db.query<{
      trust_factor: string;
      brier_mean: string | null;
      ece: string | null;
      n_resolved: number;
      force_downgrade: boolean;
      window_end: Date;
    }>(
      `SELECT trust_factor, brier_mean, ece, n_resolved, force_downgrade, window_end
         FROM trust_scores
        WHERE subject_id = $1
          AND domain = $2
        ORDER BY window_end DESC, computed_at DESC
        LIMIT 1`,
      [agentId, domain]
    );

    if ((result.rowCount ?? 0) === 0) {
      return {
        agentId,
        domain,
        hasHistory: false,
        trustFactor: DEFAULT_TRUST,
        brierMean: null,
        ece: null,
        nResolved: 0,
        forceDowngrade: false,
        overconfidencePenalty: 0,
        routingScore: DEFAULT_TRUST * 0.5, // unproven agents rank below proven ones
        demoted: false,
        requiresVerification: true,
        reasonCodes: ['no_calibration_history'],
        windowEnd: null,
      };
    }

    const row = result.rows[0];
    const trustFactor = Number(row.trust_factor);
    const brierMean = row.brier_mean === null ? null : Number(row.brier_mean);
    const ece = row.ece === null ? null : Number(row.ece);
    const reasonCodes: string[] = [];

    // Overconfidence penalty: high Brier (wrong) combined with high ECE
    // (systematically miscalibrated) indicates confident wrongness.
    let overconfidencePenalty = 0;
    if (brierMean !== null && brierMean > OVERCONFIDENT_BRIER_THRESHOLD) {
      overconfidencePenalty += Math.min(0.3, brierMean - OVERCONFIDENT_BRIER_THRESHOLD);
      reasonCodes.push('high_brier');
    }
    if (row.n_resolved >= 5 && ece !== null && ece > 0.15) {
      overconfidencePenalty += Math.min(0.2, ece - 0.15);
      reasonCodes.push('high_ece');
    }
    if (row.force_downgrade) {
      reasonCodes.push('forced_downgrade');
    }

    const routingScore = Math.max(
      0,
      (row.force_downgrade ? trustFactor * 0.25 : trustFactor) - overconfidencePenalty
    );
    const demoted = row.force_downgrade || routingScore < DEMOTION_TRUST_THRESHOLD;
    if (demoted) reasonCodes.push('demoted_below_threshold');
    const requiresVerification = demoted || routingScore < VERIFICATION_TRUST_THRESHOLD;
    if (requiresVerification && !demoted) reasonCodes.push('verification_required_low_trust');
    if (reasonCodes.length === 0) reasonCodes.push('well_calibrated');

    return {
      agentId,
      domain,
      hasHistory: true,
      trustFactor,
      brierMean,
      ece,
      nResolved: row.n_resolved,
      forceDowngrade: row.force_downgrade,
      overconfidencePenalty,
      routingScore,
      demoted,
      requiresVerification,
      reasonCodes,
      windowEnd: row.window_end,
    };
  }

  /**
   * Rank candidate agents for work in a domain. Demoted agents are separated
   * out and an auditable demotion event is recorded for each.
   */
  async rankAgents(input: {
    domain: string;
    candidateAgentIds: string[];
    correlationId?: string;
  }): Promise<RankedAgents> {
    const profiles: CalibrationProfile[] = [];
    for (const agentId of input.candidateAgentIds) {
      profiles.push(await this.assessAgent(agentId, input.domain));
    }
    const ranked = profiles
      .filter(profile => !profile.demoted)
      .sort((a, b) => b.routingScore - a.routingScore);
    const demoted = profiles.filter(profile => profile.demoted);

    for (const profile of demoted) {
      await this.recordDemotion(profile, input.correlationId);
    }

    return { domain: input.domain, ranked, demoted };
  }

  /**
   * Format a calibration block for the planner prompt. Empty string when no
   * candidate agents were assessed.
   */
  formatForPrompt(ranking: RankedAgents): string {
    if (ranking.ranked.length === 0 && ranking.demoted.length === 0) return '';
    const lines: string[] = [
      `CALIBRATION RANKING for domain "${ranking.domain}" (from resolved prediction history; higher is better):`,
    ];
    ranking.ranked.forEach((profile, index) => {
      lines.push(
        `${index + 1}. agent=${profile.agentId} score=${profile.routingScore.toFixed(2)} ` +
          `trust=${profile.trustFactor.toFixed(2)} brier=${profile.brierMean ?? 'n/a'} ` +
          `[${profile.reasonCodes.join(',')}]${profile.requiresVerification ? ' REQUIRES-VERIFICATION' : ''}`
      );
    });
    for (const profile of ranking.demoted) {
      lines.push(
        `DEMOTED (do not delegate): agent=${profile.agentId} score=${profile.routingScore.toFixed(2)} ` +
          `[${profile.reasonCodes.join(',')}]`
      );
    }
    lines.push(
      'Calibration rules: prefer the highest-ranked agent for delegation; never delegate to DEMOTED agents; ' +
        'claims influenced by REQUIRES-VERIFICATION agents need independent verification before acceptance.'
    );
    return lines.join('\n');
  }

  private async recordDemotion(profile: CalibrationProfile, correlationId?: string): Promise<void> {
    const actorId = await ledgerResolutionService.ensureServiceActor('agentco-calibration-routing', [
      'calibration.routing.demote',
    ]);
    await eventLog.append({
      event_type: 'calibration.agent_demoted',
      actor_id: actorId,
      object_type: 'agent_calibration',
      object_id: crypto.randomUUID(),
      correlation_id: correlationId,
      payload: {
        agent_id: profile.agentId,
        domain: profile.domain,
        routing_score: profile.routingScore,
        trust_factor: profile.trustFactor,
        brier_mean: profile.brierMean,
        ece: profile.ece,
        reason_codes: profile.reasonCodes,
      },
    });
  }
}

export const calibrationAwareRouting = new CalibrationAwareRoutingService();
