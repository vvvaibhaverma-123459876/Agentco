/**
 * Supervised Free-Run Service
 * ===========================
 * A bounded, kill-switchable autonomy loop over SELF-GENERATED goals:
 *
 *   tick:
 *     1. assert the free-run kill switch is not active (fail closed)
 *     2. propose internal goals from runtime state (GoalFormationService)
 *     3. governance-approve only low-risk internal goals (local/test mode)
 *     4. execute each approved goal through the real services
 *        (candidate evaluation via the civilization live flow; demotion
 *        reviews via the Audit flow)
 *     5. complete/fail goals with outcome references
 *   stop when: wall-clock limit, goal budget, kill switch, or nothing to do.
 *
 * Default mode requires NO LLM and NO web access. Goals that need live
 * services are never auto-approved here; they stay under_review for humans.
 * The summary is computed from database state, not from in-memory tallies
 * alone.
 */

import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';
import { goalFormation } from './goal-formation.service';
import { GoalManager } from './goal-manager.service';
import { civilizationLiveFlow } from './civilization-live-flow.service';
import { killSwitchService } from './kill-switch.service';
import { durableExecution } from './durable-execution.service';
import crypto from 'crypto';

export const FREE_RUN_KILL_SCOPE = 'autonomy.supervised_free_run';

export interface FreeRunResult {
  runId: string;
  startedAt: string;
  endedAt: string;
  stopReason: 'time_limit' | 'goal_limit' | 'kill_switch' | 'idle';
  goalsProposed: number;
  goalsApproved: number;
  goalsHeldForReview: number;
  goalsCompleted: number;
  goalsFailed: number;
  outcomes: Array<{ goalId: string; title: string; status: string; detail: string; workflowTaskId?: string }>;
}

export class SupervisedFreeRunService {
  private goalManager = new GoalManager();

  async run(options: {
    maxSeconds?: number;
    maxGoals?: number;
    domainKey: string;
  }): Promise<FreeRunResult> {
    const maxSeconds = Math.max(5, Math.min(options.maxSeconds ?? 600, 3600));
    const maxGoals = Math.max(1, Math.min(options.maxGoals ?? 5, 25));
    const runId = `free_run_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`;
    const startedAt = new Date();
    const deadline = startedAt.getTime() + maxSeconds * 1000;

    const outcomes: FreeRunResult['outcomes'] = [];
    let goalsProposed = 0;
    let goalsApproved = 0;
    let goalsHeld = 0;
    let stopReason: FreeRunResult['stopReason'] = 'idle';

    await this.recordRunEvent('autonomy.free_run_started', runId, {
      max_seconds: maxSeconds,
      max_goals: maxGoals,
      domain_key: options.domainKey,
    });

    while (true) {
      if (Date.now() >= deadline) {
        stopReason = 'time_limit';
        break;
      }
      if (outcomes.length >= maxGoals) {
        stopReason = 'goal_limit';
        break;
      }
      try {
        await killSwitchService.assertNotKilled(FREE_RUN_KILL_SCOPE);
      } catch {
        stopReason = 'kill_switch';
        break;
      }

      const fresh = await goalFormation.proposeGoals(Math.min(3, maxGoals - outcomes.length));
      goalsProposed += fresh.length;
      // Also pick up previously formed goals that are still open, so a goal
      // proposed in an earlier tick or run is not orphaned.
      const open = await goalFormation.listOpenFormationGoals(maxGoals - outcomes.length);
      const seen = new Set(fresh.map(p => p.goalId));
      const executedIds = new Set(outcomes.map(o => o.goalId));
      const proposals = [
        ...fresh,
        ...open.filter(p => !seen.has(p.goalId) && !executedIds.has(p.goalId)),
      ];
      if (proposals.length === 0) {
        stopReason = 'idle';
        break;
      }

      const { approved, held } = await goalFormation.approveProposedGoals(
        proposals.map(p => p.goalId)
      );
      goalsApproved += approved.length;
      goalsHeld += held.length;
      if (approved.length === 0) {
        stopReason = 'idle';
        break;
      }

      for (const goalId of approved) {
        if (Date.now() >= deadline) {
          stopReason = 'time_limit';
          break;
        }
        try {
          await killSwitchService.assertNotKilled(FREE_RUN_KILL_SCOPE);
        } catch {
          stopReason = 'kill_switch';
          break;
        }
        const proposal = proposals.find(p => p.goalId === goalId)!;
        try {
          const envelope = await this.executeGovernedGoalEnvelope({
            runId,
            goalId,
            title: proposal.title,
            sourceObjects: proposal.sourceObjects,
            domainKey: options.domainKey,
          });
          const detail = await this.executeGoal(proposal.sourceObjects, options.domainKey);
          await this.goalManager.completeGoal(goalId, `free_run:${runId}`);
          outcomes.push({ goalId, title: proposal.title, status: 'completed', detail, workflowTaskId: envelope.task_id });
        } catch (error) {
          await this.goalManager.pauseGoal(goalId, `free-run execution failed: ${error}`);
          outcomes.push({
            goalId,
            title: proposal.title,
            status: 'failed',
            detail: String(error),
          });
        }
      }
      if (stopReason === 'kill_switch' || stopReason === 'time_limit') break;
    }

    const endedAt = new Date();
    const completed = outcomes.filter(o => o.status === 'completed').length;
    const failed = outcomes.filter(o => o.status === 'failed').length;
    await this.recordRunEvent('autonomy.free_run_stopped', runId, {
      stop_reason: stopReason,
      goals_proposed: goalsProposed,
      goals_approved: goalsApproved,
      goals_held: goalsHeld,
      goals_completed: completed,
      goals_failed: failed,
      duration_ms: endedAt.getTime() - startedAt.getTime(),
      outcomes: outcomes.map(o => ({ goal_id: o.goalId, status: o.status, detail: o.detail.slice(0, 300), workflow_task_id: o.workflowTaskId ?? null })),
    });

    return {
      runId,
      startedAt: startedAt.toISOString(),
      endedAt: endedAt.toISOString(),
      stopReason,
      goalsProposed,
      goalsApproved,
      goalsHeldForReview: goalsHeld,
      goalsCompleted: completed,
      goalsFailed: failed,
      outcomes,
    };
  }

  /**
   * Record a governed durable task envelope before executing the domain
   * service. This keeps the free-run loop inside the same citizenship,
   * provenance, audit, and workflow-task controls as other protected work.
   */
  private async executeGovernedGoalEnvelope(input: {
    runId: string;
    goalId: string;
    title: string;
    sourceObjects: Array<{ table: string; id: string }>;
    domainKey: string;
  }): Promise<{ task_id: string }> {
    const task = await durableExecution.enqueue('reviewer-agent', 'review', {
      subject: `supervised free-run goal ${input.goalId}: ${input.title}`,
      criteria: [
        'goal has source DB evidence',
        'goal is approved for supervised execution',
        'execution remains bounded by the free-run budget',
      ],
      run_id: input.runId,
      goal_id: input.goalId,
      domain_key: input.domainKey,
      source_objects: input.sourceObjects,
    });
    const completed = await durableExecution.run(task.task_id);
    if (completed.status !== 'done') {
      throw new Error(`governed task envelope ${task.task_id} failed: ${completed.error ?? completed.status}`);
    }
    return { task_id: task.task_id };
  }

  /**
   * Execute one approved internal goal through the real runtime services.
   * Only internal goal types are executable here by design.
   */
  private async executeGoal(
    sourceObjects: Array<{ table: string; id: string }>,
    domainKey: string
  ): Promise<string> {
    const source = sourceObjects[0];
    if (!source) throw new Error('goal has no source object');
    if (source.table === 'learner_candidates') {
      const outcomes = await civilizationLiveFlow.runLiveFlowTick(domainKey, 1, {});
      const outcome = outcomes.find(o => o.event.objectId === source.id);
      if (!outcome) {
        // Process this specific candidate even if the stream ordering
        // surfaced others first.
        const all = await civilizationLiveFlow.runLiveFlowTick(domainKey, 10, {});
        const match = all.find(o => o.event.objectId === source.id);
        if (!match) throw new Error(`candidate ${source.id} was not processed by the live flow`);
        return `candidate ${source.id} decision: ${match.decision}`;
      }
      return `candidate ${source.id} decision: ${outcome.decision}`;
    }
    if (source.table === 'event_log') {
      const outcomes = await civilizationLiveFlow.runLiveFlowTick(domainKey, 10, {
        batchLabelPrefix: `no-candidates-${Date.now()}`,
      });
      const review = outcomes.find(o => o.event.objectId === source.id);
      if (!review) throw new Error(`demotion event ${source.id} was not reviewed`);
      return `demotion ${source.id} reviewed by institution ${review.institutionId}`;
    }
    throw new Error(
      `goal source ${source.table} requires live services and cannot run in supervised local mode`
    );
  }

  private async recordRunEvent(
    eventType: string,
    runId: string,
    payload: Record<string, unknown>
  ): Promise<void> {
    const actorId = await ledgerResolutionService.ensureServiceActor('agentco-supervised-free-run', [
      'autonomy.free_run.record',
    ]);
    await eventLog.append({
      event_type: eventType,
      actor_id: actorId,
      object_type: 'supervised_free_run',
      object_id: crypto.randomUUID(),
      payload: { run_id: runId, ...payload },
    });
  }
}

export const supervisedFreeRun = new SupervisedFreeRunService();
