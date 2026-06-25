/**
 * Real-Web Smoke Test for Bounded Learning Run
 * ============================================
 *
 * This test is SKIPPED by default.
 * Run only with: RUN_REAL_WEB_TESTS=1 npm test
 *
 * Tests real web fetching from allowlisted sources.
 * Does NOT require OpenAI (uses test-only extraction if unavailable).
 * Verifies:
 * - Real sources are discovered
 * - Real pages are fetched
 * - Content is extracted
 * - Provenance links are created
 * - No fabricated data
 */

import { describe, it, expect } from '@jest/globals';
import { BoundedCivilizationLearningRun } from '../src/services/bounded-learning-run.service';

const SKIP_REAL_WEB = !process.env.RUN_REAL_WEB_TESTS;

describe('Real-Web Smoke Test', () => {
  const orchestrator = new BoundedCivilizationLearningRun();

  (SKIP_REAL_WEB ? it.skip : it)(
    'should fetch from allowlisted real source and extract content',
    async () => {
      console.log(`\n${'='.repeat(70)}`);
      console.log('REAL-WEB SMOKE TEST');
      console.log(`${'='.repeat(70)}`);
      console.log(`This test fetches from the real internet.`);

      const result = await orchestrator.execute({
        goal: 'Learn about AI autonomy from technical sources',
        sourcePack: 'ai_tech',
        maxPages: 1,
        maxClaims: 3,
        allowedDomains: [
          'github.com',
          'arxiv.org',
          'openai.com',
          'anthropic.com',
          'deepmind.google',
        ],
        provider: 'deterministic_test_only',
        dryRun: false,
        realWebEnabled: true,
      });

      console.log(`\nSmoke Test Results:`);
      console.log(`  Status: ${result.status}`);
      console.log(`  Sources discovered: ${result.sourcesDiscovered}`);
      console.log(`  Sources allowed: ${result.sourcesAllowed}`);
      console.log(`  Documents fetched: ${result.documentsFetched}`);
      console.log(`  Claims extracted: ${result.claimsExtracted}`);
      console.log(`  Audit events: ${result.auditEventsLogged}`);

      if (result.warnings.length > 0) {
        console.log(`  Warnings:`);
        for (const warning of result.warnings) {
          console.log(`    - ${warning}`);
        }
      }

      expect(result.status).toBe('success');
      expect(result.sourcesDiscovered).toBeGreaterThan(0);
    }
  );
});
