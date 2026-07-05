/**
 * Main-loop kill switch + budget enforcement (G6 / E1-E2)
 * =======================================================
 * The audit found the kill switch enforced only in supervised-free-run; the
 * flagship autonomy loop ignored it. These tests prove, without any LLM or
 * web access, that:
 *   1. an active kill switch refuses a run before it starts,
 *   2. an active kill switch halts the loop at the first iteration boundary
 *      (i.e. within one action) with an auditable event,
 *   3. budget exhaustion stops the run cleanly with an auditable event,
 *   4. the civilization scheduler refuses ticks and stops itself while a
 *      kill switch is active.
 * No LLM is needed because every halt fires BEFORE the planner would run.
 */

import crypto from 'crypto';
import { describe, expect, test, afterEach } from '@jest/globals';
import { db } from '../src/db/client';
import { killSwitchService } from '../src/services/kill-switch.service';
import { ledgerResolutionService } from '../src/services/resolution-service.service';
import { AutonomyOrchestratorService } from '../src/services/autonomy-orchestrator.service';
import { RunGuard } from '../src/services/run-guard.service';
import { civilizationSchedulerService } from '../src/services/civilization-scheduler.service';

async function actor(): Promise<string> {
  return ledgerResolutionService.ensureServiceActor('kill-switch-test-operator', ['governance.kill_switch']);
}

async function deactivateAll(scope: string): Promise<void> {
  const active = await killSwitchService.getActive(scope);
  if (active) {
    await killSwitchService.deactivate(scope, await actor(), 'test cleanup');
  }
}

describe('kill switch in the main autonomy loop (G6)', () => {
  afterEach(async () => {
    for (const scope of ['global', 'autonomy', 'autonomy.main_loop', 'civilization.scheduler']) {
      await deactivateAll(scope);
    }
  });

  test('an active kill switch refuses the run before any action', async () => {
    await killSwitchService.activate('autonomy', await actor(), 'kill-switch main-loop test');

    const orchestrator = new AutonomyOrchestratorService();
    const result = await orchestrator.executeAutonomyActionLoop(
      'kill-switch test goal: must not run',
      3
    );

    expect(result.status).toBe('halted');
    expect(result.actionsExecuted).toBe(0);
    expect(result.claimsGenerated).toBe(0);
    expect(result.reason).toMatch(/kill switch 'autonomy' active/);

    const events = await db.query(
      `SELECT payload FROM event_log
        WHERE event_type = 'autonomy.run_killed'
        ORDER BY occurred_at DESC LIMIT 1`
    );
    expect(events.rows.length).toBe(1);
    expect((events.rows[0] as any).payload.stage).toBe('run_start');
  });

  test('budget exhaustion halts the loop at the iteration boundary with an audit event', async () => {
    const orchestrator = new AutonomyOrchestratorService();
    // Zero wall-clock budget: the first iteration-boundary check must stop
    // the run before the planner or any external action.
    const result = await orchestrator.executeAutonomyActionLoop(
      'budget test goal: must stop at boundary',
      3,
      undefined,
      undefined,
      { maxWallClockMs: 0 }
    );

    expect(result.status).toBe('halted');
    expect(result.reason).toMatch(/wall-clock budget exhausted/);

    const events = await db.query(
      `SELECT payload FROM event_log
        WHERE event_type = 'autonomy.run_budget_stop'
        ORDER BY occurred_at DESC LIMIT 1`
    );
    expect(events.rows.length).toBe(1);
    expect((events.rows[0] as any).payload.kind).toBe('budget');
  });

  test('every guarded stage refuses work while the switch is active', async () => {
    await killSwitchService.activate('autonomy.main_loop', await actor(), 'stage-gate test');
    const guard = new RunGuard(`guard-test-${crypto.randomUUID().slice(0, 8)}`);
    for (const stage of ['run_start', 'iteration_boundary', 'before_planner_llm', 'before_action_execution', 'before_resolution_chain', 'before_promotion']) {
      const decision = await guard.checkHalt(stage);
      expect(decision.halted).toBe(true);
      expect(decision.kind).toBe('kill_switch');
    }
  });

  test('the civilization scheduler refuses ticks and stops itself under a kill switch', async () => {
    await killSwitchService.activate('civilization.scheduler', await actor(), 'scheduler kill test');
    civilizationSchedulerService.start(60_000);

    await expect(civilizationSchedulerService.runOnce('kill-switch-test')).rejects.toThrow(
      /scheduler tick refused: kill switch 'civilization.scheduler' active/
    );
    // The recurring timer must be down too, not just the single tick.
    expect(civilizationSchedulerService.status().running).toBe(false);
  });
});
