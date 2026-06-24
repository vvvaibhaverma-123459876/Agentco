#!/usr/bin/env npx ts-node
/**
 * Phase 0a Test: Autonomy Loop Extraction
 *
 * Verifies that bounded-learning-run service:
 * 1. Discovers real sources from seed registry
 * 2. Fetches real documents
 * 3. Extracts claims via OpenAI
 * 4. Persists to database with full audit trail
 */

import { BoundedCivilizationLearningRun } from './src/services/bounded-learning-run.service';
import { db } from './src/db/client';

async function testPhase0a() {
  console.log('\n' + '='.repeat(70));
  console.log('PHASE 0a TEST: AUTONOMY LOOP EXTRACTION');
  console.log('='.repeat(70));

  const service = new BoundedCivilizationLearningRun();

  try {
    // Run bounded learning with ai_tech source pack
    const result = await service.execute({
      goal: 'Research recent AI autonomy developments from trusted sources',
      sourcePack: 'ai_tech',
      maxPages: 3,
      realWebEnabled: true,  // KEY: Enable real web fetching (previously was failing with node-fetch)
      provider: 'openai',     // Use OpenAI for claim extraction
    });

    console.log('\n' + '='.repeat(70));
    console.log('RESULTS SUMMARY');
    console.log('='.repeat(70));
    console.log(`Status: ${result.status}`);
    console.log(`Sources discovered: ${result.sourcesDiscovered}`);
    console.log(`Sources allowed: ${result.sourcesAllowed}`);
    console.log(`Documents fetched: ${result.documentsFetched}`);
    console.log(`Claims extracted: ${result.claimsExtracted}`);
    console.log(`Claims persisted: ${result.claimsPersisted}`);
    console.log(`Duration: ${(result.durationMs / 1000).toFixed(1)}s`);

    if (result.errors.length > 0) {
      console.log(`\nErrors:`);
      for (const error of result.errors) {
        console.log(`  - ${error}`);
      }
    }

    if (result.warnings.length > 0) {
      console.log(`\nWarnings:`);
      for (const warning of result.warnings) {
        console.log(`  - ${warning}`);
      }
    }

    // Verify actual database rows
    console.log('\n' + '='.repeat(70));
    console.log('DATABASE VERIFICATION');
    console.log('='.repeat(70));

    const evidenceCount = await db.query(
      'SELECT COUNT(*) as count FROM autonomy_evidence WHERE created_at > NOW() - INTERVAL \'5 minutes\''
    );
    const claimsCount = await db.query(
      'SELECT COUNT(*) as count FROM autonomy_claims WHERE created_at > NOW() - INTERVAL \'5 minutes\''
    );

    console.log(`Evidence rows (last 5 min): ${evidenceCount.rows[0].count}`);
    console.log(`Claims rows (last 5 min): ${claimsCount.rows[0].count}`);

    if (evidenceCount.rows[0].count > 0) {
      const recentEvidence = await db.query(
        `SELECT id, source_id, url, title, content_hash
         FROM autonomy_evidence
         WHERE created_at > NOW() - INTERVAL '5 minutes'
         LIMIT 3`
      );

      console.log('\nRecent evidence rows:');
      for (const row of recentEvidence.rows) {
        console.log(`  - ID: ${row.id}`);
        console.log(`    URL: ${row.url}`);
        console.log(`    Title: ${row.title}`);
        console.log(`    Hash: ${row.content_hash}`);
      }
    }

    if (claimsCount.rows[0].count > 0) {
      const recentClaims = await db.query(
        `SELECT id, claim_id, text, confidence, status, support_source_ids
         FROM autonomy_claims
         WHERE created_at > NOW() - INTERVAL '5 minutes'
         LIMIT 3`
      );

      console.log('\nRecent claim rows:');
      for (const row of recentClaims.rows) {
        console.log(`  - ID: ${row.id}`);
        console.log(`    Text: "${row.text.substring(0, 80)}..."`);
        console.log(`    Confidence: ${row.confidence}`);
        console.log(`    Status: ${row.status}`);
      }
    }

    console.log('\n' + '='.repeat(70));
    if (result.documentsFetched > 0 && result.claimsPersisted > 0) {
      console.log('✅ PHASE 0a SUCCESS');
      console.log('Autonomy loop extracted real documents and persisted claims');
    } else {
      console.log('⚠️  PHASE 0a INCOMPLETE');
      console.log(`Documents fetched: ${result.documentsFetched}, Claims persisted: ${result.claimsPersisted}`);
    }
    console.log('='.repeat(70) + '\n');

    process.exit(result.documentsFetched > 0 && result.claimsPersisted > 0 ? 0 : 1);
  } catch (error: any) {
    console.error(`\n❌ TEST FAILED: ${error.message}`);
    console.error(error.stack);
    process.exit(1);
  } finally {
    await db.end();
  }
}

testPhase0a();
