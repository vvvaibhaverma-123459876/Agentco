/**
 * Supervised Runtime (Phase F / G5)
 * =================================
 * The always-on-capable civilization loop, bounded and kill-switchable. The
 * audit found the scheduler manual, goal formation harness-only, judiciary
 * test-only, and persistent agents test-only — organs that never lived. One
 * `tick()` here drives them together on REAL runtime state:
 *
 *   0. RunGuard: check kill switch + budgets (halts within one tick);
 *   1. scheduler reachability tick (L14 graph liveness);
 *   2. independent resolver settles overdue predictions (true/false);
 *   3. judiciary rules on any resulting contradictions;
 *   4. goal formation proposes bounded internal goals from DB state, and
 *      governance auto-approves only low-risk local ones;
 *   5. civilization live-flow routes candidate/demotion events to
 *      institutions;
 *   6. a persistent "civic_reviewer" agent records that it operated (its
 *      trust/memory accumulate across ticks — a real lifecycle).
 *
 * Default mode is local/test with NO external side effects: no live LLM/web
 * unless the caller explicitly enables them. `runFor(ms)` loops tick() until
 * the kill switch, the budget, or the wall-clock deadline stops it — cleanly,
 * with an auditable reason.
 */

import { Pool } from 'pg';
import { db } from '../db/client';
import { resolutionServiceDatabaseUrl } from '../db/dsn';
import { RunGuard, RunBudget, AUTONOMY_KILL_SCOPES } from './run-guard.service';
import { civilizationSchedulerService } from './civilization-scheduler.service';
import { independentResolver } from './independent-resolver.service';
import { judiciaryReview } from './judiciary-review.service';
import { goalFormation } from './goal-formation.service';
import { civilizationLiveFlow } from './civilization-live-flow.service';
import { persistentAgentRegistry } from './persistent-agent-registry.service';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

const REVIEWER_ROLE = 'civic_reviewer';
const SUPERVISED_KILL_SCOPES = [...AUTONOMY_KILL_SCOPES, 'civilization.supervised_runtime'];

export interface SupervisedTickResult {
  tick: number;
  halted: boolean;
  haltReason?: string;
  reachabilityStatus: string | null;
  predictionsResolvedTrue: number;
  predictionsResolvedFalse: number;
  contradictionsRuled: number;
  goalsProposed: number;
  goalsApproved: number;
  liveFlowOutcomes: number;
  reviewerAgentId: string;
  reviewerReattached: boolean;
}

export interface SupervisedRunResult {
  ticks: number;
  stoppedBy: 'kill_switch' | 'budget' | 'deadline' | 'ticks';
  reason: string;
  results: SupervisedTickResult[];
}

export class SupervisedRuntimeService {
  private tickCount = 0;

  async tick(options: { domainKey?: string; guard?: RunGuard } = {}): Promise<SupervisedTickResult> {
    const domainKey = options.domainKey ?? 'autonomy_research';
    const guard = options.guard ?? new RunGuard(`supervised_${Date.now()}`, {}, SUPERVISED_KILL_SCOPES);
    this.tickCount += 1;

    const result: SupervisedTickResult = {
      tick: this.tickCount,
      halted: false,
      reachabilityStatus: null,
      predictionsResolvedTrue: 0,
      predictionsResolvedFalse: 0,
      contradictionsRuled: 0,
      goalsProposed: 0,
      goalsApproved: 0,
      liveFlowOutcomes: 0,
      reviewerAgentId: '',
      reviewerReattached: false,
    };

    // 0. Kill switch + budget.
    const halt = await guard.checkHalt('supervised_tick_start');
    if (halt.halted) {
      result.halted = true;
      result.haltReason = halt.reason;
      return result;
    }
    guard.recordIteration();

    // 1. Scheduler reachability tick (best-effort; failures are recorded).
    try {
      const reach = await civilizationSchedulerService.runOnce('supervised_runtime');
      result.reachabilityStatus = reach.status;
    } catch (error) {
      result.reachabilityStatus = `failed: ${error instanceof Error ? error.message.split('\n')[0] : error}`;
    }

    // 2. Settle overdue falsifiable predictions through the firewall.
    const servicePool = new Pool({ connectionString: resolutionServiceDatabaseUrl(), max: 2 });
    try {
      const client = await servicePool.connect();
      try {
        const sweep = await independentResolver.resolveDuePredictions({
          serviceClient: client,
          domain: domainKey,
        });
        result.predictionsResolvedTrue = sweep.resolvedTrue;
        result.predictionsResolvedFalse = sweep.resolvedFalse;
      } finally {
        client.release();
      }
    } finally {
      await servicePool.end();
    }

    // 3. Judiciary rules on any contradictions (from false resolutions).
    const rulings = await judiciaryReview.reviewOpenContradictions();
    result.contradictionsRuled = rulings.length;

    // 4. Bounded internal goal formation + governance approval.
    try {
      const proposals = await goalFormation.proposeGoals();
      result.goalsProposed = proposals.length;
      if (proposals.length > 0) {
        const decision = await goalFormation.approveProposedGoals(proposals.map(p => p.goalId));
        result.goalsApproved = decision.approved.length;
      }
    } catch (error) {
      console.warn(`[supervised-runtime] goal formation skipped: ${error}`);
    }

    // 5. Civilization live-flow: route candidate/demotion events.
    try {
      const outcomes = await civilizationLiveFlow.runLiveFlowTick(domainKey, 3);
      result.liveFlowOutcomes = outcomes.length;
    } catch (error) {
      console.warn(`[supervised-runtime] live-flow skipped: ${error}`);
    }

    // 6. Persistent reviewer agent operates — its identity/memory persist.
    const agent = await persistentAgentRegistry.ensureAgent(REVIEWER_ROLE);
    await persistentAgentRegistry.recordSpawn(REVIEWER_ROLE);
    result.reviewerAgentId = agent.agentId;
    result.reviewerReattached = agent.reattached;

    const actorId = await ledgerResolutionService.ensureServiceActor('agentco-supervised-runtime', [
      'runtime.tick',
    ]);
    await eventLog.append({
      event_type: 'supervised_runtime.tick',
      actor_id: actorId,
      object_type: 'supervised_runtime',
      object_id: agent.agentId,
      payload: {
        tick: result.tick,
        reachability: result.reachabilityStatus,
        predictions_true: result.predictionsResolvedTrue,
        predictions_false: result.predictionsResolvedFalse,
        contradictions_ruled: result.contradictionsRuled,
        goals_proposed: result.goalsProposed,
        goals_approved: result.goalsApproved,
        live_flow_outcomes: result.liveFlowOutcomes,
      },
    });

    return result;
  }

  /**
   * Run supervised ticks until the kill switch, the budget, the wall-clock
   * deadline, or maxTicks stops the loop — cleanly and auditably.
   */
  async runFor(input: {
    durationMs: number;
    tickIntervalMs?: number;
    maxTicks?: number;
    budget?: Partial<RunBudget>;
    domainKey?: string;
  }): Promise<SupervisedRunResult> {
    const deadline = Date.now() + Math.max(0, input.durationMs);
    const interval = Math.max(0, input.tickIntervalMs ?? 0);
    const maxTicks = Math.max(1, input.maxTicks ?? 1000);
    const guard = new RunGuard(
      `supervised_run_${Date.now()}`,
      { maxWallClockMs: input.durationMs, ...input.budget },
      SUPERVISED_KILL_SCOPES
    );
    const results: SupervisedTickResult[] = [];
    let stoppedBy: SupervisedRunResult['stoppedBy'] = 'deadline';
    let reason = 'wall-clock deadline reached';

    while (results.length < maxTicks) {
      if (Date.now() >= deadline) {
        stoppedBy = 'deadline';
        reason = 'wall-clock deadline reached';
        break;
      }
      const tick = await this.tick({ domainKey: input.domainKey, guard });
      results.push(tick);
      if (tick.halted) {
        stoppedBy = tick.haltReason?.includes('budget') ? 'budget' : 'kill_switch';
        reason = tick.haltReason ?? 'halted';
        break;
      }
      if (results.length >= maxTicks) {
        stoppedBy = 'ticks';
        reason = `reached maxTicks=${maxTicks}`;
        break;
      }
      if (interval > 0 && Date.now() + interval < deadline) {
        await new Promise(resolve => setTimeout(resolve, interval));
      }
    }

    return { ticks: results.length, stoppedBy, reason, results };
  }
}

export const supervisedRuntime = new SupervisedRuntimeService();
