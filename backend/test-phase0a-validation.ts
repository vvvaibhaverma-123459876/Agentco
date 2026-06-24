#!/usr/bin/env npx ts-node
/**
 * Phase 0a Validation: Check Extraction Quality
 *
 * Run the autonomy loop on 2-3 different goals/packs and inspect the claims
 * to assess:
 * 1. Goal relevance (are claims on-topic for the goal?)
 * 2. Claim quality (are they findings or meta-commentary?)
 * 3. Extraction fragility (how many sources fail?)
 */

import { BoundedCivilizationLearningRun } from './src/services/bounded-learning-run.service';
import { db } from './src/db/client';

interface TestCase {
  goal: string;
  pack: string;
  description: string;
}

async function readClaimsFromDb(maxAge: number = 5): Promise<any[]> {
  const result = await db.query(
    `SELECT claim_id, text, confidence, support_source_ids
     FROM autonomy_claims
     WHERE created_at > NOW() - INTERVAL '${maxAge} minutes'
     ORDER BY created_at DESC`
  );
  return result.rows;
}

async function runTest(testCase: TestCase) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`TEST: ${testCase.description}`);
  console.log(`Goal: ${testCase.goal}`);
  console.log(`Pack: ${testCase.pack}`);
  console.log(`${'='.repeat(70)}`);

  const service = new BoundedCivilizationLearningRun();

  const result = await service.execute({
    goal: testCase.goal,
    sourcePack: testCase.pack,
    maxPages: 3,
    realWebEnabled: true,
    provider: 'openai',
  });

  console.log(`\nResults: ${result.documentsFetched} docs → ${result.claimsExtracted} claims → ${result.claimsPersisted} persisted`);
  console.log(`Duration: ${(result.durationMs / 1000).toFixed(1)}s`);

  // Read back the claims from DB
  const claims = await readClaimsFromDb(5);

  if (claims.length === 0) {
    console.log('⚠️  No claims in DB');
    return { goal: testCase.goal, claims: [] };
  }

  console.log(`\n📋 CLAIMS EXTRACTED (n=${claims.length}):`);
  for (let i = 0; i < Math.min(3, claims.length); i++) {
    const claim = claims[i];
    console.log(`\n  [${i + 1}] "${claim.text.substring(0, 100)}${claim.text.length > 100 ? '...' : ''}"`);
    console.log(`      Confidence: ${claim.confidence}`);
    console.log(`      Sources: ${claim.support_source_ids}`);
  }

  return { goal: testCase.goal, claims };
}

async function validateClaims() {
  console.log('\n' + '='.repeat(70));
  console.log('PHASE 0a VALIDATION: EXTRACTION QUALITY');
  console.log('='.repeat(70));
  console.log('Running autonomy loop on different goals to assess claim quality\n');

  const testCases: TestCase[] = [
    {
      goal: 'Find recent developments in large language model safety and alignment',
      pack: 'ai_tech',
      description: 'Test 1: AI Safety Focus',
    },
    {
      goal: 'Discover recent advances in distributed systems and consensus algorithms',
      pack: 'technical',
      description: 'Test 2: Systems Engineering Focus',
    },
  ];

  const results = [];

  for (const testCase of testCases) {
    try {
      const result = await runTest(testCase);
      results.push(result);
    } catch (error: any) {
      console.error(`❌ Test failed: ${error.message}`);
    }
  }

  // Summary analysis
  console.log('\n' + '='.repeat(70));
  console.log('QUALITY ASSESSMENT');
  console.log('='.repeat(70));

  for (const result of results) {
    console.log(`\nGoal: "${result.goal}"`);
    console.log(`Claims extracted: ${result.claims.length}`);

    if (result.claims.length > 0) {
      console.log('\nKey observations:');

      // Check for goal relevance
      const goalKeywords = result.goal.toLowerCase().split(' ').filter(w => w.length > 4);
      let relevantCount = 0;
      let metaCount = 0;

      for (const claim of result.claims.slice(0, 3)) {
        const claimLower = claim.text.toLowerCase();
        const hasKeywords = goalKeywords.some(kw => claimLower.includes(kw));

        if (claimLower.includes('discusses') || claimLower.includes('paper') || claimLower.includes('introduces')) {
          metaCount++;
        } else if (hasKeywords) {
          relevantCount++;
        }
      }

      console.log(`  - On-topic (matches goal keywords): ${relevantCount}/${Math.min(3, result.claims.length)}`);
      console.log(`  - Meta-commentary ("discusses", "paper", etc): ${metaCount}/${Math.min(3, result.claims.length)}`);
      console.log(`  - Avg confidence: ${(result.claims.reduce((s, c) => s + c.confidence, 0) / result.claims.length).toFixed(2)}`);
    }
  }

  console.log('\n' + '='.repeat(70));
  console.log('KEY QUESTIONS FOR PHASE 1 DESIGN');
  console.log('='.repeat(70));
  console.log(`
1. **Goal Awareness**: Should extraction filter claims by goal relevance?
   - Current: Goal-blind extraction harvests claims broadly
   - Alternative: Pass goal to extraction prompt, filter results

2. **Quality Gate**: Where does relevance/quality filtering belong?
   - Extract-time: Filter low-relevance claims before persistence
   - Post-extract: Evaluate and mark claims after persistence
   - Routing-time: Route only high-quality claims to societies

3. **Calibration Building Block**: What is a "trustworthy claim"?
   - Is relevance a trust signal?
   - Is meta-commentary inherently lower confidence?
   - How do we avoid calibrating on junk?
`);

  await db.end();
  process.exit(0);
}

validateClaims();
