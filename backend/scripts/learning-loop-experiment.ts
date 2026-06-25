/**
 * Learning-loop experiment: does a reused goal AVOID the action it got stuck on?
 * Control (fresh goal) isolates learning from LLM temperature noise.
 */
import { db } from '../src/db/client';
import { AutonomyOrchestratorService } from '../src/services/autonomy-orchestrator.service';

const GOAL = 'Analyze emerging trends in distributed consensus algorithms and their tradeoffs.';

async function actionHistogram(goalId: string): Promise<Record<string, number>> {
  const r = await db.query(
    `SELECT action_type, count(*) c FROM autonomy_goal_actions WHERE goal_id=$1 GROUP BY action_type`, [goalId]);
  const h: Record<string, number> = {};
  for (const row of r.rows) h[row.action_type] = Number(row.c);
  return h;
}
async function reflectionCount(goalId: string): Promise<number> {
  const r = await db.query(
    `SELECT count(*) c FROM autonomy_memory WHERE content->>'type'='reflection' AND content->>'goalId'=$1`, [goalId]);
  return Number(r.rows[0].c);
}

(async () => {
  const orch = new AutonomyOrchestratorService();

  console.log('\n===== RUN 1 (establish a loop + store reflection) =====');
  const r1 = await orch.executeAutonomyActionLoop(GOAL, 8);
  const G = r1.goalId;
  console.log(`run1 goal=${G} status=${r1.status} reason=${r1.reason} actions=${r1.actionsExecuted} claims=${r1.claimsGenerated}`);
  console.log('run1 histogram:', JSON.stringify(await actionHistogram(G)));
  console.log('run1 reflections stored:', await reflectionCount(G));

  console.log('\n===== RUN 2a (REUSE goal G — planner sees run1 reflection) =====');
  const r2a = await orch.executeAutonomyActionLoop(GOAL, 8, undefined, G);
  console.log(`run2a goal=${r2a.goalId} status=${r2a.status} reason=${r2a.reason} actions=${r2a.actionsExecuted} claims=${r2a.claimsGenerated}`);
  // histogram of NEW actions in 2a = total minus run1; recompute full then note delta
  console.log('run2a+1 cumulative histogram:', JSON.stringify(await actionHistogram(G)));

  console.log('\n===== RUN 2b (CONTROL — fresh goal, same text, no reflection) =====');
  const r2b = await orch.executeAutonomyActionLoop(GOAL, 8);
  console.log(`run2b goal=${r2b.goalId} status=${r2b.status} reason=${r2b.reason} actions=${r2b.actionsExecuted} claims=${r2b.claimsGenerated}`);
  console.log('run2b histogram:', JSON.stringify(await actionHistogram(r2b.goalId)));
  console.log('run2b reflections (should be from its own loop only):', await reflectionCount(r2b.goalId));

  await db.end();
})();
