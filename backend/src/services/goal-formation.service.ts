/**
 * Goal Formation Service
 * ======================
 * Bounded internal goal formation: AgentCo proposes its own goals from the
 * evidence graph and learning state instead of only receiving them from
 * users. Every proposal:
 *
 *   - cites the concrete DB objects that motivated it (goal_evidence rows)
 *   - carries a risk tier, budget, and stop condition
 *   - goes through the EXISTING goal lifecycle (proposed -> under_review ->
 *     approved -> active); nothing runs without governance rules
 *
 * Governance rules (approveProposedGoals):
 *   - low-risk internal evaluation/review goals auto-approve in local/test
 *     modes only
 *   - anything requiring live web/LLM or with risk >= medium stays
 *     under_review for human decision — fail closed, not open
 *
 * Sources inspected (all real runtime state):
 *   - learner candidates pending evaluation
 *   - unreviewed calibration demotions
 *   - stale domains (no recent trust window)
 *   - low-confidence unverified autonomy claims
 */

import { db } from '../db/client';
import { GoalManager } from './goal-manager.service';
import { activeRuntimeMode } from '../runtime-mode';

export interface GoalProposal {
  goalId: string;
  title: string;
  reason: string;
  sourceObjects: Array<{ table: string; id: string }>;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  domain: string;
  budget: { maxIterations: number; maxSeconds: number };
  stopCondition: string;
  requiresLiveServices: boolean;
}

const PROPOSER = 'goal-formation-service';

export class GoalFormationService {
  private goalManager = new GoalManager();

  /**
   * Inspect runtime state and propose bounded internal goals. Idempotent per
   * source object: an object that already has an open formation goal is not
   * proposed twice.
   */
  async proposeGoals(limit = 5): Promise<GoalProposal[]> {
    const proposals: GoalProposal[] = [];

    // 1. Candidates pending evaluation -> internal evaluation goals.
    const candidates = await db.query<{ id: string }>(
      `SELECT c.id
         FROM learner_candidates c
        WHERE c.status = 'ready_for_eval'
          AND NOT EXISTS (
                SELECT 1 FROM goal_evidence ge
                 JOIN autonomy_goals g ON g.id = ge.goal_id
                WHERE ge.evidence_ref = 'learner_candidates:' || c.id::text
                  AND g.status NOT IN ('rejected', 'retired', 'completed')
          )
        ORDER BY c.created_at ASC
        LIMIT $1`,
      [limit]
    );
    for (const row of candidates.rows) {
      proposals.push(
        await this.persistProposal({
          title: `Evaluate candidate skill ${row.id.slice(0, 8)}`,
          reason: 'learner candidate is ready_for_eval and has never been evaluated',
          sourceObjects: [{ table: 'learner_candidates', id: row.id }],
          riskLevel: 'low',
          domain: `internal_learning_${row.id.slice(0, 8)}`,
          budget: { maxIterations: 30, maxSeconds: 120 },
          stopCondition: 'candidate reaches evaluated/rejected status or budget exhausted',
          requiresLiveServices: false,
        })
      );
      if (proposals.length >= limit) return proposals;
    }

    // 2. Unreviewed calibration demotions -> governance review goals.
    const demotions = await db.query<{ id: string; payload: Record<string, unknown> }>(
      `SELECT e.id, e.payload
         FROM event_log e
        WHERE e.event_type = 'calibration.agent_demoted'
          AND NOT EXISTS (
                SELECT 1 FROM event_log reviewed
                 WHERE reviewed.event_type = 'civilization.demotion_reviewed'
                   AND reviewed.payload->>'demotion_event_id' = e.id::text
          )
          AND NOT EXISTS (
                SELECT 1 FROM goal_evidence ge
                 JOIN autonomy_goals g ON g.id = ge.goal_id
                WHERE ge.evidence_ref = 'event_log:' || e.id::text
                  AND g.status NOT IN ('rejected', 'retired', 'completed')
          )
        ORDER BY e.created_at ASC
        LIMIT $1`,
      [limit - proposals.length]
    );
    for (const row of demotions.rows) {
      proposals.push(
        await this.persistProposal({
          title: `Review calibration demotion of ${row.payload?.agent_id ?? 'unknown agent'}`,
          reason: 'calibration demotion event has not been institutionally reviewed',
          sourceObjects: [{ table: 'event_log', id: row.id }],
          riskLevel: 'low',
          domain: String(row.payload?.domain ?? 'internal_calibration'),
          budget: { maxIterations: 5, maxSeconds: 60 },
          stopCondition: 'demotion review recorded in event log',
          requiresLiveServices: false,
        })
      );
      if (proposals.length >= limit) return proposals;
    }

    // 3. Low-confidence unverified claims -> evidence collection goals.
    //    These need live web access, so they are proposed at medium risk and
    //    will NOT auto-approve.
    const claims = await db.query<{ row_id: string; claim_id: string; claim_text: string }>(
      `SELECT c.id AS row_id, c.claim_id, c.text AS claim_text
         FROM autonomy_claims c
        WHERE COALESCE(c.confidence, 0) < 0.5
          AND COALESCE(c.status, 'unverified') NOT IN ('verified', 'retired')
          AND NOT EXISTS (
                SELECT 1 FROM goal_evidence ge
                 JOIN autonomy_goals g ON g.id = ge.goal_id
                WHERE ge.evidence_ref IN (
                        'autonomy_claims:' || c.id::text,
                        'autonomy_claims:' || c.claim_id::text
                      )
                  AND g.status NOT IN ('rejected', 'retired', 'completed')
          )
        ORDER BY c.created_at ASC
        LIMIT $1`,
      [limit - proposals.length]
    );
    for (const row of claims.rows) {
      proposals.push(
        await this.persistProposal({
          title: `Collect independent evidence for low-confidence claim ${row.claim_id.slice(0, 8)}`,
          reason: `claim confidence below 0.5 and unverified: "${row.claim_text.slice(0, 120)}"`,
          sourceObjects: [
            { table: 'autonomy_claims', id: row.claim_id },
            { table: 'autonomy_claims', id: row.row_id },
          ],
          riskLevel: 'medium',
          domain: 'evidence_verification',
          budget: { maxIterations: 10, maxSeconds: 300 },
          stopCondition: 'two independent sources registered or budget exhausted',
          requiresLiveServices: true,
        })
      );
      if (proposals.length >= limit) return proposals;
    }

    return proposals;
  }

  /**
   * List previously formed goals that are still open (not executed,
   * rejected, or retired) so a subsequent free run can pick them up.
   */
  async listOpenFormationGoals(limit = 10): Promise<GoalProposal[]> {
    const rows = await db.query<{
      id: string;
      title: string;
      description: string | null;
      risk_level: string;
      domain: string;
      success_criteria_json: Record<string, unknown> | null;
      stop_conditions_json: Record<string, unknown> | null;
    }>(
      `SELECT id, title, description, risk_level, domain,
              success_criteria_json, stop_conditions_json
         FROM autonomy_goals
        WHERE proposed_by = $1
          AND status IN ('proposed', 'under_review', 'approved', 'active')
        ORDER BY created_at ASC
        LIMIT $2`,
      [PROPOSER, Math.max(1, Math.min(limit, 50))]
    );
    const proposals: GoalProposal[] = [];
    for (const row of rows.rows) {
      const evidence = await db.query<{ evidence_ref: string }>(
        `SELECT evidence_ref FROM goal_evidence WHERE goal_id = $1`,
        [row.id]
      );
      proposals.push({
        goalId: row.id,
        title: row.title,
        reason: row.description ?? '',
        sourceObjects: evidence.rows
          .map(r => r.evidence_ref.split(':'))
          .filter(parts => parts.length === 2)
          .map(([table, id]) => ({ table, id })),
        riskLevel: row.risk_level as GoalProposal['riskLevel'],
        domain: row.domain,
        budget: {
          maxIterations: Number(row.stop_conditions_json?.max_iterations ?? 10),
          maxSeconds: Number(row.stop_conditions_json?.max_seconds ?? 60),
        },
        stopCondition: String(row.success_criteria_json?.stop_condition ?? ''),
        requiresLiveServices: row.success_criteria_json?.requires_live_services === true,
      });
    }
    return proposals;
  }

  /**
   * Governance for self-generated goals. Only low-risk internal goals in
   * non-production modes auto-approve; everything else stays under_review.
   */
  async approveProposedGoals(goalIds: string[]): Promise<{ approved: string[]; held: string[] }> {
    const approved: string[] = [];
    const held: string[] = [];
    const mode = activeRuntimeMode();
    for (const goalId of goalIds) {
      const goal = await this.goalManager.getGoal(goalId);
      if (!goal) continue;
      if (goal.status === 'active') {
        approved.push(goalId);
        continue;
      }
      if (goal.status === 'approved') {
        await this.goalManager.activateGoal(goalId);
        approved.push(goalId);
        continue;
      }
      if (goal.status === 'proposed') {
        await this.goalManager.submitForReview(goalId);
      }
      const requiresLive = goal.success_criteria_json?.requires_live_services === true;
      const autoApprovable =
        goal.risk_level === 'low' && !requiresLive && (mode === 'test' || mode === 'development');
      if (autoApprovable) {
        try {
          await this.goalManager.reviewGoal(goalId, {
            reviewerId: 'goal-formation-governor',
            reviewerRole: 'governance_service',
            decision: 'approved',
            reason: 'low-risk internal goal auto-approved in local mode',
          });
          await this.goalManager.activateGoal(goalId);
          approved.push(goalId);
        } catch (error) {
          // Conflicts (e.g. another active goal in the same domain) hold the
          // goal for review instead of crashing the whole governance pass.
          console.warn(`goal ${goalId} held: ${error}`);
          held.push(goalId);
        }
      } else {
        held.push(goalId);
      }
    }
    return { approved, held };
  }

  private async persistProposal(input: Omit<GoalProposal, 'goalId'>): Promise<GoalProposal> {
    const { goalId } = await this.goalManager.proposeGoal({
      title: input.title,
      description: input.reason,
      source: 'agent_proposed',
      proposedBy: PROPOSER,
      domain: input.domain,
      riskLevel: input.riskLevel,
      autonomyLevelAllowed: 'L2',
      successCriteria: {
        stop_condition: input.stopCondition,
        requires_live_services: input.requiresLiveServices,
      },
      stopConditions: {
        max_iterations: input.budget.maxIterations,
        max_seconds: input.budget.maxSeconds,
      },
    });
    for (const source of input.sourceObjects) {
      await this.goalManager.attachEvidence(
        goalId,
        'formation_source',
        `${source.table}:${source.id}`,
        1.0,
        { reason: input.reason }
      );
    }
    await this.goalManager.setBudget(goalId, {
      timeBudgetSeconds: input.budget.maxSeconds,
      toolBudget: { max_iterations: input.budget.maxIterations },
    });
    return { goalId, ...input };
  }
}

export const goalFormation = new GoalFormationService();
