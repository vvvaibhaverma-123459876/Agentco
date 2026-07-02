#!/usr/bin/env ts-node
/**
 * Supervised Free-Run CLI
 * =======================
 * Bounded self-directed run over internally proposed goals. Default mode is
 * local: no LLM, no web; goals that need live services are held for human
 * review instead of executed.
 *
 * Usage:
 *   npm run agentco:supervised-free-run -- --minutes 10 --max-goals 5 --domain internal_learning
 *
 * Stop guarantees: wall-clock limit, goal budget, kill switch
 * (scope autonomy.supervised_free_run), or idle (nothing to propose).
 */

import { supervisedFreeRun } from '../services/supervised-free-run.service';
import { pool } from '../db/client';

function argValue(name: string, fallback: string): string {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

async function main() {
  const minutes = Number(argValue('minutes', '10'));
  const maxGoals = Number(argValue('max-goals', '5'));
  const domain = argValue('domain', 'internal_learning');

  console.log(
    `[free-run] starting supervised free run: ${minutes} minutes, ${maxGoals} goals max, domain ${domain}`
  );
  const result = await supervisedFreeRun.run({
    maxSeconds: Math.round(minutes * 60),
    maxGoals,
    domainKey: domain,
  });

  console.log(`[free-run] run ${result.runId} stopped: ${result.stopReason}`);
  console.log(
    `[free-run] proposed=${result.goalsProposed} approved=${result.goalsApproved} ` +
      `held=${result.goalsHeldForReview} completed=${result.goalsCompleted} failed=${result.goalsFailed}`
  );
  for (const outcome of result.outcomes) {
    console.log(`[free-run]   ${outcome.status}: ${outcome.title} — ${outcome.detail}`);
  }
  await pool.end();
}

main().catch(error => {
  console.error(`[free-run] failed: ${error}`);
  process.exitCode = 1;
});
