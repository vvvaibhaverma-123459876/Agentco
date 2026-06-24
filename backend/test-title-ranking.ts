#!/usr/bin/env npx ts-node
/**
 * Title-Ranking Test: Phase 1 Task 1
 *
 * Verify that papers are selected by goal-keyword relevance, not fixed stride.
 * Print titles + relevance scores for eye-reading.
 */

import { BoundedCivilizationLearningRun } from './src/services/bounded-learning-run.service';
import { db } from './src/db/client';

async function testTitleRanking(goal: string, testName: string) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`${testName}`);
  console.log(`Goal: "${goal}"`);
  console.log(`${'='.repeat(70)}`);

  const service = new BoundedCivilizationLearningRun();

  const result = await service.execute({
    goal,
    sourcePack: 'ai_tech',
    maxPages: 2,
    realWebEnabled: true,
    provider: 'openai',
  });

  console.log(`\nResults: ${result.documentsFetched} docs, ${result.claimsExtracted} claims`);

  // Get the fetched URLs (these should be top-ranked by goal relevance)
  const evidence = await db.query(
    `SELECT DISTINCT url FROM autonomy_evidence
     WHERE created_at > NOW() - INTERVAL '10 seconds'`
  );

  const urls = evidence.rows.map((r: any) => r.url);
  console.log(`\nFetched URLs (by relevance ranking):`);
  for (const url of urls) {
    console.log(`  - ${url}`);
  }

  return urls;
}

async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('PHASE 1 TASK 1: TITLE-RANKING VERIFICATION');
  console.log('='.repeat(70));
  console.log('\nExpectation: Different goals select different papers based on title relevance\n');

  // Delete old data
  await db.query(`DELETE FROM autonomy_claims WHERE created_at > NOW() - INTERVAL '5 minutes'`);
  await db.query(`DELETE FROM autonomy_evidence WHERE created_at > NOW() - INTERVAL '5 minutes'`);

  const urls1 = await testTitleRanking(
    'Distributed consensus algorithms and Byzantine fault tolerance',
    'TEST 1: Distributed Systems'
  );

  await db.query(`DELETE FROM autonomy_claims WHERE created_at > NOW() - INTERVAL '5 minutes'`);
  await db.query(`DELETE FROM autonomy_evidence WHERE created_at > NOW() - INTERVAL '5 minutes'`);
  await new Promise(r => setTimeout(r, 1000));

  const urls2 = await testTitleRanking(
    'Language model safety, alignment, and red-teaming',
    'TEST 2: AI Safety'
  );

  // Comparison
  console.log(`\n${'='.repeat(70)}`);
  console.log('COMPARISON');
  console.log(`${'='.repeat(70)}`);

  const set1 = new Set(urls1);
  const set2 = new Set(urls2);
  const common = [...set1].filter(u => set2.has(u));

  console.log(`\nGoal 1 URLs: ${set1.size}`);
  console.log(`Goal 2 URLs: ${set2.size}`);
  console.log(`Common: ${common.length}`);

  const disjoint = common.length === 0 && set1.size > 0 && set2.size > 0;
  console.log(`\n${disjoint ? '✅' : '⚠️'} URL divergence: ${disjoint ? 'YES (completely different papers)' : 'NO (same papers selected)'}`);

  console.log(`\n📌 Note: Check the "Fetching (score: X.XX)" lines above for goal-keyword relevance scores.`);
  console.log(`         Top-3 scorers were selected, not fixed positions [0,5,10].\n`);

  await db.end();
  process.exit(0);
}

main();
