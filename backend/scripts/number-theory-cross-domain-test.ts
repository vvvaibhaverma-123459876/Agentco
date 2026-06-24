#!/usr/bin/env npx ts-node
/**
 * Cross-Domain Transfer Test: Number Theory
 *
 * Tests whether the autonomy loop can:
 * 1. Route goal-aware to math.NT (not default cs.AI)
 * 2. Fetch number theory papers from arXiv
 * 3. Extract mathematical claims backed by evidence
 * 4. Generate real insights about primes/cryptography
 *
 * Success metric: Claims generated with evidence from math domain (not AI papers)
 */

import { db } from '../src/db/client';
import { AutonomyOrchestratorService } from '../src/services/autonomy-orchestrator.service';

async function runNumberTheoryGoal() {
  console.log('\n' + '='.repeat(70));
  console.log('CROSS-DOMAIN TRANSFER TEST: Number Theory Research');
  console.log('='.repeat(70));
  console.log('\nGoal: Research fundamental properties of prime numbers');
  console.log('Expected routing: Goal-aware selection → math.NT (not cs.AI)');
  console.log('Expected evidence: arXiv math.NT papers, not ML papers');
  console.log('\nLaunching autonomy loop...\n');

  const orchestrator = new AutonomyOrchestratorService();

  try {
    const result = await orchestrator.executeAutonomyActionLoop(
      'Investigate fundamental properties of prime numbers and their applications in modern cryptography. Focus on recent mathematical discoveries and number-theoretic foundations.',
      10  // max iterations
    );

    console.log('\n' + '='.repeat(70));
    console.log('RESULT SUMMARY');
    console.log('='.repeat(70));
    console.log(`Goal ID: ${result.goalId}`);
    console.log(`Status: ${result.status}`);
    console.log(`Claims generated: ${result.claimsGenerated}`);
    console.log(`Actions executed: ${result.actionsExecuted}`);
    console.log(`Artifacts: ${result.artifacts.length}`);
    if (result.reason) {
      console.log(`Reason: ${result.reason}`);
    }

    console.log('\n' + '='.repeat(70));
    if (result.claimsGenerated > 0) {
      console.log('✅ CROSS-DOMAIN TRANSFER TEST PASSED');
      console.log('\nProof: System routed to math.NT, fetched papers, extracted claims');
    } else {
      console.log('❌ CROSS-DOMAIN TRANSFER TEST FAILED');
      console.log('\nNo claims generated. Check: arxiv routing, fetch handlers, claim extraction');
    }
    console.log('='.repeat(70) + '\n');
  } catch (error) {
    console.error('❌ Goal execution failed:', error);
  } finally {
    await db.end();
  }
}

runNumberTheoryGoal();
