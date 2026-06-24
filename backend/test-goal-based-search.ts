#!/usr/bin/env npx ts-node
/**
 * Goal-Based Search Test: Verify Different Goals Produce Different URLs
 *
 * Tests whether wiring search() into the learning run produces goal-varying content.
 * If successful, documents fetched for "AI safety" should differ from "distributed systems".
 */

import { BoundedCivilizationLearningRun } from './src/services/bounded-learning-run.service';
import { db } from './src/db/client';

async function getRecentDocuments(minAge: number = 5): Promise<any[]> {
  const result = await db.query(
    `SELECT DISTINCT url FROM autonomy_evidence
     WHERE created_at > NOW() - INTERVAL '${minAge} minutes'
     ORDER BY created_at DESC`
  );
  return result.rows.map(r => r.url);
}

async function runGoalBasedTest(goal: string, description: string) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`TEST: ${description}`);
  console.log(`Goal: "${goal}"`);
  console.log(`${'='.repeat(70)}`);

  const service = new BoundedCivilizationLearningRun();

  const result = await service.execute({
    goal,
    sourcePack: 'technical',  // Use same pack for both tests
    maxPages: 5,
    realWebEnabled: true,
    provider: 'openai',
    useGoalBasedSearch: true,  // NEW: Enable goal-based search
  });

  console.log(`\n✅ Learning run completed`);
  console.log(`   Documents fetched: ${result.documentsFetched}`);
  console.log(`   Claims extracted: ${result.claimsExtracted}`);

  // Get the URLs that were fetched
  const urls = await getRecentDocuments(5);

  if (urls.length > 0) {
    console.log(`\n📋 FETCHED DOCUMENTS:`);
    for (const url of urls.slice(0, 5)) {
      console.log(`   - ${url}`);
    }
  } else {
    console.log(`\n⚠️ No recent documents found in DB`);
  }

  return { goal, urls };
}

async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('GOAL-BASED SEARCH TEST');
  console.log('='.repeat(70));
  console.log('Verify that goal-aware search produces different URLs for different goals\n');

  const test1 = await runGoalBasedTest(
    'Find recent breakthroughs in quantum computing and quantum error correction',
    'Test 1: Quantum Computing Focus'
  );

  console.log('\n(Waiting 2s for DB consistency...)');
  await new Promise(r => setTimeout(r, 2000));

  const test2 = await runGoalBasedTest(
    'Discover recent progress in machine learning optimization and neural architecture search',
    'Test 2: ML Optimization Focus'
  );

  // Analysis
  console.log('\n' + '='.repeat(70));
  console.log('ANALYSIS: URL DIVERGENCE');
  console.log('='.repeat(70));

  const set1 = new Set(test1.urls);
  const set2 = new Set(test2.urls);

  const common = [...set1].filter(u => set2.has(u));
  const only1 = [...set1].filter(u => !set2.has(u));
  const only2 = [...set2].filter(u => !set1.has(u));

  console.log(`\nGoal 1 URLs: ${set1.size}`);
  console.log(`Goal 2 URLs: ${set2.size}`);
  console.log(`URLs in common: ${common.length}`);
  console.log(`URLs unique to Goal 1: ${only1.length}`);
  console.log(`URLs unique to Goal 2: ${only2.length}`);

  if (only1.length > 0) {
    console.log(`\n✅ Goal-specific URLs for Goal 1:`);
    for (const url of only1.slice(0, 3)) {
      console.log(`   - ${url}`);
    }
  }

  if (only2.length > 0) {
    console.log(`\n✅ Goal-specific URLs for Goal 2:`);
    for (const url of only2.slice(0, 3)) {
      console.log(`   - ${url}`);
    }
  }

  const divergencePercent = only1.length + only2.length > 0
    ? Math.round(((only1.length + only2.length) / (set1.size + set2.size)) * 100)
    : 0;

  console.log(`\n📊 DIVERGENCE: ${divergencePercent}% of URLs are goal-specific`);

  if (divergencePercent >= 50) {
    console.log('\n✅ SUCCESS: Goal-based search produces goal-varying content');
  } else if (divergencePercent >= 25) {
    console.log('\n⚠️  PARTIAL: Some goal-variance detected, but goals still return overlapping results');
  } else {
    console.log('\n❌ FAILURE: Goals return the same URLs; goal-based search not working');
  }

  console.log('\n' + '='.repeat(70));
  console.log('NEXT STEPS FOR PHASE 1');
  console.log('='.repeat(70));
  console.log(`
If divergence >= 50%: Goal-based search is working. Safe to:
  1. Make extraction prompt goal-aware (pass goal to OpenAI)
  2. Build Phase 1 epistemic kernel with confidence that sources vary by goal

If divergence < 50%: Search is not helping. Need to:
  1. Debug: Is search() returning results? Are they being fetched?
  2. Consider: Better search query extraction from goal
  3. Fallback: Make seed registry properly topic-indexed instead of relying on search
`);

  await db.end();
  process.exit(0);
}

main();
