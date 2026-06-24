#!/usr/bin/env npx ts-node
/**
 * Test Prompt Fix: Verify extraction works again after prompt tightening
 *
 * Single paper (2606.24747 - Scaling Laws) should yield claims
 */

import { BoundedCivilizationLearningRun } from './src/services/bounded-learning-run.service';
import { db } from './src/db/client';

async function testPromptFix() {
  console.log('\n' + '='.repeat(70));
  console.log('TEST: PROMPT FIX VERIFICATION');
  console.log('='.repeat(70));
  console.log('Goal: Verify extraction works after prompt tightening\n');

  const service = new BoundedCivilizationLearningRun();

  const result = await service.execute({
    goal: 'Test extraction on scaling laws paper',
    sourcePack: 'ai_tech',
    maxPages: 1,
    realWebEnabled: true,
    provider: 'openai',
  });

  console.log(`\nResults:  ${result.documentsFetched} docs → ${result.claimsExtracted} claims → ${result.claimsPersisted} persisted`);
  console.log(`Status: ${result.status}`);

  if (result.claimsPersisted > 0) {
    console.log('\n✅ EXTRACTION WORKS: Prompt fix successful\n');

    const claims = await db.query(
      `SELECT text, confidence FROM autonomy_claims
       WHERE created_at > NOW() - INTERVAL '2 minutes'
       ORDER BY created_at DESC
       LIMIT 5`
    );

    console.log('Sample claims extracted:');
    for (const claim of claims.rows) {
      console.log(`  - "${claim.text.substring(0, 80)}..." (confidence: ${claim.confidence})`);
    }
  } else {
    console.log('\n❌ EXTRACTION STILL BROKEN: Prompt needs further adjustment\n');

    if (result.warnings.length > 0) {
      console.log('Warnings:');
      for (const warning of result.warnings) {
        console.log(`  - ${warning}`);
      }
    }
  }

  console.log('\n' + '='.repeat(70));
  await db.end();
  process.exit(result.claimsPersisted > 0 ? 0 : 1);
}

testPromptFix();
