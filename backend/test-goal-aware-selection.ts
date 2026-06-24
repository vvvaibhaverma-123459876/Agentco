#!/usr/bin/env npx ts-node
/**
 * Test Goal-Aware Arxiv Selection
 *
 * Verify that different goals select different arxiv categories
 */

import { BoundedCivilizationLearningRun } from './src/services/bounded-learning-run.service';
import { db } from './src/db/client';

async function testGoal(goal: string, expectedCategory: string) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`Goal: "${goal}"`);
  console.log(`Expected Category: ${expectedCategory}`);
  console.log(`${'='.repeat(70)}`);

  const service = new BoundedCivilizationLearningRun();

  const result = await service.execute({
    goal,
    sourcePack: 'ai_tech',
    maxPages: 3,
    realWebEnabled: true,
    provider: 'openai',
  });

  // Get fetched URLs from DB
  const urls = await db.query(
    `SELECT DISTINCT url, created_at FROM autonomy_evidence
     WHERE created_at > NOW() - INTERVAL '2 minutes'
     ORDER BY created_at DESC`
  );

  console.log(`\nDocuments fetched: ${result.documentsFetched}`);

  if (urls.rows.length > 0) {
    console.log(`URLs:`);
    for (const row of urls.rows.slice(0, 3)) {
      const url = row.url as string;
      const categoryMatch = url.match(/arxiv\.org\/list\/([^/]+)/);
      const category = categoryMatch ? categoryMatch[1] : 'unknown';
      console.log(`  - ${url}`);
      console.log(`    Category detected: ${category}`);
    }
  }

  return { goal, urls: urls.rows.map((r: any) => r.url) };
}

async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('GOAL-AWARE ARXIV SELECTION TEST');
  console.log('='.repeat(70));

  const test1 = await testGoal(
    'Develop distributed consensus algorithms for blockchain systems',
    'cs.DS'
  );

  await new Promise(r => setTimeout(r, 1000));

  const test2 = await testGoal(
    'Improve AI safety and alignment for language models',
    'cs.AI'
  );

  // Analysis
  console.log('\n' + '='.repeat(70));
  console.log('ANALYSIS');
  console.log('='.repeat(70));

  const set1 = new Set(test1.urls);
  const set2 = new Set(test2.urls);

  console.log(`\nGoal 1 URLs: ${set1.size}`);
  console.log(`Goal 2 URLs: ${set2.size}`);

  const categories1 = new Set(
    Array.from(set1)
      .map(url => (url as string).match(/arxiv\.org\/list\/([^/]+)/)?.[1])
      .filter(Boolean)
  );
  const categories2 = new Set(
    Array.from(set2)
      .map(url => (url as string).match(/arxiv\.org\/list\/([^/]+)/)?.[1])
      .filter(Boolean)
  );

  console.log(`\nCategories selected by Goal 1: ${Array.from(categories1).join(', ')}`);
  console.log(`Categories selected by Goal 2: ${Array.from(categories2).join(', ')}`);

  const different = ![...categories1].some(cat => categories2.has(cat));

  console.log(`\n${different ? '✅ SUCCESS' : '❌ FAILURE'}: Different goals selected ${different ? 'different' : 'same'} arxiv categories`);

  await db.end();
  process.exit(0);
}

main();
