#!/usr/bin/env npx ts-node

/**
 * AGENTCO REAL-WORLD 2-MINUTE UNCONSTRAINED AUTONOMY RUN
 * ======================================================
 *
 * Complete observation of AgentCo operating freely in the real world
 * with real OpenAI API access for 2 minutes.
 *
 * NO constraints. NO guidance. FULL autonomy.
 * Capture everything that happens.
 *
 * Run with: npm run autonomy:unconstrained
 */

import { AutonomyOrchestratorService } from '../src/services/autonomy-orchestrator.service';
import * as fs from 'fs';
import * as path from 'path';

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

async function runUnconstrainedAutonomy(): Promise<boolean> {
  console.log('\n' + '='.repeat(70));
  console.log('  AGENTCO REAL-WORLD 2-MINUTE UNCONSTRAINED RUN');
  console.log('  No constraints. No guidance. Pure autonomy observation.');
  console.log('='.repeat(70) + '\n');

  // Check for API key
  const apiKey = process.env.LLM_API_KEY || process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.log('❌ ERROR: No API key found');
    console.log('   Set LLM_API_KEY or OPENAI_API_KEY environment variable');
    return false;
  }

  console.log(`✅ API Key: Found (${apiKey.length} chars)`);
  console.log(`   Using: ${process.env.LLM_API_KEY ? 'LLM_API_KEY' : 'OPENAI_API_KEY'}`);

  const startTime = Date.now();
  const timeoutMs = 2 * 60 * 1000; // 2 minutes

  console.log(`\n⏱️  Test Duration: ${timeoutMs / 1000} seconds (2 minutes)`);
  console.log(`   Start Time: ${new Date().toISOString()}`);
  console.log('\n' + '='.repeat(70));
  console.log('  LAUNCHING ORCHESTRATOR...');
  console.log('='.repeat(70) + '\n');

  try {
    const orchestrator = new AutonomyOrchestratorService();
    console.log('✅ Orchestrator initialized');
    console.log('   Status: Ready for autonomous execution\n');

    // Random unconstrained goals
    const goals = [
      'Investigate how AI systems learn and adapt to novel situations',
      'Analyze the current state of autonomous agent technology in 2026',
      'Research emerging trends in AI safety and alignment',
      'Explore the intersection of machine learning and scientific discovery',
      'Investigate how autonomous systems handle ambiguity and uncertainty',
      'Research the latest breakthroughs in artificial general intelligence',
      'Analyze real-world applications of autonomous systems',
      'Investigate how AI systems can improve human decision-making'
    ];

    const goal = goals[Math.floor(Math.random() * goals.length)];

    console.log(`🎯 Goal (randomly selected for unconstrained exploration):`);
    console.log(`   "${goal}"`);
    console.log(`\n⏳ Running orchestrator without constraints...`);
    console.log(`   Max iterations: 1000 (or until timeout/convergence)`);
    console.log('\n' + '-'.repeat(70) + '\n');

    // Run autonomy loop
    const result = await orchestrator.executeAutonomyActionLoop(
      goal,
      1000, // Max iterations
      `unconstrained_run_${startTime}`
    );

    const elapsed = (Date.now() - startTime) / 1000;

    console.log('\n' + '-'.repeat(70));
    console.log('  RUN COMPLETED');
    console.log('-'.repeat(70) + '\n');

    // Display results
    console.log(`⏱️  Total Time: ${elapsed.toFixed(2)} seconds`);
    console.log(`   Status: ${result.status}`);
    console.log(`   Goal ID: ${result.goalId}`);
    console.log(`   Actions Executed: ${result.actionsExecuted}`);
    console.log(`   Claims Generated: ${result.claimsGenerated}`);

    if (result.reason) {
      console.log(`   Termination Reason: ${result.reason}`);
    }

    // Detailed analysis
    console.log('\n' + '='.repeat(70));
    console.log('  DETAILED ANALYSIS');
    console.log('='.repeat(70) + '\n');

    console.log(`🔍 Behavior Observations:`);
    console.log(`   • Autonomy Duration: ${elapsed.toFixed(2)}s (target: 120s)`);
    console.log(`   • Autonomy Efficiency: ${(result.actionsExecuted / elapsed).toFixed(2)} actions/sec`);
    console.log(`   • Claim Generation Rate: ${(result.claimsGenerated / elapsed).toFixed(2)} claims/sec`);

    if (elapsed < 120) {
      console.log(`\n⚠️  Early Termination: Completed in ${elapsed.toFixed(2)}s (target: 120s)`);
      console.log(`   Reason: ${result.reason || 'Unknown'}`);
      console.log(`   Actions before termination: ${result.actionsExecuted}`);
    } else {
      console.log(`\n✅ Full 2-minute autonomy run completed`);
    }

    // Observations
    console.log(`\n📊 System Observations:`);
    console.log(`   • Total Actions: ${result.actionsExecuted}`);
    console.log(`   • Claims Generated: ${result.claimsGenerated}`);
    console.log(`   • Final Status: ${result.status}`);

    if (result.claimsGenerated > 0) {
      console.log(`   • Avg Claims per Action: ${(result.claimsGenerated / result.actionsExecuted).toFixed(2)}`);
    }

    // Detect patterns and gaps
    console.log(`\n🔎 Autonomy Patterns & Gaps Detected:`);

    if (result.actionsExecuted === 0) {
      console.log(`   ❌ No actions executed - system may have encountered blocker`);
    } else if (result.actionsExecuted < 5) {
      console.log(`   ⚠️  Very few actions - possible early termination or constraint`);
    } else {
      console.log(`   ✅ Normal action execution rate`);
    }

    if (result.claimsGenerated === 0) {
      console.log(`   ⚠️  No claims generated - research may not be finding supported claims`);
    } else if (result.claimsGenerated < result.actionsExecuted) {
      console.log(`   ℹ️  Low claim generation rate (${result.claimsGenerated}/${result.actionsExecuted})`);
    } else {
      console.log(`   ✅ Good claim generation`);
    }

    // Save detailed log
    const logPath = path.join(__dirname, `../audit_artifacts/autonomy_unconstrained/run_${startTime}`);
    const fs_promises = require('fs').promises;

    try {
      await fs_promises.mkdir(logPath, { recursive: true });
      await fs_promises.writeFile(
        path.join(logPath, 'result.json'),
        JSON.stringify(
          {
            ...result,
            elapsed_seconds: elapsed,
            timestamp: new Date().toISOString(),
            goal: goal,
            api_key_used: !!apiKey
          },
          null,
          2
        )
      );

      console.log(`\n💾 Log saved to: ${logPath}/result.json`);
    } catch (logErr) {
      console.log(`\n⚠️  Could not save log: ${(logErr as any).message}`);
    }

    return true;
  } catch (err) {
    console.log(`❌ Error during autonomy run:`);
    console.log(`   ${(err as any).message}`);
    if (process.env.DEBUG) {
      console.log((err as any).stack);
    }
    return false;
  }
}

async function main(): Promise<number> {
  const success = await runUnconstrainedAutonomy();

  console.log('\n' + '='.repeat(70));
  console.log('  OBSERVATION COMPLETE');
  console.log('='.repeat(70) + '\n');

  if (success) {
    console.log('✅ Real-world autonomy observation successful');
  } else {
    console.log('❌ Real-world autonomy observation failed');
  }

  return success ? 0 : 1;
}

main()
  .then(code => process.exit(code))
  .catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
