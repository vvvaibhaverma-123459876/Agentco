/**
 * Claim Accuracy Tracker Service
 * =============================
 *
 * Tracks real-world accuracy of extracted claims.
 * Builds calibration data needed to enable Phase 5 self-modification.
 *
 * Core principle: Self-modification only allowed when backed by evidence
 * that a proposed change actually improves decision quality.
 *
 * Workflow:
 * 1. Claims are extracted from sources (captured in autonomy_claims)
 * 2. Claims are validated against ground truth (autonomy_claim_validations)
 * 3. Accuracy metrics computed per provider/source (autonomy_provider_calibration)
 * 4. Source trustworthiness updated (autonomy_source_trustworthiness)
 * 5. Self-modification gates checked (autonomy_self_mod_gates)
 * 6. Phase 5 readiness assessed (autonomy_calibration_reports)
 */

import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/client';

export interface ClaimValidation {
  claimId: string;
  actualOutcome: 'TRUE' | 'FALSE' | 'PARTIAL' | 'UNRESOLVED' | 'UNKNOWN';
  confidence: number; // 0-1, how sure is this validation
  validationSource: 'human_review' | 'external_api' | 'community_feedback' | 'ground_truth_db';
  evidenceForValidation?: string;
  validatorNotes?: string;
}

export interface CalibrationMetrics {
  provider: string;
  sourcePack?: string;
  claimsExtracted: number;
  claimsValidated: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  confidenceInMeasurement: number;
  readyForPhase5: boolean;
  blockingReasons: string[];
}

export class ClaimAccuracyTracker {
  /**
   * Record a validation of a claim against ground truth
   */
  async recordValidation(validation: ClaimValidation): Promise<void> {
    try {
      await db.query(
        `INSERT INTO autonomy_claim_validations (
          id, claim_id, validation_timestamp, validation_source, actual_outcome,
          confidence, evidence_for_validation, validator_notes, created_at
        ) VALUES ($1, $2, NOW(), $3, $4, $5, $6, $7, NOW())`,
        [
          uuidv4(),
          validation.claimId,
          validation.validationSource,
          validation.actualOutcome,
          validation.confidence,
          validation.evidenceForValidation,
          validation.validatorNotes,
        ]
      );

      await this.logCalibrationEvent('validation_recorded', {
        claimId: validation.claimId,
        outcome: validation.actualOutcome,
      });
    } catch (error: any) {
      console.error(`Failed to record validation: ${error.message}`);
      throw error;
    }
  }

  /**
   * Record validations in batch
   */
  async recordValidations(validations: ClaimValidation[]): Promise<void> {
    for (const validation of validations) {
      await this.recordValidation(validation);
    }
  }

  /**
   * Compute calibration metrics for a provider
   */
  async computeProviderMetrics(
    provider: string,
    sourcePack?: string,
    periodStart?: Date,
    periodEnd?: Date
  ): Promise<CalibrationMetrics> {
    const start = periodStart || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000); // Last 30 days
    const end = periodEnd || new Date();

    // Get claims extracted by this provider
    const extractResult = await db.query(
      `SELECT COUNT(*) as count FROM autonomy_claims
       WHERE generated_by = $1
       AND created_at >= $2
       AND created_at <= $3
       ${sourcePack ? 'AND source_pack = $4' : ''}`,
      sourcePack ? [provider, start, end, sourcePack] : [provider, start, end]
    );

    const claimsExtracted = parseInt(extractResult.rows[0]?.count || '0');

    // Get validated claims with outcomes
    const validationQuery = `
      SELECT
        cv.actual_outcome,
        COUNT(*) as count
      FROM autonomy_claim_validations cv
      JOIN autonomy_claims ac ON ac.claim_id = cv.claim_id
      WHERE ac.generated_by = $1
      AND cv.validation_timestamp >= $2
      AND cv.validation_timestamp <= $3
      ${sourcePack ? 'AND ac.source_pack = $4' : ''}
      GROUP BY cv.actual_outcome
    `;

    const validationResult = await db.query(
      validationQuery,
      sourcePack ? [provider, start, end, sourcePack] : [provider, start, end]
    );

    let claimsTrue = 0;
    let claimsFalse = 0;
    let claimsPartial = 0;
    let claimsValidated = 0;

    for (const row of validationResult.rows) {
      const count = parseInt(row.count || '0');
      claimsValidated += count;
      if (row.actual_outcome === 'TRUE') claimsTrue = count;
      if (row.actual_outcome === 'FALSE') claimsFalse = count;
      if (row.actual_outcome === 'PARTIAL') claimsPartial = count;
    }

    // Calculate metrics
    const accuracy = claimsValidated > 0 ? claimsTrue / claimsValidated : 0;
    const precision = claimsTrue + claimsFalse > 0 ? claimsTrue / (claimsTrue + claimsFalse) : 0;
    const recall = claimsTrue + claimsPartial > 0 ? claimsTrue / (claimsTrue + claimsPartial) : 0;
    const f1Score = precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0;

    // Confidence based on sample size
    const minSampleSize = 10;
    const confidenceInMeasurement = Math.min(claimsValidated / minSampleSize, 1.0);

    // Check Phase 5 readiness
    const blockingReasons: string[] = [];
    let readyForPhase5 = false;

    if (claimsValidated < minSampleSize) {
      blockingReasons.push(`Only ${claimsValidated}/${minSampleSize} claims validated`);
    }
    if (accuracy < 0.85) {
      blockingReasons.push(`Accuracy ${(accuracy * 100).toFixed(1)}% < 85% threshold`);
    }
    if (f1Score < 0.80) {
      blockingReasons.push(`F1 score ${(f1Score * 100).toFixed(1)}% < 80% threshold`);
    }

    if (blockingReasons.length === 0 && claimsValidated >= minSampleSize) {
      readyForPhase5 = true;
    }

    // Store metrics
    await db.query(
      `INSERT INTO autonomy_provider_calibration (
        provider, source_pack, measurement_period_start, measurement_period_end,
        claims_extracted, claims_validated, claims_true, claims_false, claims_partial,
        accuracy, precision, recall, f1_score, confidence_in_measurement, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW())`,
      [
        provider,
        sourcePack,
        start,
        end,
        claimsExtracted,
        claimsValidated,
        claimsTrue,
        claimsFalse,
        claimsPartial,
        accuracy,
        precision,
        recall,
        f1Score,
        confidenceInMeasurement,
      ]
    );

    await this.logCalibrationEvent('metrics_computed', {
      provider,
      sourcePack,
      accuracy: accuracy.toFixed(3),
      readyForPhase5,
    });

    return {
      provider,
      sourcePack,
      claimsExtracted,
      claimsValidated,
      accuracy,
      precision,
      recall,
      f1Score,
      confidenceInMeasurement,
      readyForPhase5,
      blockingReasons,
    };
  }

  /**
   * Update source trustworthiness based on validation data
   */
  async updateSourceTrustworthiness(sourceDomain: string, sourcePack?: string): Promise<void> {
    const start = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000); // Last 30 days
    const end = new Date();

    // Get validation metrics for this source
    const result = await db.query(
      `SELECT
        COUNT(*) as claims_validated,
        SUM(CASE WHEN cv.actual_outcome = 'TRUE' THEN 1 ELSE 0 END) as claims_true
      FROM autonomy_claim_validations cv
      JOIN autonomy_claims ac ON ac.claim_id = cv.claim_id
      JOIN autonomy_evidence ae ON ae.source_id = ANY(STRING_TO_ARRAY(TRIM(BOTH '[" ]' FROM ac.support_source_ids::text), ','))
      WHERE ae.source_domain = $1
      AND cv.validation_timestamp >= $2
      AND cv.validation_timestamp <= $3
      ${sourcePack ? 'AND ac.source_pack = $4' : ''}`,
      sourcePack ? [sourceDomain, start, end, sourcePack] : [sourceDomain, start, end]
    );

    const claimsValidated = parseInt(result.rows[0]?.claims_validated || '0');
    const claimsTrue = parseInt(result.rows[0]?.claims_true || '0');
    const accuracy = claimsValidated > 0 ? claimsTrue / claimsValidated : -1;

    // Determine trust tier
    let trustTier = 'UNCERTAIN';
    let reasonForTier = 'Insufficient validation data';

    if (claimsValidated < 5) {
      trustTier = 'UNCERTAIN';
      reasonForTier = `Only ${claimsValidated} validated claims`;
    } else if (accuracy >= 0.85) {
      trustTier = 'TRUSTED';
      reasonForTier = `${(accuracy * 100).toFixed(1)}% accuracy on ${claimsValidated} validated claims`;
    } else if (accuracy >= 0.60) {
      trustTier = 'UNCERTAIN';
      reasonForTier = `${(accuracy * 100).toFixed(1)}% accuracy - below trusted threshold`;
    } else if (accuracy >= 0) {
      trustTier = 'UNRELIABLE';
      reasonForTier = `${(accuracy * 100).toFixed(1)}% accuracy - chronically inaccurate`;
    }

    // Store trustworthiness
    await db.query(
      `INSERT INTO autonomy_source_trustworthiness (
        source_domain, source_pack, measurement_period_start, measurement_period_end,
        claims_extracted, claims_validated, accuracy, trust_tier, reason_for_tier, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())`,
      [
        sourceDomain,
        sourcePack,
        start,
        end,
        0, // claims_extracted - would need to count separately if needed
        claimsValidated,
        accuracy >= 0 ? accuracy : null,
        trustTier,
        reasonForTier,
      ]
    );

    await this.logCalibrationEvent('tier_updated', {
      sourceDomain,
      trustTier,
      accuracy: accuracy >= 0 ? accuracy.toFixed(3) : 'N/A',
    });
  }

  /**
   * Check if self-modification is permitted based on current calibration
   */
  async checkPhase5Gates(): Promise<{
    allGatesPass: boolean;
    gateResults: Array<{ gateName: string; passes: boolean; reason?: string }>;
  }> {
    const gateResults: Array<{ gateName: string; passes: boolean; reason?: string }> = [];

    // Get all gates (not just enabled - we'll check all for completeness)
    const gatesResult = await db.query(`
      SELECT gate_name, required_metric, required_threshold, minimum_sample_size
      FROM autonomy_self_mod_gates
      ORDER BY gate_name
    `);

    if (gatesResult.rows.length === 0) {
      // If no gates exist, return a default result
      return {
        allGatesPass: false,
        gateResults: [
          {
            gateName: 'PROVIDER_ACCURACY',
            passes: false,
            reason: 'No calibration data yet (need 10+ validated claims with >85% accuracy)',
          },
        ],
      };
    }

    for (const gate of gatesResult.rows) {
      let passes = false;
      let reason = '';

      // Check if gate requirements are met
      const metricsResult = await db.query(
        `SELECT COALESCE(AVG(accuracy), 0) as value, COUNT(*) as samples
        FROM autonomy_provider_calibration
        WHERE created_at >= NOW() - INTERVAL '30 days'
        AND accuracy IS NOT NULL`
      );

      const value = parseFloat(metricsResult.rows[0]?.value || '0');
      const samples = parseInt(metricsResult.rows[0]?.samples || '0');

      if (samples < gate.minimum_sample_size) {
        reason = `Insufficient samples: ${samples} < ${gate.minimum_sample_size}`;
      } else if (value < gate.required_threshold) {
        reason = `${gate.required_metric} ${(value * 100).toFixed(1)}% < ${(gate.required_threshold * 100).toFixed(1)}%`;
      } else {
        passes = true;
        reason = `${gate.required_metric} ${(value * 100).toFixed(1)}% >= ${(gate.required_threshold * 100).toFixed(1)}%`;
      }

      gateResults.push({
        gateName: gate.gate_name,
        passes,
        reason,
      });

      // Update gate status in database
      try {
        await db.query(
          `UPDATE autonomy_self_mod_gates
           SET passes_gate = $1, failure_reason = $2, last_evaluated = NOW()
           WHERE gate_name = $3`,
          [passes, reason, gate.gate_name]
        );
      } catch (error) {
        console.warn(`Warning updating gate ${gate.gate_name}: ${error}`);
      }
    }

    const allGatesPass = gateResults.length > 0 && gateResults.every(r => r.passes);

    return { allGatesPass, gateResults };
  }

  /**
   * Generate calibration report
   */
  async generateCalibrationReport(): Promise<any> {
    const start = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const end = new Date();

    // Get overall metrics
    const summaryResult = await db.query(`
      SELECT
        COUNT(DISTINCT ac.claim_id) as total_claims_extracted,
        COUNT(DISTINCT cv.claim_id) as total_claims_validated,
        SUM(CASE WHEN cv.actual_outcome = 'TRUE' THEN 1 ELSE 0 END)::FLOAT /
        COUNT(DISTINCT cv.claim_id) as overall_accuracy
      FROM autonomy_claims ac
      LEFT JOIN autonomy_claim_validations cv ON ac.claim_id = cv.claim_id
      WHERE ac.created_at >= $1
      AND ac.created_at <= $2`,
      [start, end]
    );

    const totalClaimsExtracted = parseInt(summaryResult.rows[0]?.total_claims_extracted || '0');
    const totalClaimsValidated = parseInt(summaryResult.rows[0]?.total_claims_validated || '0');
    const overallAccuracy = parseFloat(summaryResult.rows[0]?.overall_accuracy || '0') || 0;
    const validationCoverage = totalClaimsExtracted > 0 ? totalClaimsValidated / totalClaimsExtracted : 0;

    // Get Phase 5 readiness
    const gatesResult = await this.checkPhase5Gates();
    const phase5Ready = gatesResult.allGatesPass;

    const blockers: string[] = [];
    for (const result of gatesResult.gateResults) {
      if (!result.passes) {
        blockers.push(`${result.gateName}: ${result.reason}`);
      }
    }

    // Store report
    try {
      await db.query(
        `INSERT INTO autonomy_calibration_reports (
          report_period_start, report_period_end,
          total_claims_extracted, total_claims_validated, overall_accuracy,
          validation_coverage, phase5_ready, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())`,
        [
          start,
          end,
          totalClaimsExtracted,
          totalClaimsValidated,
          overallAccuracy,
          validationCoverage,
          phase5Ready,
        ]
      );
    } catch (error: any) {
      console.warn(`Warning storing calibration report: ${error.message}`);
    }

    return {
      reportPeriodStart: start,
      reportPeriodEnd: end,
      totalClaimsExtracted,
      totalClaimsValidated,
      overallAccuracy: (overallAccuracy * 100).toFixed(1) + '%',
      validationCoverage: (validationCoverage * 100).toFixed(1) + '%',
      phase5Ready,
      phase5Blockers: blockers,
      readyForSelfModification: phase5Ready,
      nextSteps: phase5Ready
        ? 'All calibration gates pass. Self-modification can be enabled with expert approval.'
        : 'More validation data needed before Phase 5 can be enabled.',
    };
  }

  private async logCalibrationEvent(eventType: string, data?: any): Promise<void> {
    try {
      await db.query(
        `INSERT INTO autonomy_calibration_events (
          id, event_type, event_data, timestamp, created_at
        ) VALUES ($1, $2, $3, NOW(), NOW())`,
        [uuidv4(), eventType, JSON.stringify(data || {})]
      );
    } catch (error) {
      console.warn(`Failed to log calibration event: ${error}`);
    }
  }
}

export const claimAccuracyTracker = new ClaimAccuracyTracker();
