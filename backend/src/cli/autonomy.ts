#!/usr/bin/env ts-node
/**
 * Autonomy CLI (D10)
 * ==================
 * The single first-class entrypoint for a full autonomous run:
 *   fetch -> grounded claims -> predictions -> grounded resolution ->
 *   auto-promotion -> user-readable deliverable.
 *
 * Usage:
 *   npm run autonomy -- --goal "Research X" --iterations 6 --output-dir outputs
 *
 * Requires LLM_API_KEY/OPENAI_API_KEY and DATABASE_URL. Deliverable is written
 * to the output dir (default: <repo>/outputs).
 */

import { autonomyRun } from '../services/autonomy-run.service';
import { pool } from '../db/client';

function arg(name: string, fallback?: string): string | undefined {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

async function main() {
  const goal = arg('goal');
  if (!goal) {
    console.error('usage: npm run autonomy -- --goal "..." [--iterations 6] [--output-dir outputs]');
    process.exitCode = 2;
    return;
  }
  const iterations = Number(arg('iterations', '6'));
  const outputDir = arg('output-dir');

  console.log(`[autonomy] goal="${goal}" iterations=${iterations} model=${process.env.LLM_MODEL_DEFAULT ?? 'gpt-4o-mini'}`);
  const result = await autonomyRun.run({ goal, maxIterations: iterations, outputDir });

  console.log(
    `[autonomy] run=${result.runId}\n` +
      `  claims=${result.claims} predictions=${result.predictionsRegistered} ` +
      `resolved=${result.predictionsResolved} lessonsPromoted=${result.lessonsPromoted}\n` +
      `  evidence=${result.evidenceUrls.length} sources\n` +
      `  deliverable=${result.deliverablePath ?? '(none)'}`
  );
  await pool.end();
}

main().catch(async e => {
  console.error(`[autonomy] failed: ${e}`);
  try { await pool.end(); } catch {}
  process.exitCode = 1;
});
