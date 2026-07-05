/**
 * Run Guard (G6 / E1-E2)
 * ======================
 * Enforces the kill switch and hard budgets INSIDE the main autonomy runtime.
 * The audit found kill-switch checks only in supervised-free-run; the flagship
 * loop (orchestrator -> planner -> executor -> resolver -> promotion) never
 * consulted it. Every stage of the main loop now asks this guard before doing
 * work, so activating the switch halts a run within one action.
 *
 * Scopes checked (any active switch halts):
 *   - 'global'             emergency stop for everything
 *   - 'autonomy'           all autonomy runs
 *   - 'autonomy.main_loop' the flagship action loop specifically
 *
 * Budgets are hard ceilings; exhaustion stops the run cleanly with an
 * auditable event, never silently.
 */

import crypto from 'crypto';
import { killSwitchService } from './kill-switch.service';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export const AUTONOMY_KILL_SCOPES = ['global', 'autonomy', 'autonomy.main_loop'];

export interface RunBudget {
  maxIterations: number;
  maxWallClockMs: number;
  maxWebFetches: number;
  maxSearchCalls: number;
  maxLlmCalls: number;
  maxBytesFetched: number;
}

export const DEFAULT_RUN_BUDGET: RunBudget = {
  maxIterations: 10,
  maxWallClockMs: 10 * 60 * 1000,
  maxWebFetches: 30,
  maxSearchCalls: 15,
  maxLlmCalls: 40,
  maxBytesFetched: 20 * 1024 * 1024,
};

export interface HaltDecision {
  halted: boolean;
  kind?: 'kill_switch' | 'budget';
  reason?: string;
}

export class RunGuard {
  private readonly budget: RunBudget;
  private readonly startedAt = Date.now();
  private usage = { iterations: 0, webFetches: 0, searchCalls: 0, llmCalls: 0, bytesFetched: 0 };

  constructor(
    private readonly runId: string,
    budget: Partial<RunBudget> = {},
    private readonly scopes: string[] = AUTONOMY_KILL_SCOPES
  ) {
    this.budget = { ...DEFAULT_RUN_BUDGET, ...budget };
  }

  recordIteration(): void { this.usage.iterations++; }
  recordWebFetch(bytes = 0): void { this.usage.webFetches++; this.usage.bytesFetched += bytes; }
  recordSearchCall(): void { this.usage.searchCalls++; }
  recordLlmCall(): void { this.usage.llmCalls++; }

  usageSnapshot(): Record<string, number> {
    return { ...this.usage, wallClockMs: Date.now() - this.startedAt };
  }

  /**
   * Check kill switch + budgets at a stage boundary. On halt, appends an
   * auditable event and returns the decision; callers must stop the run.
   */
  async checkHalt(stage: string): Promise<HaltDecision> {
    for (const scope of this.scopes) {
      const active = await killSwitchService.getActive(scope);
      if (active) {
        const reason = `kill switch '${scope}' active: ${active.reason}`;
        await this.appendHaltEvent(stage, 'kill_switch', reason);
        return { halted: true, kind: 'kill_switch', reason };
      }
    }
    const overBudget = this.budgetViolation();
    if (overBudget) {
      await this.appendHaltEvent(stage, 'budget', overBudget);
      return { halted: true, kind: 'budget', reason: overBudget };
    }
    return { halted: false };
  }

  /** Convenience for stages that must throw instead of branching. */
  async assertCanContinue(stage: string): Promise<void> {
    const decision = await this.checkHalt(stage);
    if (decision.halted) {
      throw new Error(`run halted at ${stage}: ${decision.reason}`);
    }
  }

  private budgetViolation(): string | null {
    const elapsed = Date.now() - this.startedAt;
    const b = this.budget;
    const u = this.usage;
    if (u.iterations > b.maxIterations) return `iteration budget exhausted (${u.iterations}/${b.maxIterations})`;
    if (elapsed > b.maxWallClockMs) return `wall-clock budget exhausted (${elapsed}ms/${b.maxWallClockMs}ms)`;
    if (u.webFetches > b.maxWebFetches) return `web fetch budget exhausted (${u.webFetches}/${b.maxWebFetches})`;
    if (u.searchCalls > b.maxSearchCalls) return `search budget exhausted (${u.searchCalls}/${b.maxSearchCalls})`;
    if (u.llmCalls > b.maxLlmCalls) return `LLM call budget exhausted (${u.llmCalls}/${b.maxLlmCalls})`;
    if (u.bytesFetched > b.maxBytesFetched) return `fetched-bytes budget exhausted (${u.bytesFetched}/${b.maxBytesFetched})`;
    return null;
  }

  private async appendHaltEvent(stage: string, kind: string, reason: string): Promise<void> {
    try {
      const actorId = await ledgerResolutionService.ensureServiceActor('agentco-run-guard', [
        'autonomy.run.halt',
      ]);
      await eventLog.append({
        event_type: kind === 'kill_switch' ? 'autonomy.run_killed' : 'autonomy.run_budget_stop',
        actor_id: actorId,
        object_type: 'autonomy_run',
        // event_log requires a UUID object_id; run ids are human-readable
        // strings, so they travel in the payload instead.
        object_id: crypto.randomUUID(),
        payload: { run_id: this.runId, stage, kind, reason, usage: this.usageSnapshot() },
      });
    } catch (error) {
      // The halt itself must never be blocked by event-log failure; surface it.
      console.error(`[RunGuard] failed to append halt event: ${error}`);
    }
  }
}
