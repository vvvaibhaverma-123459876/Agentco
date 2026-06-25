/**
 * Deterministic cross-run learning test: SEED a lesson for goal G (spawn_specialist failed),
 * then prove a REUSED run honors it (overrides spawn_specialist) vs a FRESH control that doesn't.
 */
import { db } from '../src/db/client';
import { v4 as uuid } from 'uuid';
import { AutonomyOrchestratorService } from '../src/services/autonomy-orchestrator.service';

const GOAL = 'Analyze emerging trends in distributed consensus algorithms and their tradeoffs.';

async function executedCount(goalId: string, type: string): Promise<number> {
  const r = await db.query(`SELECT count(*) c FROM autonomy_goal_actions WHERE goal_id=$1 AND action_type=$2`, [goalId, type]);
  return Number(r.rows[0].c);
}

(async () => {
  const orch = new AutonomyOrchestratorService();
  const G = uuid();

  // Create goal G and SEED a reflection flagging spawn_specialist as repeatedly-failed.
  await db.query(
    `INSERT INTO autonomy_goals (id, title, description, source, domain, expected_value, risk_level, autonomy_level_allowed, status, proposed_by)
     VALUES ($1,$2,$3,'agent_proposed','research',0.7,'low','L3','approved','test')`,
    [G, GOAL.substring(0,100), GOAL]);
  await db.query(
    `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at) VALUES ($1, NULL, $2, NOW(), NOW())`,
    [uuid(), JSON.stringify({ type:'reflection', goalId:G, loopType:'identical_action_repeat', streak:3,
      failurePattern:'spawn_specialist was repeated 3 times with args: {"role":"background_researcher"}',
      suggestedStrategy:'spawn_specialist fails; TRY evaluate_progress', confidence:0.9,
      summary:'LOOP: spawn_specialist blocked every time' })]);
  console.log(`Seeded reflection for goal G=${G} flagging spawn_specialist\n`);

  console.log('===== REUSE G (sees seeded lesson) =====');
  const r2a = await orch.executeAutonomyActionLoop(GOAL, 8, undefined, G);
  console.log(`reuse: status=${r2a.status} actions=${r2a.actionsExecuted} spawn_specialist EXECUTED=${await executedCount(G, 'spawn_specialist')}`);

  console.log('\n===== CONTROL fresh goal (no lesson) =====');
  const r2b = await orch.executeAutonomyActionLoop(GOAL, 8);
  console.log(`control: goal=${r2b.goalId} status=${r2b.status} actions=${r2b.actionsExecuted} spawn_specialist EXECUTED=${await executedCount(r2b.goalId, 'spawn_specialist')}`);

  await db.end();
})();
