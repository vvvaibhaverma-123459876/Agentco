/**
 * Civilization Live Flow
 * ======================
 * Connects the institution layer to the LIVE runtime event stream so
 * civilization structures act on real system state instead of only
 * hand-seeded objects:
 *
 *   event stream (query of live runtime state)
 *     - learner candidates ready for evaluation
 *     - calibration demotion events awaiting governance review
 *   -> trust-ordered institution routing via the domain registry
 *   -> Improvement-department work request (bounded budget)
 *   -> department executes the REAL evaluation + canary services
 *   -> decision persisted on the work request + work-cycle events
 *   -> passing candidates are promoted (and thereby reach the planner's
 *      skill retrieval); failing candidates are rolled back
 *
 * Every step can fail honestly and leaves event lineage. The scheduler can
 * drive `runLiveFlowTick` the same way it drives reachability ticks.
 */

import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';
import { domainRegistry } from './domain-registry.service';
import { institutionWorkAssignmentService as institutionWorkAssignment } from './institution-work-assignment.service';
import { candidateEvaluation } from './candidate-evaluation.service';
import { skillCanary } from './skill-canary.service';
import { skillDeployment } from './skill-deployment.service';
import crypto from 'crypto';

export interface CivilizationEvent {
  eventType: 'candidate_ready_for_eval' | 'calibration_demotion_review';
  objectId: string;
  detail: Record<string, unknown>;
}

export interface LiveFlowOutcome {
  event: CivilizationEvent;
  institutionId: string;
  departmentId: string;
  workRequestId: string;
  decision: 'promoted' | 'rolled_back' | 'reviewed';
  skillVersionId: string | null;
}

export class CivilizationLiveFlowService {
  /**
   * F1: the live event stream. Reads pending work from real runtime state.
   * No synthetic events: if nothing is pending, the stream is empty.
   */
  async collectPendingEvents(
    limit = 10,
    options: { batchLabelPrefix?: string } = {}
  ): Promise<CivilizationEvent[]> {
    const events: CivilizationEvent[] = [];

    const candidates = await db.query<{ id: string; candidate_type: string }>(
      `SELECT c.id, c.candidate_type
         FROM learner_candidates c
         JOIN learner_runs r ON r.id = c.learner_run_id
         JOIN replay_batches b ON b.id = r.replay_batch_id
        WHERE c.status = 'ready_for_eval'
          AND ($2::text IS NULL OR b.batch_label LIKE $2 || '%')
        ORDER BY c.created_at ASC
        LIMIT $1`,
      [limit, options.batchLabelPrefix ?? null]
    );
    for (const row of candidates.rows) {
      events.push({
        eventType: 'candidate_ready_for_eval',
        objectId: row.id,
        detail: { candidate_type: row.candidate_type },
      });
    }

    const demotions = await db.query<{ id: string; payload: Record<string, unknown> }>(
      `SELECT e.id, e.payload
         FROM event_log e
        WHERE e.event_type = 'calibration.agent_demoted'
          AND NOT EXISTS (
                SELECT 1 FROM event_log reviewed
                 WHERE reviewed.event_type = 'civilization.demotion_reviewed'
                   AND reviewed.payload->>'demotion_event_id' = e.id::text
          )
        ORDER BY e.created_at ASC
        LIMIT $1`,
      [Math.max(0, limit - events.length)]
    );
    for (const row of demotions.rows) {
      events.push({
        eventType: 'calibration_demotion_review',
        objectId: row.id,
        detail: row.payload ?? {},
      });
    }

    return events.slice(0, limit);
  }

  /**
   * F2+F3: route pending events into institutions and let departments act.
   * Bounded: processes at most `limit` events per tick.
   */
  async runLiveFlowTick(
    domainKey: string,
    limit = 3,
    options: { batchLabelPrefix?: string } = {}
  ): Promise<LiveFlowOutcome[]> {
    const events = await this.collectPendingEvents(limit, options);
    const outcomes: LiveFlowOutcome[] = [];
    for (const event of events) {
      if (event.eventType === 'candidate_ready_for_eval') {
        outcomes.push(await this.processCandidateEvent(event, domainKey));
      } else {
        outcomes.push(await this.processDemotionReview(event, domainKey));
      }
    }
    return outcomes;
  }

  /**
   * A candidate-ready event flows through the domain-qualified institution's
   * Improvement department: evaluation -> canary -> promote or rollback.
   */
  private async processCandidateEvent(
    event: CivilizationEvent,
    domainKey: string
  ): Promise<LiveFlowOutcome> {
    const { institutionId, departmentId } = await this.routeToDepartment(domainKey, 'Improvement');

    await institutionWorkAssignment.assignSpecialistToDepartment(
      institutionId,
      departmentId,
      'candidate_evaluator',
      0.5
    );
    const workRequest = await institutionWorkAssignment.submitWorkRequest({
      institution_id: institutionId,
      department_id: departmentId,
      objective: `Evaluate learner candidate ${event.objectId} through evaluation and canary gates`,
      required_specialists: [{ role: 'candidate_evaluator', priority: 1 }],
      budget: { tokens: 0, iterations: 30, seconds: 120 },
      verification_required: true,
      risk_level: 'low',
    });
    await institutionWorkAssignment.updateWorkRequestStatus(workRequest.id, 'in_progress', {
      result_summary: { stage: 'evaluation' },
    });

    // The department does REAL work: evaluation + canary via the same
    // services the self-improvement loop uses.
    let decision: 'promoted' | 'rolled_back' = 'rolled_back';
    let skillVersionId: string | null = null;
    let summary: Record<string, unknown>;
    try {
      const evaluation = await candidateEvaluation.evaluateCandidate(event.objectId);
      if (!evaluation.passed) {
        summary = { stage: 'evaluation', passed: false, reason: evaluation.failureReason };
      } else {
        const canary = await skillCanary.runCanary({ candidateId: event.objectId, maxIterations: 20 });
        if (!canary.passed) {
          await skillDeployment.rollbackCandidate(event.objectId, 'canary failed in institution flow');
          summary = { stage: 'canary', passed: false, improvement: canary.improvement };
        } else {
          const skillKey = `institution_${event.objectId.slice(0, 8)}`;
          const deployed = await skillDeployment.promoteCandidate({
            candidateId: event.objectId,
            skillKey,
            domainKey,
            description: `Institution-vetted strategy from candidate ${event.objectId}.`,
          });
          decision = 'promoted';
          skillVersionId = deployed.skillVersionId;
          summary = {
            stage: 'promotion',
            passed: true,
            skill_version_id: deployed.skillVersionId,
            canary_improvement: canary.improvement,
          };
        }
      }
    } catch (error) {
      summary = { stage: 'error', passed: false, reason: String(error) };
    }

    await institutionWorkAssignment.updateWorkRequestStatus(
      workRequest.id,
      decision === 'promoted' ? 'completed' : 'failed',
      { result_summary: summary }
    );
    await this.recordFlowEvent('civilization.candidate_processed', {
      candidate_id: event.objectId,
      institution_id: institutionId,
      department_id: departmentId,
      work_request_id: workRequest.id,
      decision,
      ...summary,
    });

    return {
      event,
      institutionId,
      departmentId,
      workRequestId: workRequest.id,
      decision,
      skillVersionId,
    };
  }

  /**
   * A calibration demotion flows through the Audit department for review;
   * the review is recorded so the same demotion is not re-reviewed and the
   * agent's reduced authority is institutionally acknowledged.
   */
  private async processDemotionReview(
    event: CivilizationEvent,
    domainKey: string
  ): Promise<LiveFlowOutcome> {
    const { institutionId, departmentId } = await this.routeToDepartment(domainKey, 'Audit');
    await institutionWorkAssignment.assignSpecialistToDepartment(
      institutionId,
      departmentId,
      'calibration_auditor',
      0.5
    );
    const workRequest = await institutionWorkAssignment.submitWorkRequest({
      institution_id: institutionId,
      department_id: departmentId,
      objective: `Review calibration demotion event ${event.objectId}`,
      required_specialists: [{ role: 'calibration_auditor', priority: 1 }],
      budget: { tokens: 0, iterations: 5, seconds: 60 },
      verification_required: false,
      risk_level: 'low',
    });
    await institutionWorkAssignment.updateWorkRequestStatus(workRequest.id, 'completed', {
      result_summary: { reviewed_demotion: event.objectId, agent_id: event.detail.agent_id ?? null },
    });
    await this.recordFlowEvent('civilization.demotion_reviewed', {
      demotion_event_id: event.objectId,
      institution_id: institutionId,
      department_id: departmentId,
      work_request_id: workRequest.id,
      agent_id: event.detail.agent_id ?? null,
    });
    return {
      event,
      institutionId,
      departmentId,
      workRequestId: workRequest.id,
      decision: 'reviewed',
      skillVersionId: null,
    };
  }

  /**
   * Trust-ordered routing: the best qualified institution for the domain
   * (per domain registry) receives the work; routing fails closed when the
   * domain has no qualifying institution.
   */
  private async routeToDepartment(
    domainKey: string,
    departmentName: string
  ): Promise<{ institutionId: string; departmentId: string }> {
    const institution = await domainRegistry.bestInstitutionForDomain(domainKey);
    if (!institution) {
      throw new Error(`no qualifying institution for domain '${domainKey}'; live flow fails closed`);
    }
    const department = await db.query<{ id: string }>(
      `SELECT id FROM departments
        WHERE parent_id = $1 AND name = $2 AND status = 'active'
        LIMIT 1`,
      [institution.institution_id, departmentName]
    );
    if ((department.rowCount ?? 0) !== 1) {
      throw new Error(
        `institution ${institution.institution_id} lacks mandatory ${departmentName} department`
      );
    }
    return { institutionId: institution.institution_id, departmentId: department.rows[0].id };
  }

  private async recordFlowEvent(eventType: string, payload: Record<string, unknown>): Promise<void> {
    const actorId = await ledgerResolutionService.ensureServiceActor('agentco-civilization-live-flow', [
      'civilization.live_flow.record',
    ]);
    await eventLog.append({
      event_type: eventType,
      actor_id: actorId,
      object_type: 'civilization_live_flow',
      object_id: crypto.randomUUID(),
      payload,
    });
  }
}

export const civilizationLiveFlow = new CivilizationLiveFlowService();
