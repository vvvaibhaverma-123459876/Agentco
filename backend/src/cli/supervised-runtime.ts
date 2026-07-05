#!/usr/bin/env ts-node
/**
 * Supervised Runtime CLI (Phase F / G5)
 * =====================================
 * Runs the bounded, kill-switchable civilization loop for a fixed duration.
 * Default mode is local/test with no external side effects.
 *
 * Usage:
 *   npm run agentco:supervised-runtime -- --duration-ms 600000 --tick-interval-ms 5000
 *   npm run agentco:supervised-runtime -- --ticks 1     # single tick
 *
 * Stops cleanly on the kill switch (scope 'global', 'autonomy', or
 * 'civilization.supervised_runtime'), on budget exhaustion, or at the
 * deadline.
 */

import { supervisedRuntime } from '../services/supervised-runtime.service';
import { pool } from '../db/client';

function arg(name: string, fallback?: string): string | undefined {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

async function main() {
  const durationMs = Number(arg('duration-ms', '0'));
  const tickIntervalMs = Number(arg('tick-interval-ms', '0'));
  const maxTicks = Number(arg('ticks', durationMs > 0 ? '1000' : '1'));

  console.log(
    `[supervised-runtime] duration=${durationMs}ms interval=${tickIntervalMs}ms maxTicks=${maxTicks}`
  );
  const result = await supervisedRuntime.runFor({ durationMs, tickIntervalMs, maxTicks });

  const totals = result.results.reduce(
    (acc, t) => ({
      resolvedFalse: acc.resolvedFalse + t.predictionsResolvedFalse,
      resolvedTrue: acc.resolvedTrue + t.predictionsResolvedTrue,
      ruled: acc.ruled + t.contradictionsRuled,
      proposed: acc.proposed + t.goalsProposed,
      approved: acc.approved + t.goalsApproved,
    }),
    { resolvedFalse: 0, resolvedTrue: 0, ruled: 0, proposed: 0, approved: 0 }
  );

  console.log(
    `[supervised-runtime] ticks=${result.ticks} stoppedBy=${result.stoppedBy} (${result.reason})\n` +
      `  predictions resolved: true=${totals.resolvedTrue} false=${totals.resolvedFalse}\n` +
      `  contradictions ruled=${totals.ruled} goals proposed=${totals.proposed} approved=${totals.approved}`
  );
  await pool.end();
}

main().catch(async e => {
  console.error(`[supervised-runtime] failed: ${e}`);
  try { await pool.end(); } catch {}
  process.exitCode = 1;
});
