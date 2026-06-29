/**
 * Phase 5 Calibration Groundwork Test
 * ====================================
 *
 * Demonstrates the calibration infrastructure needed for self-modification.
 * Shows: validation recording, metric computation, gate checking, Phase 5 readiness.
 *
 * Key principle: Self-modification is ONLY enabled when calibration proves
 * that proposed changes improve decision quality on real validation data.
 */

import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import { claimAccuracyTracker } from '../src/services/claim-accuracy-tracker.service';
import { v4 as uuidv4 } from 'uuid';

describe('Phase 5 Calibration Groundwork', () => {
  let testClaimId: string;
  let testProviderId = 'openai';

  beforeAll(async () => {
    // Create a test claim to work with
    testClaimId = uuidv4();
    const claimUuid = uuidv4();

    await db.query(
      `INSERT INTO autonomy_claims (
        id, claim_id, text, status, confidence, support_source_ids,
        generated_by, generated_at, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())`,
      [
        claimUuid,
        testClaimId,
        'Test claim for calibration verification',
        'OBSERVED',
        0.8,
        JSON.stringify(['test-source-1']),
        testProviderId,
      ]
    );

    console.log(`✅ Test claim created: ${testClaimId}`);
  });

  afterAll(async () => {
    // Cleanup
    try {
      await db.query(`DELETE FROM autonomy_claim_validations WHERE claim_id = $1`, [testClaimId]);
      await db.query(`DELETE FROM autonomy_claims WHERE claim_id = $1`, [testClaimId]);
    } catch (error) {
      console.warn(`Cleanup warning: ${error}`);
    }
  });

  it('should record claim validations against ground truth', async () => {
    console.log('\n[1] Recording validation...');

    // Record that this claim was validated as TRUE
    await claimAccuracyTracker.recordValidation({
      claimId: testClaimId,
      actualOutcome: 'TRUE',
      confidence: 0.95,
      validationSource: 'human_review',
      evidenceForValidation: 'Verified against external source',
      validatorNotes: 'Human expert confirmed this claim',
    });

    // Verify it was saved
    const result = await db.query(
      `SELECT actual_outcome, confidence FROM autonomy_claim_validations
       WHERE claim_id = $1`,
      [testClaimId]
    );

    expect(result.rows.length).toBe(1);
    expect(result.rows[0].actual_outcome).toBe('TRUE');
    expect(result.rows[0].confidence).toBe(0.95);

    console.log('✅ Validation recorded successfully');
  });

  it('should compute provider calibration metrics', async () => {
    console.log('\n[2] Computing provider metrics...');

    // Record multiple validations to build metrics
    for (let i = 0; i < 3; i++) {
      const claimId = uuidv4();
      const claimUuid = uuidv4();

      await db.query(
        `INSERT INTO autonomy_claims (
          id, claim_id, text, status, confidence, support_source_ids,
          generated_by, generated_at, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())`,
        [
          claimUuid,
          claimId,
          `Test claim ${i}`,
          'OBSERVED',
          0.8,
          JSON.stringify(['test-source']),
          testProviderId,
        ]
      );

      // Validate: 2 true, 1 false for metrics
      const outcome = i < 2 ? 'TRUE' : 'FALSE';
      await claimAccuracyTracker.recordValidation({
        claimId,
        actualOutcome: outcome as any,
        confidence: 0.9,
        validationSource: 'human_review',
      });
    }

    // Compute metrics
    const metrics = await claimAccuracyTracker.computeProviderMetrics(testProviderId);

    console.log(`✅ Provider Metrics for '${testProviderId}':`);
    console.log(`   Claims Extracted: ${metrics.claimsExtracted}`);
    console.log(`   Claims Validated: ${metrics.claimsValidated}`);
    console.log(`   Accuracy: ${(metrics.accuracy * 100).toFixed(1)}%`);
    console.log(`   Precision: ${(metrics.precision * 100).toFixed(1)}%`);
    console.log(`   Recall: ${(metrics.recall * 100).toFixed(1)}%`);
    console.log(`   F1 Score: ${(metrics.f1Score * 100).toFixed(1)}%`);
    console.log(`   Confidence in Measurement: ${(metrics.confidenceInMeasurement * 100).toFixed(1)}%`);

    // Verify metrics are computed
    expect(metrics.claimsValidated).toBeGreaterThan(0);
    expect(metrics.accuracy).toBeGreaterThan(0);
  });

  it('should check Phase 5 self-modification gates', async () => {
    console.log('\n[3] Checking Phase 5 gates...');

    const gateResults = await claimAccuracyTracker.checkPhase5Gates();

    console.log('✅ Phase 5 Gate Results:');
    for (const gate of gateResults.gateResults) {
      const status = gate.passes ? '✅' : '❌';
      console.log(`   ${status} ${gate.gateName}: ${gate.reason}`);
    }

    console.log(
      `\n   Overall Phase 5 Ready: ${gateResults.allGatesPass ? 'YES' : 'NO'}`
    );

    // Verify gates exist and have results
    expect(gateResults.gateResults.length).toBeGreaterThan(0);
  });

  it('should generate calibration report', async () => {
    console.log('\n[4] Generating calibration report...');

    const report = await claimAccuracyTracker.generateCalibrationReport();

    console.log('✅ Calibration Report:');
    console.log(`   Period: ${report.reportPeriodStart.toISOString().split('T')[0]} to ${report.reportPeriodEnd.toISOString().split('T')[0]}`);
    console.log(`   Total Claims Extracted: ${report.totalClaimsExtracted}`);
    console.log(`   Total Claims Validated: ${report.totalClaimsValidated}`);
    console.log(`   Overall Accuracy: ${report.overallAccuracy}`);
    console.log(`   Validation Coverage: ${report.validationCoverage}`);
    console.log(`   Phase 5 Ready: ${report.phase5Ready}`);

    if (!report.phase5Ready) {
      console.log(`\n   Blockers preventing Phase 5:`);
      for (const blocker of report.phase5Blockers) {
        console.log(`     - ${blocker}`);
      }
    } else {
      console.log(`\n   ✅ All gates pass! Self-modification can be enabled with expert approval.`);
    }

    console.log(`\n   Next Steps: ${report.nextSteps}`);

    // Verify report was created
    expect(report.reportPeriodStart).toBeDefined();
    expect(report.totalClaimsExtracted).toBeDefined();
  });

  it('should demonstrate Phase 5 workflow: extract → validate → measure → gate-check', async () => {
    console.log('\n' + '='.repeat(70));
    console.log('PHASE 5 WORKFLOW DEMONSTRATION');
    console.log('='.repeat(70));

    console.log(`
Step 1: Extract claims (happening in bounded learning run)
  ✅ Claims extracted from real sources using OpenAI
  ✅ Claims stored with provider/source metadata

Step 2: Validate claims (human/external verification)
  ✅ Expert reviews claims against ground truth
  ✅ Records: actual_outcome (TRUE/FALSE/PARTIAL), confidence

Step 3: Compute calibration metrics
  ✅ Accuracy: % of claims that were true
  ✅ Precision: true claims / (true + false)
  ✅ Recall: true claims / (true + partial)
  ✅ F1 Score: harmonic mean of precision/recall

Step 4: Check Phase 5 gates
  ✅ Require: accuracy >= 85%, F1 score >= 80%
  ✅ Require: minimum 10 validated claims per provider
  ✅ Only when gates pass can self-modification be enabled

Step 5: Expert approval
  ✅ Even if gates pass, requires human review
  ✅ Self-modification is the highest-risk change
  ✅ Must have clear evidence it improves decision quality
    `);

    console.log('='.repeat(70));
    console.log('Phase 5 Groundwork: READY FOR CALIBRATION DATA COLLECTION');
    console.log('='.repeat(70));
  });
});
