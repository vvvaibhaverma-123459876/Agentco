#!/usr/bin/env npx ts-node
/**
 * Test Extraction Only: One goal, ai_tech pack, let it fetch from arxiv
 */

import { BoundedCivilizationLearningRun } from './src/services/bounded-learning-run.service';
import { db } from './src/db/client';

async function testExtraction() {
  console.log('\n' + '='.repeat(70));
  console.log('TEST: EXTRACTION VERIFICATION');
  console.log('='.repeat(70) + '\n');

  const service = new BoundedCivilizationLearningRun();

  const result = await service.execute({
    goal: 'Research AI scaling laws and LLM efficiency',
    sourcePack: 'ai_tech',
    maxPages: 5,
    realWebEnabled: true,
    provider: 'openai',
  });

  console.log(`\nDocuments: ${result.documentsFetched}, Claims: ${result.claimsExtracted}, Persisted: ${result.claimsPersisted}`);

  if (result.claimsPersisted > 0) {
    console.log('\n✅ SUCCESS: Extraction working\n');

    const claims = await db.query(
      `SELECT text, confidence FROM autonomy_claims
       WHERE created_at > NOW() - INTERVAL '3 minutes'
       ORDER BY created_at DESC
       LIMIT 5`
    );

    console.log(`Extracted ${claims.rows.length} claims:`);
    for (const claim of claims.rows) {
      console.log(`\n  "${claim.text}"`);
      console.log(`  Confidence: ${claim.confidence}`);
    }
  } else {
    console.log('\n❌ EXTRACTION FAILED');
    if (result.warnings.length > 0) {
      console.log('\nWarnings:');
      result.warnings.forEach(w => console.log(`  ${w}`));
    }
  }

  await db.end();
  process.exit(result.claimsPersisted > 0 ? 0 : 1);
}

testExtraction();
