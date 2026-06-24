#!/usr/bin/env npx ts-node
/**
 * Phase 0b: Pre-Register Predictions
 *
 * This script pre-registers 17 predictions about AgentCo's autonomy loop behavior.
 * It must be run BEFORE any predictions are resolved.
 * The git commit that includes these predictions is the proof of pre-registration.
 *
 * Run with: npx ts-node scripts/phase0b-register-predictions.ts
 */

import { db } from '../src/db/client';
import { Phase0bCalibrationService } from '../src/services/phase0b-calibration.service';

async function registerPredictions() {
  console.log('\n' + '='.repeat(70));
  console.log('PHASE 0B: PRE-REGISTRATION OF PREDICTIONS');
  console.log('='.repeat(70));
  console.log('\nThis script commits predictions to database BEFORE outcomes are known.');
  console.log('The timestamp of the git commit is the proof of pre-registration.\n');

  const service = new Phase0bCalibrationService();

  // Define 17 predictions across 6 categories
  const predictions = [
    // Category 1: Autonomy Loop Completion (3 predictions)
    {
      category: 'autonomy_completion',
      description: 'Autonomy loop with goal "Find AI safety papers" will extract >= 5 claims',
      confidence: 0.75,
      hypothesis: 'Recent improvements to extraction prompt should improve claim count',
      daysUntilResolution: 3,
    },
    {
      category: 'autonomy_completion',
      description: 'Autonomy loop will complete in <= 120 seconds',
      confidence: 0.85,
      hypothesis: 'Network latency to OpenAI is predictable; goal-aware routing is optimized',
      daysUntilResolution: 3,
    },
    {
      category: 'autonomy_completion',
      description: 'Autonomy loop will fetch >= 3 documents from real sources',
      confidence: 0.80,
      hypothesis: 'ArXiv API is stable; goal-aware category selection works',
      daysUntilResolution: 3,
    },

    // Category 2: Evidence Quality (3 predictions)
    {
      category: 'evidence_quality',
      description: 'Extracted claims will have relevance_score >= 0.5 on average',
      confidence: 0.70,
      hypothesis: 'Title-based keyword matching should correlate with relevance',
      daysUntilResolution: 3,
    },
    {
      category: 'evidence_quality',
      description: 'At least 80% of claims will reference autonomy_evidence rows (support_source_ids non-empty)',
      confidence: 0.90,
      hypothesis: 'Claim generation explicitly requires sources; schema enforces this',
      daysUntilResolution: 3,
    },
    {
      category: 'evidence_quality',
      description: 'Evidence content_hash will be non-null for all fetched documents',
      confidence: 0.95,
      hypothesis: 'Hash computation is deterministic; no null paths in fetch code',
      daysUntilResolution: 3,
    },

    // Category 3: Model Decision Logging (3 predictions)
    {
      category: 'model_decisions',
      description: 'Model decision ledger will record >= 1 decision per autonomy loop run',
      confidence: 0.95,
      hypothesis: 'Action planner always calls selectModelForAction(); ledger is write-once',
      daysUntilResolution: 2,
    },
    {
      category: 'model_decisions',
      description: 'Token tracking will populate request_tokens for all decisions',
      confidence: 0.85,
      hypothesis: 'OpenAI response always includes usage field; updateDecisionOutcome is called',
      daysUntilResolution: 2,
    },
    {
      category: 'model_decisions',
      description: 'All logged decisions will have success field set to true or false (not null)',
      confidence: 0.80,
      hypothesis: 'Success status is recorded on API response or error; no paths skip update',
      daysUntilResolution: 2,
    },

    // Category 4: System Stability (3 predictions)
    {
      category: 'system_stability',
      description: 'Test run will not error with database constraint violation',
      confidence: 0.92,
      hypothesis: 'All FK relationships validated; test data seeded correctly',
      daysUntilResolution: 2,
    },
    {
      category: 'system_stability',
      description: 'Relevance scoring will not cause latency > 5 seconds per autonomy loop',
      confidence: 0.88,
      hypothesis: 'Title ranking is O(n*m) where n=papers, m=keywords; both small (<100)',
      daysUntilResolution: 3,
    },
    {
      category: 'system_stability',
      description: 'No null pointer errors in action planner service',
      confidence: 0.90,
      hypothesis: 'Planner uses optional chaining and defensive checks throughout',
      daysUntilResolution: 2,
    },

    // Category 5: Goal-Aware Routing (2 predictions)
    {
      category: 'goal_aware_routing',
      description: 'Different goals will fetch different papers (0 URL overlap between runs)',
      confidence: 0.75,
      hypothesis: 'Goal-aware category selection routes to different ArXiv categories; papers differ',
      daysUntilResolution: 4,
    },
    {
      category: 'goal_aware_routing',
      description: 'ArXiv category routing will select correct categories based on goal keywords',
      confidence: 0.70,
      hypothesis: 'Keyword extraction from goal and category matching logic is sound',
      daysUntilResolution: 4,
    },

    // Category 6: Integration (2 predictions)
    {
      category: 'integration',
      description: 'ModelSelectionService will be called by AutonomyActionPlannerService during every plan',
      confidence: 0.95,
      hypothesis: 'Integration test verified this path; it is in the code and executed',
      daysUntilResolution: 2,
    },
    {
      category: 'integration',
      description: 'All predictions will have resolution measured by 2026-07-01',
      confidence: 0.85,
      hypothesis: 'Most predictions resolve in 2-4 days; we allow 7 days for buffer',
      daysUntilResolution: 7,
    },
  ];

  console.log(`Registering ${predictions.length} predictions...\n`);

  const registeredPredictions = [];
  for (const pred of predictions) {
    const expectedResolutionBy = new Date();
    expectedResolutionBy.setDate(expectedResolutionBy.getDate() + pred.daysUntilResolution);

    try {
      const registered = await service.registerPrediction(
        {
          category: pred.category,
          description: pred.description,
          confidence: pred.confidence,
          expectedResolutionBy,
          hypothesis: pred.hypothesis,
        },
        'phase0b_registration_script'
      );

      registeredPredictions.push(registered);
      console.log(`✅ [${pred.category}] Confidence ${pred.confidence}`);
      console.log(`   "${pred.description.substring(0, 70)}..."`);
      console.log(`   Resolves by: ${expectedResolutionBy.toISOString().split('T')[0]}\n`);
    } catch (error) {
      console.error(`❌ Failed to register: ${pred.description}`);
      console.error(`   Error: ${error}\n`);
    }
  }

  // Summary
  console.log('='.repeat(70));
  console.log('\n📋 PREDICTION REGISTRATION SUMMARY\n');
  console.log(`Total registered: ${registeredPredictions.length}/${predictions.length}`);

  // Group by category
  const byCategory: Record<string, number> = {};
  for (const pred of registeredPredictions) {
    byCategory[pred.category] = (byCategory[pred.category] || 0) + 1;
  }

  console.log('\nBy category:');
  for (const [category, count] of Object.entries(byCategory)) {
    console.log(`  - ${category}: ${count} predictions`);
  }

  // Average confidence
  const avgConfidence =
    registeredPredictions.reduce((sum, p) => sum + p.confidence, 0) /
    registeredPredictions.length;
  console.log(`\nAverage confidence: ${avgConfidence.toFixed(3)}`);

  // Earliest and latest resolution dates
  const dates = registeredPredictions.map(p => p.expectedResolutionBy).sort((a, b) => a.getTime() - b.getTime());
  if (dates.length > 0) {
    console.log(`\nEarliest resolution: ${dates[0].toISOString().split('T')[0]}`);
    console.log(`Latest resolution:   ${dates[dates.length - 1].toISOString().split('T')[0]}`);
  }

  console.log('\n' + '='.repeat(70));
  console.log('\n🔒 PROOF OF PRE-REGISTRATION\n');
  console.log('These predictions are now in the database.');
  console.log('The git commit that includes this script and the migration is the proof');
  console.log('that these predictions were registered BEFORE outcomes were known.\n');
  console.log('Next steps:');
  console.log('1. Commit this code to git');
  console.log('2. Run autonomy loops to generate outcomes');
  console.log('3. Resolve predictions with actual measured values');
  console.log('4. Compute Brier score and calibration curves\n');

  await db.end();
}

registerPredictions().catch(error => {
  console.error('\n❌ Registration failed:', error);
  process.exit(1);
});
