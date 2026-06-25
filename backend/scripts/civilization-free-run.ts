#!/usr/bin/env npx ts-node
/**
 * Civilization Free-Run entry point (vision primary objective).
 *
 *   npx ts-node scripts/civilization-free-run.ts --mode fixture          # deterministic, CI-safe
 *   npx ts-node scripts/civilization-free-run.ts --mode read_only_web    # real loop (needs LLM key)
 *
 * Runs WITHOUT a user-given goal: self-assessment → internal goal → society agenda → bounded task
 * → claim → promotion gate → prediction registration → report artifact.
 */
import { db } from '../src/db/client';
import { civilizationFreeRun, FreeRunMode } from '../src/services/civilization-free-run.service';
import { autonomyOrchestrator } from '../src/services/autonomy-orchestrator.service';

function arg(name: string, def: string): string {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : def;
}

async function main() {
  const mode = arg('mode', 'fixture') as FreeRunMode;
  console.log(`\n🌐 Civilization Free-Run starting (mode=${mode}, no user goal)\n`);

  // For read_only_web, the bounded task IS the hardened autonomy loop run on the internal goal.
  const boundedTask = async (goalId: string): Promise<string[]> => {
    const goalRow = await db.query(`SELECT description FROM autonomy_goals WHERE id = $1`, [goalId]);
    const goalText = goalRow.rows[0]?.description || 'Investigate an under-covered research topic.';
    await autonomyOrchestrator.executeAutonomyActionLoop(goalText, 8, undefined, goalId);
    const claims = await db.query(
      `SELECT claim_id FROM autonomy_claims WHERE action_id IN
         (SELECT action_id FROM autonomy_goal_actions WHERE goal_id = $1)`, [goalId]);
    return claims.rows.map((r: { claim_id: string }) => r.claim_id);
  };

  const report = await civilizationFreeRun.run(mode, mode === 'read_only_web' ? boundedTask : undefined);

  console.log('\n===== FREE-RUN REPORT =====');
  console.log(`run:         ${report.runId}`);
  console.log(`weaknesses:  ${report.weaknesses.map(w => w.kind).join(', ')}`);
  console.log(`internalGoal:${report.internalGoalId}`);
  console.log(`agenda:      ${report.agendaItemId} (${report.societyId})`);
  console.log(`claims:      processed=${report.claimsProcessed} promoted=${report.claimsPromoted} blocked=${report.claimsBlocked}`);
  console.log(`predictions: ${report.predictionsRegistered}`);
  console.log(`report:      ${report.reportDir}/civilization_report.md`);
  if (report.errors.length) console.log(`errors:      ${report.errors.join('; ')}`);
  console.log('===========================\n');

  await db.end();
}

main().catch(async (e) => { console.error('Free-run failed:', e); await db.end(); process.exit(1); });
