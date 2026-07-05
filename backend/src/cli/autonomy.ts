#!/usr/bin/env ts-node
/**
 * Autonomy CLI (D10)
 * ==================
 * The single first-class entrypoint for a full autonomous run:
 *   fetch -> grounded claims -> falsifiable predictions (future due time) ->
 *   independent resolution (true/false/open) -> auto-promotion ->
 *   user-readable deliverable. Overdue predictions from earlier runs are
 *   settled (possibly FALSE) at the start of the resolution stage.
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
    `[autonomy] run=${result.runId}${result.halted ? ` HALTED: ${result.halted}` : ''}\n` +
      `  claims=${result.claims} predictions=${result.predictionsRegistered} ` +
      `resolved=${result.predictionsResolved} (false=${result.predictionsResolvedFalse}, ` +
      `open=${result.predictionsOpen}) lessonsPromoted=${result.lessonsPromoted}\n` +
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
