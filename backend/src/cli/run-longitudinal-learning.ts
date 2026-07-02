#!/usr/bin/env ts-node
/**
 * Longitudinal Learning Run CLI
 * =============================
 * Runs the standard three-cycle longitudinal learning proof (deterministic,
 * clean-room: no LLM, no web) and writes a report GENERATED FROM DATABASE
 * STATE to reports/system_run/latest/.
 *
 * Usage:
 *   DATABASE_URL=postgresql://... ts-node src/cli/run-longitudinal-learning.ts
 */

import * as fs from 'fs';
import * as path from 'path';
import { longitudinalLearningHarness } from '../services/longitudinal-learning-harness.service';
import { pool } from '../db/client';

async function main() {
  const runLabel = `longrun_${Date.now()}`;
  console.log(`[longitudinal] starting run ${runLabel} (deterministic clean-room mode)`);

  const cycles = await longitudinalLearningHarness.runThreeCycles(runLabel);
  for (const cycle of cycles) {
    console.log(
      `[longitudinal] ${cycle.cycleLabel} family=${cycle.taskFamily} outcome=${cycle.outcome} ` +
        `baseline=${cycle.baselineScore.toFixed(3)} improved=${cycle.improvedScore?.toFixed(3) ?? 'n/a'} ` +
        `reused=${cycle.reused}`
    );
  }

  const report = await longitudinalLearningHarness.generateReport(runLabel);
  const outDir = path.resolve(__dirname, '../../../reports/system_run/latest');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(
    path.join(outDir, 'longitudinal_learning_report.json'),
    JSON.stringify(report, null, 2) + '\n'
  );
  const md = [
    '# Longitudinal Learning Report',
    '',
    `Generated from database state at ${report.generatedAt} (run label: \`${report.runLabel}\`).`,
    '',
    `- Improved cycles: ${report.improvedCycles}`,
    `- Rolled-back (demotion) cycles: ${report.rolledBackCycles}`,
    `- Durable improvement criterion met: ${report.durableImprovement}`,
    '',
    '| Cycle | Family | Domain | Baseline | Improved | Delta | Outcome |',
    '|---|---|---|---|---|---|---|',
    ...report.cycles.map(
      (c: any) =>
        `| ${c.cycle_label} | ${c.task_family} | ${c.domain} | ${Number(c.baseline_score).toFixed(3)} | ` +
        `${c.improved_score === null ? 'n/a' : Number(c.improved_score).toFixed(3)} | ` +
        `${c.score_delta === null ? 'n/a' : Number(c.score_delta).toFixed(3)} | ${c.outcome} |`
    ),
    '',
    'All rows above are read from `longitudinal_learning_cycles`; each row links a real',
    'candidate, evaluation, canary run, and (for improved cycles) promoted skill version',
    'with event-log lineage. Scores come from executed deterministic-benchmark policies,',
    'not projections. This is clean-room benchmark evidence, not live-web/LLM evidence.',
    '',
  ].join('\n');
  fs.writeFileSync(path.join(outDir, 'longitudinal_learning_report.md'), md);
  console.log(`[longitudinal] report written to ${outDir}/longitudinal_learning_report.{json,md}`);
  console.log(`[longitudinal] durable improvement: ${report.durableImprovement}`);

  await pool.end();
  if (!report.durableImprovement) {
    process.exitCode = 1;
  }
}

main().catch(error => {
  console.error(`[longitudinal] run failed: ${error}`);
  process.exitCode = 1;
});
