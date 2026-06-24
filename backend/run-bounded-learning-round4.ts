#!/usr/bin/env npx ts-node
/**
 * Round 4: Real Bounded Learning Run
 *
 * Uses the actual BoundedCivilizationLearningRun service
 * to fetch real paper content and extract verified claims.
 *
 * This avoids citation fabrication by:
 * 1. Fetching real content from arXiv
 * 2. Extracting claims from fetched abstracts
 * 3. Persisting evidence with content hashes
 * 4. Linking claims to real sources
 */

import { BoundedCivilizationLearningRun } from './src/services/bounded-learning-run.service';

async function runRound4() {
  const learningRun = new BoundedCivilizationLearningRun();

  // Use ai_tech source pack which includes verified arXiv and research sources
  // This ensures we fetch from a source discovery registry that's been validated
  const config = {
    goal: 'Round 4: Extract high-quality, diverse AI research claims from verified sources',
    sourcePack: 'ai_tech', // Verified AI & Autonomy sources from seed registry
    maxPages: 12, // Fetch up to 12 different papers
    maxClaims: 40, // Extract up to 40 claims
    maxDurationSeconds: 300,
    provider: 'openai' as const,
    realWebEnabled: true, // Actually fetch from web
    dryRun: false,
    allowedDomains: ['arxiv.org', 'openai.com', 'anthropic.com', 'deepmind.google'],
    deniedDomains: [],
  };

  console.log(`\n${'='.repeat(70)}`);
  console.log('ROUND 4: BOUNDED LEARNING RUN WITH REAL SOURCES');
  console.log('='.repeat(70));
  console.log(`Objective: Extract verified claims from real paper content`);
  console.log(`Provider: OpenAI (gpt-4o-mini)`);
  console.log(`Real Web: ENABLED (actual arXiv fetch)`);
  console.log(`Expected Claims: 20-40 (diverse, verified)`);
  console.log('');

  try {
    const result = await learningRun.execute(config);

    console.log(`\n${'='.repeat(70)}`);
    console.log('ROUND 4 RESULTS');
    console.log('='.repeat(70));
    console.log(`Status: ${result.status}`);
    console.log(`Sources discovered: ${result.sourcesDiscovered}`);
    console.log(`Sources allowed: ${result.sourcesAllowed}`);
    console.log(`Sources fetched: ${result.sourcesFetched}`);
    console.log(`Documents fetched: ${result.documentsFetched}`);
    console.log(`Claims extracted: ${result.claimsExtracted}`);
    console.log(`Claims persisted: ${result.claimsPersisted}`);
    console.log(`Claims routed: ${result.claimsRouted}`);
    console.log(`Duration: ${result.durationMs}ms`);

    if (result.errors.length > 0) {
      console.log(`\nErrors:`);
      result.errors.forEach((e) => console.log(`  • ${e}`));
    }

    if (result.warnings.length > 0) {
      console.log(`\nWarnings:`);
      result.warnings.forEach((w) => console.log(`  • ${w}`));
    }

    console.log(`\n✅ Round 4 learning run complete!`);
    console.log(`Next: Validate ${result.claimsExtracted} extracted claims`);
  } catch (error: any) {
    console.error(`\n❌ Learning run failed: ${error.message}`);
    process.exit(1);
  }
}

// Run
runRound4().catch((error) => {
  console.error('Fatal error:', error.message);
  process.exit(1);
});
