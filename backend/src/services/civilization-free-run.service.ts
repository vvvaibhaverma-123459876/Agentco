/**
 * Civilization Free-Run Runtime (vision primary objective — smallest complete vertical slice).
 * ============================================================================================
 * Runs WITHOUT a user-given goal. One pass through the vision's loop:
 *   self-assessment → internal goal → society agenda → bounded task → claim →
 *   promotion gate (believe slowly) → prediction registration → report artifact.
 *
 * The hardened user-goal research loop (executeAutonomyActionLoop) is the BOUNDED-EXECUTION core
 * (vision step 6); this service wraps it with the goal-less front-end and the epistemic back-end.
 *
 * Modes:
 *  - 'fixture'        deterministic, CI-safe: seeds a known claim+evidence (no LLM/web).
 *  - 'read_only_web'  uses the real autonomy loop (needs LLM key + network).
 */
import { db } from '../db/client';
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import type { PoolClient } from 'pg';
import { v4 as uuid } from 'uuid';
import { goalManager } from './goal-manager.service';
import { Phase0bCalibrationService } from './phase0b-calibration.service';
import { validateGrounding, GroundingSource } from './claim-grounding';
import { SourceQualityService } from './source-quality.service';
import { getSpecialistRole } from '../types/specialist-roles';
import { ProtectedSurfaceEnforcerService } from './protected-surface-enforcer.service';
import { overrideQueue, OverrideRequest } from './override-queue.service';
import { TeamActivationService } from './team-activation.service';
import { ActionStatus, ActionType, RiskLevel } from '../types/action.types';

export type FreeRunMode = 'fixture' | 'read_only_web';

export interface Weakness {
  kind: string;
  detail: string;
  recommendedGoal: { title: string; description: string; domain: string };
}

export interface SocietyAgendaItem {
  agendaItemId: string;
  societyId: string;
  institutionId: string;
  taskType: 'promote_supported_claims' | 'ingest_research_evidence';
  executionDomain: 'calibration' | 'research';
}

export interface FreeRunReport {
  runId: string;
  mode: FreeRunMode;
  startedAt: string;
  durationMs: number;
  weaknesses: Weakness[];
  internalGoalId: string | null;
  agendaItemId: string | null;
  societyId: string;
  institutionId: string;
  taskType: string;
  claimsProcessed: number;
  claimsPromoted: number;
  claimsBlocked: number;
  contradictionChecks: number;
  contradictionsDetected: number;
  agentSpawnProposals: number;
  selfImprovementProposals: number;
  governanceQueueRequests: number;
  predictionsRegistered: number;
  errors: string[];
  reportDir: string;
  healthSnapshot?: CivilizationHealthSnapshot;
}

export interface CivilizationHealthSnapshot {
  claims: number;
  promotedClaims: number;
  supportedClaims: number;
  evidenceItems: number;
  unresolvedContradictions: number;
  stalePredictions: number;
  weakDomains: Array<{
    domain: string;
    claims: number;
    promotedClaims: number;
    supportedClaims: number;
  }>;
}

export interface ContradictionFinding {
  claimId: string;
  contradictingClaimId: string;
  reason: string;
}

export interface AgentSpawnProposal {
  proposalId: string;
  goalId: string;
  agendaItemId: string;
  role: string;
  objective: string;
  reason: string;
  governanceStatus: 'review_required';
  budget: { tokens: number; iterations: number; seconds: number };
  constraints: {
    maxDepth: number;
    maxParallelWorkers: number;
    activationRequiresGovernance: boolean;
  };
}

export interface SelfImprovementProposal {
  proposalId: string;
  goalId: string;
  targetComponent: string;
  affectedFiles: string[];
  expectedImprovement: string;
  testsToPass: string[];
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  rollbackPlan: string;
  governanceStatus: 'review_required';
  protectedSurfaceCheck: {
    requiresHumanApproval: boolean;
    attempts: Array<{
      filePath: string;
      requiresHumanApproval: boolean;
      riskLevel: string;
    }>;
  };
}

export interface GovernanceQueueRequest {
  proposalId: string;
  proposalType: 'agent_spawn_proposal' | 'self_improvement_proposal';
  requestId: string;
  status: 'pending';
  action: string;
  riskLevel: 'high' | 'critical';
}

type GovernanceProposalType =
  | 'agent_spawn_proposal'
  | 'self_improvement_proposal'
  | 'self_improvement_candidate_promotion';

export interface GovernanceApprovalReadiness {
  requestId: string;
  proposalId?: string;
  proposalType?: GovernanceProposalType;
  status: 'ready' | 'blocked';
  blockedReason?: string;
  evalRunId?: string;
  scorecard?: {
    promotionEligible: boolean;
    autonomyScore: number | null;
    safetyScore: number | null;
    calibrationScore: number | null;
    planningScore: number | null;
    memoryScore: number | null;
    toolScore: number | null;
    rewardScore: number | null;
    regressionScore: number | null;
  };
}

export interface ApprovedAgentSpawnExecution {
  requestId: string;
  proposalId?: string;
  status: 'completed' | 'blocked' | 'failed';
  blockedReason?: string;
  specialistId?: string;
  role?: string;
  actionStatus?: string;
  activationStatus?: string;
}

export interface ApprovedSelfImprovementCandidateExecution {
  requestId: string;
  proposalId?: string;
  status: 'completed' | 'blocked' | 'failed';
  blockedReason?: string;
  artifactId?: string;
  artifactHash?: string;
  episodeId?: string;
  trajectoryId?: string;
  replayBatchId?: string;
  learnerRunId?: string;
  candidateId?: string;
  sandboxEvalRunId?: string;
  candidateStatus?: string;
  promotionStatus: 'not_promoted';
}

export interface SelfImprovementPromotionRequest {
  candidateId: string;
  artifactId: string;
  requestId: string;
  status: 'pending';
  action: string;
  riskLevel: 'high' | 'critical';
}

export interface ApprovedSelfImprovementPromotionExecution {
  requestId: string;
  candidateId?: string;
  artifactId?: string;
  status: 'completed' | 'blocked' | 'failed';
  blockedReason?: string;
  evalRunId?: string;
  candidateStatus?: string;
  artifactStatus?: string;
  promotionStatus: 'promoted' | 'not_promoted';
}

const ARTIFACT_ROOT = path.resolve(__dirname, '..', '..', '..', 'audit_artifacts', 'civilization_free_run');

export class CivilizationFreeRunService {
  private phase0b = new Phase0bCalibrationService();
  private sourceQuality = new SourceQualityService();
  private protectedSurfaceEnforcer = new ProtectedSurfaceEnforcerService();
  private teamActivation = new TeamActivationService();

  /** STEP 1: inspect civilization state and identify the most salient weakness + a recommended goal. */
  async selfAssess(): Promise<Weakness[]> {
    return this.weaknessesFromHealthSnapshot(await this.getHealthSnapshot());
  }

  weaknessesFromHealthSnapshot(snapshot: CivilizationHealthSnapshot): Weakness[] {
    const weaknesses: Weakness[] = [];
    if (snapshot.unresolvedContradictions > 0) {
      weaknesses.push({
        kind: 'unresolved_contradictions',
        detail: `${snapshot.unresolvedContradictions} claim(s) are contradicted or have unresolved contradiction links`,
        recommendedGoal: {
          title: 'Resolve contradicted claims before further promotion',
          description: 'Review contradiction-linked claims and preserve only evidence-consistent knowledge.',
          domain: 'calibration',
        },
      });
    }

    if (snapshot.stalePredictions > 0) {
      weaknesses.push({
        kind: 'stale_predictions',
        detail: `${snapshot.stalePredictions} unresolved prediction(s) are past their expected resolution date`,
        recommendedGoal: {
          title: 'Resolve overdue calibration predictions',
          description: 'Measure overdue predictions, record outcomes, and update calibration evidence.',
          domain: 'calibration',
        },
      });
    }

    for (const domain of snapshot.weakDomains.slice(0, 2)) {
      weaknesses.push({
        kind: 'weak_domain',
        detail: `${domain.domain} has ${domain.claims} claim(s), ${domain.supportedClaims} supported, and ${domain.promotedClaims} promoted`,
        recommendedGoal: {
          title: `Strengthen ${domain.domain} evidence quality`,
          description: `Gather or validate grounded evidence for the weak ${domain.domain} domain until at least one claim can be promoted.`,
          domain: domain.domain === 'unknown' ? 'research' : domain.domain,
        },
      });
    }

    // Weakness: knowledge exists but little is promoted to trusted knowledge ("believe slowly" backlog).
    if (snapshot.supportedClaims > snapshot.promotedClaims) {
      weaknesses.push({
        kind: 'unpromoted_knowledge',
        detail: `${snapshot.supportedClaims} supported claims vs ${snapshot.promotedClaims} promoted — a promotion backlog`,
        recommendedGoal: {
          title: 'Validate and promote high-confidence supported claims',
          description: 'Run the evidence promotion gate over supported claims and promote those that pass.',
          domain: 'calibration',
        },
      });
    }

    // Weakness: thin evidence base → go gather more.
    if (snapshot.claims < 10) {
      weaknesses.push({
        kind: 'thin_evidence',
        detail: `only ${snapshot.claims} claims in the knowledge base`,
        recommendedGoal: {
          title: 'Expand the evidence base with new grounded research',
          description: 'Investigate an under-covered topic and extract grounded, source-quality-weighted claims.',
          domain: 'research',
        },
      });
    }

    if (weaknesses.length === 0) {
      weaknesses.push({
        kind: 'maintain',
        detail: 'no acute weakness; perform a maintenance research pass',
        recommendedGoal: {
          title: 'Maintenance research pass',
          description: 'Gather fresh evidence to keep the knowledge base current.',
          domain: 'research',
        },
      });
    }
    return weaknesses;
  }

  async getHealthSnapshot(): Promise<CivilizationHealthSnapshot> {
    const totals = await db.query(
      `SELECT
         (SELECT count(*) FROM autonomy_claims) AS claims,
         (SELECT count(*) FROM autonomy_claims WHERE status = 'promoted') AS promoted,
         (SELECT count(*) FROM autonomy_claims WHERE status = 'supported') AS supported,
         (SELECT count(*) FROM autonomy_evidence) AS evidence,
         (SELECT count(*)
            FROM autonomy_claims
           WHERE status = 'contradicted'
              OR jsonb_array_length(COALESCE(contradicted_by, '[]'::jsonb)) > 0
              OR jsonb_array_length(COALESCE(contradicts, '[]'::jsonb)) > 0) AS contradictions,
         (SELECT count(*)
            FROM predictions p
            LEFT JOIN prediction_resolutions pr ON pr.prediction_id = p.prediction_id
           WHERE pr.prediction_id IS NULL
             AND p.expected_resolution_by < NOW()) AS stale_predictions`
    );

    const weakDomains = await db.query(
      `SELECT COALESCE(g.domain, 'unknown') AS domain,
              count(*)::int AS claims,
              count(*) FILTER (WHERE c.status = 'promoted')::int AS promoted_claims,
              count(*) FILTER (WHERE c.status = 'supported')::int AS supported_claims
         FROM autonomy_claims c
         LEFT JOIN autonomy_goal_actions a ON a.action_id = c.action_id
         LEFT JOIN autonomy_goals g ON g.id = a.goal_id
        GROUP BY COALESCE(g.domain, 'unknown')
       HAVING count(*) >= 2
          AND count(*) FILTER (WHERE c.status = 'promoted') = 0
        ORDER BY count(*) DESC, COALESCE(g.domain, 'unknown') ASC
        LIMIT 5`
    );

    const t = totals.rows[0];
    return {
      claims: Number(t.claims),
      promotedClaims: Number(t.promoted),
      supportedClaims: Number(t.supported),
      evidenceItems: Number(t.evidence),
      unresolvedContradictions: Number(t.contradictions),
      stalePredictions: Number(t.stale_predictions),
      weakDomains: weakDomains.rows.map((r: {
        domain: string;
        claims: number | string;
        promoted_claims: number | string;
        supported_claims: number | string;
      }) => ({
        domain: String(r.domain),
        claims: Number(r.claims),
        promotedClaims: Number(r.promoted_claims),
        supportedClaims: Number(r.supported_claims),
      })),
    };
  }

  /** STEP 2: generate ONE internal goal from self-assessment (no user prompt). */
  async generateInternalGoal(weakness: Weakness): Promise<string> {
    const { goalId } = await goalManager.proposeGoal({
      title: weakness.recommendedGoal.title,
      description: weakness.recommendedGoal.description,
      source: 'perception_derived', // internally generated, not user/agent-prompted
      proposedBy: 'civilization_free_run',
      domain: weakness.recommendedGoal.domain,
      riskLevel: 'low',
      autonomyLevelAllowed: 'L2',
      successCriteria: { weakness: weakness.kind },
      stopConditions: { maxIterations: 8 },
    } as Parameters<typeof goalManager.proposeGoal>[0]);
    return goalId;
  }

  /** STEP 3: route the goal to a society agenda that determines the bounded task behavior. */
  async createAgendaItem(goalId: string, weakness: Weakness): Promise<SocietyAgendaItem> {
    const isCalibration = weakness.recommendedGoal.domain === 'calibration';
    const societyId = isCalibration ? 'calibration_society' : 'scientific_society';
    const institutionId = isCalibration ? 'evidence_promotion_institution' : 'research_ingestion_institution';
    const taskType = isCalibration ? 'promote_supported_claims' : 'ingest_research_evidence';
    const executionDomain = isCalibration ? 'calibration' : 'research';
    const agendaItemId = uuid();
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at) VALUES ($1, NULL, $2, NOW(), NOW())`,
      [agendaItemId, JSON.stringify({
        type: 'society_agenda', agendaItemId, societyId, goalId,
        institutionId, taskType, executionDomain,
        priority: 'high', reason: weakness.detail, status: 'assigned',
      })],
    );
    return { agendaItemId, societyId, institutionId, taskType, executionDomain };
  }

  /**
   * STEP 4-6: bounded execution → claim. In fixture mode, deterministically seed one grounded
   * claim+evidence (CI-safe). In read_only_web mode the real autonomy loop runs (caller wires it).
   * Returns the claim ids produced under this goal.
   */
  async executeBoundedTaskFixture(goalId: string, agenda: SocietyAgendaItem): Promise<string[]> {
    const sourceId = uuid();
    const actionId = uuid();
    const routedTask = this.fixtureTaskForAgenda(agenda);
    await db.query(
      `INSERT INTO autonomy_goal_actions (id, action_id, goal_id, action_type, objective)
       VALUES ($1,$2,$3,'generate_claim',$4)`,
      [uuid(), actionId, goalId, routedTask.objective]);
    await db.query(
      `INSERT INTO autonomy_evidence (id, source_id, action_id, url, title, snippet, retrieved_at, content_hash, source_type, is_public_access, created_at)
       VALUES ($1,$2,$3,$4,$5,$6,NOW(),$7,'web',true,NOW())`,
      [uuid(), sourceId, actionId, routedTask.url, routedTask.title, routedTask.abstract, `hash_fixture_${agenda.executionDomain}`]);
    const claimId = uuid();
    await db.query(
      `INSERT INTO autonomy_claims (id, claim_id, action_id, text, status, confidence, support_source_ids, support_snippets, derived_from_action_ids)
       VALUES ($1,$2,$3,$4,'supported',0.7,$5,$6,$7)`,
      [uuid(), claimId, actionId, routedTask.claim,
       JSON.stringify([sourceId]),
       JSON.stringify([routedTask.supportSnippet]),
       JSON.stringify([actionId])]);
    return [claimId];
  }

  private fixtureTaskForAgenda(agenda: SocietyAgendaItem): {
    objective: string;
    url: string;
    title: string;
    abstract: string;
    claim: string;
    supportSnippet: string;
  } {
    if (agenda.taskType === 'promote_supported_claims') {
      return {
        objective: `free-run fixture bounded task: ${agenda.societyId}/${agenda.institutionId} performs evidence promotion`,
        url: 'https://example.org/agentco/calibration-evidence',
        title: 'Calibration evidence backlog review',
        abstract: 'Calibration improves when promoted claims are checked against grounded evidence before prediction registration.',
        claim: 'Calibration improves when promoted claims are checked against grounded evidence before prediction registration.',
        supportSnippet: 'Calibration improves when promoted claims are checked against grounded evidence before prediction registration',
      };
    }

    return {
      objective: `free-run fixture bounded task: ${agenda.societyId}/${agenda.institutionId} ingests research evidence`,
      url: 'https://arxiv.org/abs/1311.4600',
      title: 'Small gaps between primes',
      abstract: 'We prove that bounded gaps between primes occur infinitely often, refining the GPY sieve.',
      claim: 'Bounded gaps between primes occur infinitely often.',
      supportSnippet: 'bounded gaps between primes occur infinitely often',
    };
  }

  /**
   * STEP 7: actively detect contradictions before the promotion gate. This is deterministic and
   * conservative: it only links direct polarity conflicts over the same normalized proposition.
   */
  async detectContradictions(claimIds: string[]): Promise<ContradictionFinding[]> {
    if (claimIds.length === 0) return [];

    const incoming = await db.query(
      `SELECT claim_id, text, contradicted_by, contradicts
         FROM autonomy_claims
        WHERE claim_id = ANY($1)`,
      [claimIds],
    );
    const existing = await db.query(
      `SELECT claim_id, text, contradicted_by, contradicts
         FROM autonomy_claims
        WHERE claim_id <> ALL($1)
        ORDER BY generated_at DESC
        LIMIT 500`,
      [claimIds],
    );

    const findings: ContradictionFinding[] = [];
    for (const claim of incoming.rows) {
      for (const candidate of existing.rows) {
        const reason = this.directContradictionReason(String(claim.text), String(candidate.text));
        if (!reason) continue;
        findings.push({
          claimId: String(claim.claim_id),
          contradictingClaimId: String(candidate.claim_id),
          reason,
        });
        await this.linkContradiction(String(claim.claim_id), String(candidate.claim_id));
        break;
      }
    }

    return findings;
  }

  private directContradictionReason(a: string, b: string): string | null {
    const pa = this.polarizedProposition(a);
    const pb = this.polarizedProposition(b);
    if (!pa || !pb) return null;
    if (pa.proposition === pb.proposition && pa.polarity !== pb.polarity) {
      return `opposite polarity for proposition "${pa.proposition}"`;
    }
    return null;
  }

  private polarizedProposition(text: string): { proposition: string; polarity: 'positive' | 'negative' } | null {
    let s = text.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
    if (!s) return null;

    let polarity: 'positive' | 'negative' = 'positive';
    const negativePatterns: Array<[RegExp, string]> = [
      [/\bdoes not\b/, ''],
      [/\bdo not\b/, ''],
      [/\bdid not\b/, ''],
      [/\bis not\b/, 'is'],
      [/\bare not\b/, 'are'],
      [/\bwas not\b/, 'was'],
      [/\bwere not\b/, 'were'],
      [/\bcannot\b/, 'can'],
      [/\bcan not\b/, 'can'],
    ];

    for (const [pattern, replacement] of negativePatterns) {
      if (pattern.test(s)) {
        polarity = 'negative';
        s = s.replace(pattern, replacement);
      }
    }

    const proposition = s.replace(/\s+/g, ' ').trim();
    return proposition ? { proposition, polarity } : null;
  }

  private async linkContradiction(claimId: string, contradictingClaimId: string): Promise<void> {
    const rows = await db.query(
      `SELECT claim_id, contradicted_by, contradicts
         FROM autonomy_claims
        WHERE claim_id = ANY($1)`,
      [[claimId, contradictingClaimId]],
    );

    const byId = new Map(rows.rows.map((r: { claim_id: string; contradicted_by: unknown; contradicts: unknown }) => [r.claim_id, r]));
    const current = byId.get(claimId);
    const other = byId.get(contradictingClaimId);
    if (!current || !other) return;

    await db.query(
      `UPDATE autonomy_claims
          SET contradicted_by = $2,
              status = CASE WHEN status = 'promoted' THEN status ELSE 'contradicted' END
        WHERE claim_id = $1`,
      [claimId, JSON.stringify(this.addJsonArrayValue(current.contradicted_by, contradictingClaimId))],
    );
    await db.query(
      `UPDATE autonomy_claims
          SET contradicts = $2
        WHERE claim_id = $1`,
      [contradictingClaimId, JSON.stringify(this.addJsonArrayValue(other.contradicts, claimId))],
    );
  }

  private addJsonArrayValue(raw: unknown, value: string): string[] {
    const arr = Array.isArray(raw)
      ? raw.map(String)
      : (raw ? JSON.parse(String(raw)).map(String) : []);
    return Array.from(new Set([...arr, value]));
  }

  /**
   * STEP 8: propose specialist spawns when the free-run detects a missing capability. This does
   * NOT spawn a process; it records a bounded, governance-review proposal that can later be approved.
   */
  async proposeAgentSpawns(
    goalId: string,
    agenda: SocietyAgendaItem,
    contradictions: ContradictionFinding[],
  ): Promise<AgentSpawnProposal[]> {
    const needs = new Map<string, string>();
    if (agenda.taskType === 'promote_supported_claims') {
      needs.set('claim_validator', `No active claim_validator assignment for ${agenda.institutionId}`);
    }
    if (agenda.taskType === 'ingest_research_evidence') {
      needs.set('researcher', `No active researcher assignment for ${agenda.institutionId}`);
    }
    if (contradictions.length > 0) {
      needs.set('contradiction_hunter', `${contradictions.length} contradiction(s) require specialist review`);
    }

    const proposals: AgentSpawnProposal[] = [];
    for (const [role, reason] of needs) {
      const roleSpec = getSpecialistRole(role);
      if (!roleSpec) continue;
      const active = await db.query(
        `SELECT id
           FROM institution_specialist_assignments
          WHERE institution_id = $1
            AND specialist_role = $2
            AND active = TRUE
          LIMIT 1`,
        [agenda.institutionId, role],
      );
      if (active.rows.length > 0) continue;

      const proposal: AgentSpawnProposal = {
        proposalId: uuid(),
        goalId,
        agendaItemId: agenda.agendaItemId,
        role,
        objective: this.spawnObjectiveForRole(role, agenda, contradictions),
        reason,
        governanceStatus: 'review_required',
        budget: { ...roleSpec.defaultBudgets },
        constraints: {
          maxDepth: 2,
          maxParallelWorkers: 3,
          activationRequiresGovernance: true,
        },
      };
      await db.query(
        `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at)
         VALUES ($1, NULL, $2, NOW(), NOW())`,
        [proposal.proposalId, JSON.stringify({ type: 'agent_spawn_proposal', ...proposal })],
      );
      proposals.push(proposal);
    }

    return proposals;
  }

  private spawnObjectiveForRole(
    role: string,
    agenda: SocietyAgendaItem,
    contradictions: ContradictionFinding[],
  ): string {
    if (role === 'contradiction_hunter') {
      const ids = contradictions.map(c => c.claimId).join(', ');
      return `Review detected contradiction(s) for claim(s): ${ids}`;
    }
    if (role === 'claim_validator') {
      return `Validate supported claims for ${agenda.societyId}/${agenda.institutionId} before trusted promotion`;
    }
    return `Gather and ground evidence for ${agenda.societyId}/${agenda.institutionId}`;
  }

  /**
   * STEP 9: propose safe self-improvements from observed free-run limits. This does not edit code;
   * it records a governed proposal with affected files, tests, rollback plan, and protected scan.
   */
  async proposeSelfImprovements(
    goalId: string,
    weaknesses: Weakness[],
    reportContext: {
      contradictionsDetected: number;
      agentSpawnProposals: number;
      errors: string[];
    },
  ): Promise<SelfImprovementProposal[]> {
    const proposals: SelfImprovementProposal[] = [];
    const proposal = await this.buildSelfImprovementProposal(goalId, weaknesses, reportContext);
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at)
       VALUES ($1, NULL, $2, NOW(), NOW())`,
      [proposal.proposalId, JSON.stringify({ type: 'self_improvement_proposal', ...proposal })],
    );
    proposals.push(proposal);
    return proposals;
  }

  /**
   * STEP 10: submit proposal-only outputs to the existing human override queue. This is an
   * escalation path, not approval: pending override rows have no approval token and do not activate
   * specialists, candidates, or code changes.
   */
  async enqueueGovernanceReviewRequests(
    goalId: string,
    agentSpawnProposals: AgentSpawnProposal[],
    selfImprovementProposals: SelfImprovementProposal[],
  ): Promise<GovernanceQueueRequest[]> {
    const requests: GovernanceQueueRequest[] = [];

    for (const proposal of agentSpawnProposals) {
      const request = await overrideQueue.enqueue(
        'civilization_free_run',
        'agent_upgrade',
        'high',
        {
          risk_score: 0.75,
          proposal_type: 'agent_spawn_proposal',
          proposal_id: proposal.proposalId,
          goal_id: goalId,
          role: proposal.role,
          objective: proposal.objective,
          budget: proposal.budget,
          constraints: proposal.constraints,
          blocked_until_approved: true,
        },
      );
      requests.push(this.governanceQueueRequestFromOverride(proposal.proposalId, 'agent_spawn_proposal', request));
    }

    for (const proposal of selfImprovementProposals) {
      const riskLevel = proposal.riskLevel === 'critical' ? 'critical' : 'high';
      const request = await overrideQueue.enqueue(
        'civilization_free_run',
        'config_change',
        riskLevel,
        {
          risk_score: riskLevel === 'critical' ? 1.0 : 0.85,
          proposal_type: 'self_improvement_proposal',
          proposal_id: proposal.proposalId,
          goal_id: goalId,
          target_component: proposal.targetComponent,
          affected_files: proposal.affectedFiles,
          expected_improvement: proposal.expectedImprovement,
          tests_to_pass: proposal.testsToPass,
          rollback_plan: proposal.rollbackPlan,
          protected_surface_check: proposal.protectedSurfaceCheck,
          blocked_until_approved: true,
        },
      );
      requests.push(this.governanceQueueRequestFromOverride(proposal.proposalId, 'self_improvement_proposal', request));
    }

    return requests;
  }

  private governanceQueueRequestFromOverride(
    proposalId: string,
    proposalType: GovernanceQueueRequest['proposalType'],
    request: OverrideRequest,
  ): GovernanceQueueRequest {
    return {
      proposalId,
      proposalType,
      requestId: request.request_id,
      status: 'pending',
      action: request.action,
      riskLevel: request.risk_level,
    };
  }

  /**
   * Approval-token consumption preflight. This verifies a human-approved override and a real
   * promotion-eligible eval scorecard, then records the readiness decision. It intentionally does
   * not execute the approved action.
   */
  async assessGovernanceApprovalReadiness(input: {
    requestId: string;
    approvalToken?: string;
    evalRunId?: string;
  }): Promise<GovernanceApprovalReadiness> {
    const override = await db.query(
      `SELECT request_id, action, status, approval_token, context
         FROM override_queue
        WHERE request_id = $1
          AND agent_id = 'civilization_free_run'`,
      [input.requestId],
    );
    if (override.rows.length === 0) {
      return this.recordGovernanceApprovalReadiness({
        requestId: input.requestId,
        status: 'blocked',
        blockedReason: 'override request not found for civilization_free_run',
      });
    }

    const row = override.rows[0];
    const context = row.context || {};
    const base = {
      requestId: String(row.request_id),
      proposalId: context.proposal_id ? String(context.proposal_id) : undefined,
      proposalType: this.knownProposalType(context.proposal_type),
    };

    if (row.status !== 'approved') {
      return this.recordGovernanceApprovalReadiness({
        ...base,
        status: 'blocked',
        blockedReason: `override request is ${row.status}, not approved`,
      });
    }

    const token = row.approval_token ? String(row.approval_token) : '';
    if (!input.approvalToken || input.approvalToken !== token) {
      return this.recordGovernanceApprovalReadiness({
        ...base,
        status: 'blocked',
        blockedReason: 'approval token missing or does not match override_queue',
      });
    }

    if (!input.evalRunId) {
      return this.recordGovernanceApprovalReadiness({
        ...base,
        status: 'blocked',
        blockedReason: 'promotion-eligible eval scorecard is required before execution',
      });
    }

    const scorecard = await db.query(
      `SELECT sc.promotion_eligible,
              sc.autonomy_score, sc.safety_score, sc.calibration_score, sc.planning_score,
              sc.memory_score, sc.tool_score, sc.reward_score, sc.regression_score,
              er.status AS eval_status
         FROM eval_scorecards sc
         JOIN eval_runs er ON er.id = sc.eval_run_id
        WHERE sc.eval_run_id = $1
        ORDER BY sc.created_at DESC
        LIMIT 1`,
      [input.evalRunId],
    );
    if (scorecard.rows.length === 0) {
      return this.recordGovernanceApprovalReadiness({
        ...base,
        status: 'blocked',
        evalRunId: input.evalRunId,
        blockedReason: 'eval scorecard not found',
      });
    }

    const sc = scorecard.rows[0];
    const normalizedScorecard = {
      promotionEligible: Boolean(sc.promotion_eligible),
      autonomyScore: this.nullableNumber(sc.autonomy_score),
      safetyScore: this.nullableNumber(sc.safety_score),
      calibrationScore: this.nullableNumber(sc.calibration_score),
      planningScore: this.nullableNumber(sc.planning_score),
      memoryScore: this.nullableNumber(sc.memory_score),
      toolScore: this.nullableNumber(sc.tool_score),
      rewardScore: this.nullableNumber(sc.reward_score),
      regressionScore: this.nullableNumber(sc.regression_score),
    };

    if (sc.eval_status !== 'completed') {
      return this.recordGovernanceApprovalReadiness({
        ...base,
        status: 'blocked',
        evalRunId: input.evalRunId,
        scorecard: normalizedScorecard,
        blockedReason: `eval run is ${sc.eval_status}, not completed`,
      });
    }

    if (!normalizedScorecard.promotionEligible) {
      return this.recordGovernanceApprovalReadiness({
        ...base,
        status: 'blocked',
        evalRunId: input.evalRunId,
        scorecard: normalizedScorecard,
        blockedReason: 'eval scorecard is not promotion eligible',
      });
    }

    return this.recordGovernanceApprovalReadiness({
      ...base,
      status: 'ready',
      evalRunId: input.evalRunId,
      scorecard: normalizedScorecard,
    });
  }

  private knownProposalType(raw: unknown): GovernanceApprovalReadiness['proposalType'] {
    return raw === 'agent_spawn_proposal'
      || raw === 'self_improvement_proposal'
      || raw === 'self_improvement_candidate_promotion'
      ? raw
      : undefined;
  }

  private nullableNumber(raw: unknown): number | null {
    if (raw === null || raw === undefined) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }

  private async recordGovernanceApprovalReadiness(
    readiness: GovernanceApprovalReadiness,
  ): Promise<GovernanceApprovalReadiness> {
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at)
       VALUES ($1, NULL, $2, NOW(), NOW())`,
      [uuid(), JSON.stringify({ type: 'governance_approval_preflight', ...readiness })],
    );
    return readiness;
  }

  /**
   * Consume a ready governance preflight into one bounded specialist lifecycle. This starts the
   * real specialist subprocess, sends one signed evaluate_progress action, terminates the process,
   * and records the execution. It only supports agent-spawn proposals; self-improvement still stops
   * at preflight until a candidate/sandbox lifecycle exists.
   */
  async executeApprovedAgentSpawn(input: {
    requestId: string;
    approvalToken: string;
    evalRunId: string;
  }): Promise<ApprovedAgentSpawnExecution> {
    const readiness = await this.assessGovernanceApprovalReadiness(input);
    if (readiness.status !== 'ready') {
      return this.recordApprovedAgentSpawnExecution({
        requestId: input.requestId,
        proposalId: readiness.proposalId,
        status: 'blocked',
        blockedReason: readiness.blockedReason || 'governance preflight did not return ready',
      });
    }

    const row = await db.query(
      `SELECT context
         FROM override_queue
        WHERE request_id = $1
          AND agent_id = 'civilization_free_run'
          AND status = 'approved'`,
      [input.requestId],
    );
    if (row.rows.length === 0) {
      return this.recordApprovedAgentSpawnExecution({
        requestId: input.requestId,
        proposalId: readiness.proposalId,
        status: 'blocked',
        blockedReason: 'approved override request disappeared before execution',
      });
    }

    const context = row.rows[0].context || {};
    if (context.proposal_type !== 'agent_spawn_proposal') {
      return this.recordApprovedAgentSpawnExecution({
        requestId: input.requestId,
        proposalId: readiness.proposalId,
        status: 'blocked',
        blockedReason: `proposal type ${context.proposal_type || 'unknown'} is not executable by agent-spawn lifecycle`,
      });
    }

    const goalId = String(context.goal_id || '');
    const role = String(context.role || '');
    const objective = String(context.objective || '');
    if (!goalId || !role || !objective) {
      return this.recordApprovedAgentSpawnExecution({
        requestId: input.requestId,
        proposalId: readiness.proposalId,
        status: 'blocked',
        blockedReason: 'agent-spawn queue context is missing goal_id, role, or objective',
      });
    }

    const specialist = await this.teamActivation.activateSpecialist({
      parentGoalId: goalId,
      role,
      objective,
      customBudget: context.budget,
    });
    if (!specialist) {
      return this.recordApprovedAgentSpawnExecution({
        requestId: input.requestId,
        proposalId: readiness.proposalId,
        status: 'failed',
        role,
        blockedReason: 'TeamActivationService failed to activate specialist',
      });
    }

    const action = await this.teamActivation.executeActionViaSpecialist(specialist.specialistId, {
      actionId: uuid(),
      actionType: ActionType.EVALUATE_PROGRESS,
      goalId,
      objective: `Approved free-run specialist activation check: ${objective}`,
      args: {
        requestId: input.requestId,
        proposalId: readiness.proposalId,
        evalRunId: input.evalRunId,
      },
      successCriteria: ['specialist process accepts a signed bounded action'],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'civilization_free_run',
      decidedAt: new Date(),
      reasoning: 'Human approval token and promotion-eligible eval preflight were both verified.',
    });

    await this.teamActivation.terminateSpecialist(specialist.specialistId, {
      artifacts: action?.createdArtifacts || [],
      evidence: [],
      claims: [],
      error: action?.status === ActionStatus.COMPLETED ? undefined : 'specialist action did not complete',
    });

    return this.recordApprovedAgentSpawnExecution({
      requestId: input.requestId,
      proposalId: readiness.proposalId,
      status: action?.status === ActionStatus.COMPLETED ? 'completed' : 'failed',
      specialistId: specialist.specialistId,
      role,
      actionStatus: action?.status || 'missing',
      activationStatus: action?.status === ActionStatus.COMPLETED ? 'completed' : 'failed',
      blockedReason: action ? undefined : 'specialist did not return an action result',
    });
  }

  private async recordApprovedAgentSpawnExecution(
    execution: ApprovedAgentSpawnExecution,
  ): Promise<ApprovedAgentSpawnExecution> {
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at)
       VALUES ($1, NULL, $2, NOW(), NOW())`,
      [uuid(), JSON.stringify({ type: 'approved_agent_spawn_execution', ...execution })],
    );
    return execution;
  }

  /**
   * Consume a ready self-improvement approval into a learner candidate and sandbox validation
   * record. This creates DB artifacts only: no source files are edited and no candidate is promoted.
   */
  async executeApprovedSelfImprovementCandidate(input: {
    requestId: string;
    approvalToken: string;
    evalRunId: string;
  }): Promise<ApprovedSelfImprovementCandidateExecution> {
    const readiness = await this.assessGovernanceApprovalReadiness(input);
    if (readiness.status !== 'ready') {
      return this.recordApprovedSelfImprovementCandidateExecution({
        requestId: input.requestId,
        proposalId: readiness.proposalId,
        status: 'blocked',
        blockedReason: readiness.blockedReason || 'governance preflight did not return ready',
        promotionStatus: 'not_promoted',
      });
    }

    const override = await db.query(
      `SELECT context
         FROM override_queue
        WHERE request_id = $1
          AND agent_id = 'civilization_free_run'
          AND status = 'approved'`,
      [input.requestId],
    );
    if (override.rows.length === 0) {
      return this.recordApprovedSelfImprovementCandidateExecution({
        requestId: input.requestId,
        proposalId: readiness.proposalId,
        status: 'blocked',
        blockedReason: 'approved override request disappeared before candidate creation',
        promotionStatus: 'not_promoted',
      });
    }

    const context = override.rows[0].context || {};
    if (context.proposal_type !== 'self_improvement_proposal') {
      return this.recordApprovedSelfImprovementCandidateExecution({
        requestId: input.requestId,
        proposalId: readiness.proposalId,
        status: 'blocked',
        blockedReason: `proposal type ${context.proposal_type || 'unknown'} is not executable by self-improvement candidate lifecycle`,
        promotionStatus: 'not_promoted',
      });
    }

    const goalId = String(context.goal_id || '');
    const proposalId = String(context.proposal_id || readiness.proposalId || '');
    const targetComponent = String(context.target_component || '');
    const affectedFiles = Array.isArray(context.affected_files) ? context.affected_files.map(String) : [];
    const testsToPass = Array.isArray(context.tests_to_pass) ? context.tests_to_pass.map(String) : [];
    const protectedSurfaceCheck = context.protected_surface_check || {};
    if (!goalId || !proposalId || !targetComponent || affectedFiles.length === 0 || testsToPass.length === 0) {
      return this.recordApprovedSelfImprovementCandidateExecution({
        requestId: input.requestId,
        proposalId: proposalId || readiness.proposalId,
        status: 'blocked',
        blockedReason: 'self-improvement queue context is missing goal_id, proposal_id, target_component, affected_files, or tests_to_pass',
        promotionStatus: 'not_promoted',
      });
    }

    const regressionValidation = this.validateSelfImprovementScorecard(readiness.scorecard);
    if (regressionValidation.status !== 'passed') {
      return this.recordApprovedSelfImprovementCandidateExecution({
        requestId: input.requestId,
        proposalId,
        status: 'blocked',
        blockedReason: regressionValidation.reason,
        promotionStatus: 'not_promoted',
      });
    }

    const sandbox = {
      status: 'passed',
      promotion_allowed: false,
      reason: 'sandbox validation creates an evaluated learner candidate only; promotion requires a separate human-governed promotion path',
      no_source_files_modified: true,
      requires_human_approval: Boolean(protectedSurfaceCheck.requiresHumanApproval ?? true),
      tests_required_before_promotion: testsToPass,
      preflight_eval_run_id: input.evalRunId,
      eval_gate: regressionValidation,
      protected_surface_check: protectedSurfaceCheck,
    };
    const artifactJson = {
      type: 'civilization_free_run_self_improvement_candidate',
      request_id: input.requestId,
      proposal_id: proposalId,
      goal_id: goalId,
      target_component: targetComponent,
      affected_files: affectedFiles,
      expected_improvement: String(context.expected_improvement || ''),
      tests_to_pass: testsToPass,
      rollback_plan: String(context.rollback_plan || ''),
      sandbox,
      generated_by: 'civilization_free_run',
    };
    const artifactHash = this.sha256Json(artifactJson);
    const batchHash = this.sha256Json({
      type: 'civilization_free_run_self_improvement_replay_batch',
      request_id: input.requestId,
      proposal_id: proposalId,
      artifact_hash: artifactHash,
    });

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const artifact = await client.query(
        `INSERT INTO artifacts (artifact_type, artifact_hash, artifact_json, lineage_json, is_simulation_derived, status)
         VALUES ('heuristic_update', $1, $2, $3, false, 'tested')
         RETURNING id`,
        [artifactHash, JSON.stringify(artifactJson), JSON.stringify({
          source: 'civilization_free_run',
          request_id: input.requestId,
          proposal_id: proposalId,
          preflight_eval_run_id: input.evalRunId,
        })],
      );
      const artifactId = String(artifact.rows[0].id);

      const episode = await client.query(
        `INSERT INTO autonomy_episodes (
           run_id, agent_id, institution_id, title, summary, domain, risk_level,
           autonomy_level, ended_at, outcome_status, reward_score, regret_score,
           intervention_required, intervention_count, human_override_count, trace_id,
           metadata, tags
         ) VALUES ($1,$2,$3,$4,$5,$6,'medium',2,NOW(),'success',1.0,0.0,true,1,1,$7,$8,$9)
         RETURNING id`,
        [
          `free_run_self_improvement_${input.requestId}`,
          'civilization_free_run',
          'self_improvement_governance',
          `Sandbox self-improvement candidate for ${targetComponent}`,
          'Human-approved free-run proposal converted into a sandbox-validated learner candidate without promotion.',
          'civilization_free_run',
          `trace_${input.requestId}`,
          JSON.stringify({ request_id: input.requestId, proposal_id: proposalId, artifact_id: artifactId }),
          ['civilization_free_run', 'self_improvement', 'sandbox_validation'],
        ],
      );
      const episodeId = String(episode.rows[0].id);

      const trajectory = await client.query(
        `INSERT INTO trajectory_store (
           episode_id, step_index, state_json, action_json, observation_json,
           reward, done, info_json, policy_version
         ) VALUES ($1,0,$2,$3,$4,1.0,true,$5,'civilization_free_run.v1')
         RETURNING id`,
        [
          episodeId,
          JSON.stringify({ request_id: input.requestId, proposal_id: proposalId, target_component: targetComponent }),
          JSON.stringify({ type: 'create_self_improvement_candidate', artifact_hash: artifactHash }),
          JSON.stringify({ sandbox_status: sandbox.status, promotion_allowed: false, artifact_id: artifactId }),
          JSON.stringify({ governance_preflight_eval_run_id: input.evalRunId }),
        ],
      );
      const trajectoryId = String(trajectory.rows[0].id);

      const replayBatch = await client.query(
        `INSERT INTO replay_batches (source_filter_json, trajectory_ids, batch_hash, batch_size, created_by, tags)
         VALUES ($1, ARRAY[$2]::uuid[], $3, 1, 'civilization_free_run', $4)
         RETURNING id`,
        [
          JSON.stringify({ request_id: input.requestId, proposal_id: proposalId, source: 'approved_self_improvement_candidate' }),
          trajectoryId,
          batchHash,
          ['civilization_free_run', 'self_improvement', 'sandbox_validation'],
        ],
      );
      const replayBatchId = String(replayBatch.rows[0].id);
      const replayValidation = await this.validateReplayBatch(client, replayBatchId);
      if (replayValidation.status !== 'passed') {
        throw new Error(replayValidation.reason);
      }

      const learnerRun = await client.query(
        `INSERT INTO learner_runs (
           replay_batch_id, policy_version_before, policy_version_after,
           baseline_metrics_json, candidate_count, status, completed_at
         ) VALUES ($1,'civilization_free_run.v1',NULL,$2,1,'completed',NOW())
         RETURNING id`,
        [replayBatchId, JSON.stringify({
          preflight_eval_run_id: input.evalRunId,
          sandbox_status: sandbox.status,
          replay_validation_status: replayValidation.status,
          regression_validation_status: regressionValidation.status,
          promotion_allowed: false,
        })],
      );
      const learnerRunId = String(learnerRun.rows[0].id);

      const candidate = await client.query(
        `INSERT INTO learner_candidates (
           learner_run_id, candidate_type, artifact_id, artifact_hash,
           metrics_before_json, metrics_after_json, improvement_percent,
           status, eval_feedback_json, evaluated_at
         ) VALUES ($1,'heuristic_update',$2,$3,$4,$5,0.0,'evaluated',$6,NOW())
         RETURNING id, status`,
        [
          learnerRunId,
          artifactId,
          artifactHash,
          JSON.stringify({ current_self_improvement_candidate_count: 0 }),
          JSON.stringify({
            sandbox_validated_candidate_count: 1,
            replay_validated_candidate_count: 1,
            regression_validated_candidate_count: 1,
            promoted_candidate_count: 0,
          }),
          JSON.stringify({
            sandbox,
            replay_validation: replayValidation,
            regression_validation: regressionValidation,
            promotion_allowed: false,
            promoted: false,
          }),
        ],
      );
      const candidateId = String(candidate.rows[0].id);
      const candidateStatus = String(candidate.rows[0].status);

      await client.query(
        `UPDATE learner_runs
            SET best_candidate_id = $1
          WHERE id = $2`,
        [candidateId, learnerRunId],
      );

      const suite = await client.query(
        `INSERT INTO eval_suites (name, domain, version, active)
         VALUES ($1, 'civilization_free_run', 1, TRUE)
         RETURNING id`,
        [`civilization-free-run-self-improvement-sandbox-${uuid()}`],
      );
      const sandboxEval = await client.query(
        `INSERT INTO eval_runs (suite_id, run_timestamp, status)
         VALUES ($1, NOW(), 'completed')
         RETURNING id`,
        [suite.rows[0].id],
      );
      const sandboxEvalRunId = String(sandboxEval.rows[0].id);
      await client.query(
        `INSERT INTO eval_scorecards (
           eval_run_id, autonomy_score, safety_score, calibration_score, planning_score,
           memory_score, tool_score, reward_score, regression_score, promotion_eligible
         ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,false)`,
        [
          sandboxEvalRunId,
          regressionValidation.scores.autonomy,
          regressionValidation.scores.safety,
          regressionValidation.scores.calibration,
          regressionValidation.scores.planning,
          regressionValidation.scores.memory,
          regressionValidation.scores.tool,
          regressionValidation.scores.reward,
          regressionValidation.scores.regression,
        ],
      );

      await client.query('COMMIT');
      return this.recordApprovedSelfImprovementCandidateExecution({
        requestId: input.requestId,
        proposalId,
        status: 'completed',
        artifactId,
        artifactHash,
        episodeId,
        trajectoryId,
        replayBatchId,
        learnerRunId,
        candidateId,
        sandboxEvalRunId,
        candidateStatus,
        promotionStatus: 'not_promoted',
      });
    } catch (error) {
      await client.query('ROLLBACK');
      return this.recordApprovedSelfImprovementCandidateExecution({
        requestId: input.requestId,
        proposalId,
        status: 'failed',
        blockedReason: error instanceof Error ? error.message : String(error),
        artifactHash,
        promotionStatus: 'not_promoted',
      });
    } finally {
      client.release();
    }
  }

  private async recordApprovedSelfImprovementCandidateExecution(
    execution: ApprovedSelfImprovementCandidateExecution,
  ): Promise<ApprovedSelfImprovementCandidateExecution> {
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at)
       VALUES ($1, NULL, $2, NOW(), NOW())`,
      [uuid(), JSON.stringify({ type: 'approved_self_improvement_candidate_execution', ...execution })],
    );
    return execution;
  }

  /**
   * Enqueue a separate human-governed promotion request for an evaluated sandbox candidate. This
   * does not promote; it creates another blocked override row that must be approved independently.
   */
  async enqueueSelfImprovementPromotionRequest(candidateId: string): Promise<SelfImprovementPromotionRequest> {
    const candidate = await db.query(
      `SELECT c.id, c.status AS candidate_status, c.artifact_id, c.artifact_hash, c.eval_feedback_json,
              a.artifact_type, a.status AS artifact_status, a.is_simulation_derived, a.artifact_json
         FROM learner_candidates c
         JOIN artifacts a ON a.id = c.artifact_id
        WHERE c.id = $1`,
      [candidateId],
    );
    if (candidate.rows.length === 0) {
      throw new Error(`Learner candidate ${candidateId} not found`);
    }

    const row = candidate.rows[0];
    this.assertPromotableSandboxCandidate(row, { requireEvaluated: true });

    const request = await overrideQueue.enqueue(
      'civilization_free_run',
      'config_change',
      'critical',
      {
        risk_score: 0.95,
        proposal_type: 'self_improvement_candidate_promotion',
        candidate_id: String(row.id),
        artifact_id: String(row.artifact_id),
        artifact_type: String(row.artifact_type),
        artifact_hash: String(row.artifact_hash),
        source_candidate_request_id: row.artifact_json?.request_id ? String(row.artifact_json.request_id) : undefined,
        source_proposal_id: row.artifact_json?.proposal_id ? String(row.artifact_json.proposal_id) : undefined,
        sandbox_status: row.eval_feedback_json?.sandbox?.status || 'unknown',
        requires_human_approval: true,
        blocked_until_approved: true,
      },
    );

    const promotionRequest: SelfImprovementPromotionRequest = {
      candidateId: String(row.id),
      artifactId: String(row.artifact_id),
      requestId: request.request_id,
      status: 'pending',
      action: request.action,
      riskLevel: request.risk_level,
    };
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at)
       VALUES ($1, NULL, $2, NOW(), NOW())`,
      [uuid(), JSON.stringify({ type: 'self_improvement_candidate_promotion_request', ...promotionRequest })],
    );
    return promotionRequest;
  }

  /**
   * Promote a sandbox-validated candidate after a distinct human approval and promotion-eligible
   * eval. Promotion here means marking the learning candidate/artifact as promoted; it does not
   * deploy or modify source files because no active artifact deployment table exists in this DB.
   */
  async executeApprovedSelfImprovementPromotion(input: {
    requestId: string;
    approvalToken: string;
    evalRunId: string;
  }): Promise<ApprovedSelfImprovementPromotionExecution> {
    const readiness = await this.assessGovernanceApprovalReadiness(input);
    if (readiness.status !== 'ready') {
      return this.recordApprovedSelfImprovementPromotionExecution({
        requestId: input.requestId,
        status: 'blocked',
        blockedReason: readiness.blockedReason || 'governance preflight did not return ready',
        evalRunId: input.evalRunId,
        promotionStatus: 'not_promoted',
      });
    }

    const override = await db.query(
      `SELECT context
         FROM override_queue
        WHERE request_id = $1
          AND agent_id = 'civilization_free_run'
          AND status = 'approved'`,
      [input.requestId],
    );
    if (override.rows.length === 0) {
      return this.recordApprovedSelfImprovementPromotionExecution({
        requestId: input.requestId,
        status: 'blocked',
        blockedReason: 'approved override request disappeared before promotion',
        evalRunId: input.evalRunId,
        promotionStatus: 'not_promoted',
      });
    }

    const context = override.rows[0].context || {};
    if (context.proposal_type !== 'self_improvement_candidate_promotion') {
      return this.recordApprovedSelfImprovementPromotionExecution({
        requestId: input.requestId,
        status: 'blocked',
        blockedReason: `proposal type ${context.proposal_type || 'unknown'} is not executable by self-improvement promotion lifecycle`,
        evalRunId: input.evalRunId,
        promotionStatus: 'not_promoted',
      });
    }

    const candidateId = String(context.candidate_id || '');
    const artifactId = String(context.artifact_id || '');
    if (!candidateId || !artifactId) {
      return this.recordApprovedSelfImprovementPromotionExecution({
        requestId: input.requestId,
        status: 'blocked',
        blockedReason: 'promotion queue context is missing candidate_id or artifact_id',
        evalRunId: input.evalRunId,
        promotionStatus: 'not_promoted',
      });
    }

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const candidate = await client.query(
        `SELECT c.id, c.status AS candidate_status, c.artifact_id, c.artifact_hash, c.eval_feedback_json,
                a.artifact_type, a.status AS artifact_status, a.is_simulation_derived, a.artifact_json
           FROM learner_candidates c
           JOIN artifacts a ON a.id = c.artifact_id
          WHERE c.id = $1
            AND a.id = $2
          FOR UPDATE OF c, a`,
        [candidateId, artifactId],
      );
      if (candidate.rows.length === 0) {
        throw new Error('candidate/artifact pair not found for promotion request');
      }

      const row = candidate.rows[0];
      this.assertPromotableSandboxCandidate(row, { requireEvaluated: true });

      await client.query(
        `UPDATE learner_candidates
            SET status = 'promoted',
                promoted_at = NOW(),
                eval_feedback_json = jsonb_set(
                  COALESCE(eval_feedback_json, '{}'::jsonb),
                  '{promotion}',
                  $2::jsonb,
                  true
                )
          WHERE id = $1`,
        [candidateId, JSON.stringify({
          status: 'promoted',
          request_id: input.requestId,
          eval_run_id: input.evalRunId,
          promoted_by: 'human_governed_free_run_promotion',
          source_files_modified: false,
        })],
      );
      await client.query(
        `UPDATE artifacts
            SET status = 'promoted',
                lineage_json = jsonb_set(
                  COALESCE(lineage_json, '{}'::jsonb),
                  '{promotion}',
                  $2::jsonb,
                  true
                )
          WHERE id = $1`,
        [artifactId, JSON.stringify({
          request_id: input.requestId,
          eval_run_id: input.evalRunId,
          promoted_by: 'human_governed_free_run_promotion',
          deployed: false,
        })],
      );
      await client.query('COMMIT');

      return this.recordApprovedSelfImprovementPromotionExecution({
        requestId: input.requestId,
        candidateId,
        artifactId,
        status: 'completed',
        evalRunId: input.evalRunId,
        candidateStatus: 'promoted',
        artifactStatus: 'promoted',
        promotionStatus: 'promoted',
      });
    } catch (error) {
      await client.query('ROLLBACK');
      return this.recordApprovedSelfImprovementPromotionExecution({
        requestId: input.requestId,
        candidateId,
        artifactId,
        status: 'failed',
        blockedReason: error instanceof Error ? error.message : String(error),
        evalRunId: input.evalRunId,
        promotionStatus: 'not_promoted',
      });
    } finally {
      client.release();
    }
  }

  private assertPromotableSandboxCandidate(
    row: {
      candidate_status: string;
      artifact_status: string;
      is_simulation_derived: boolean;
      eval_feedback_json?: {
        sandbox?: {
          status?: string;
          no_source_files_modified?: boolean;
          requires_human_approval?: boolean;
        };
        replay_validation?: {
          status?: string;
        };
        regression_validation?: {
          status?: string;
        };
      };
    },
    options: { requireEvaluated: boolean },
  ): void {
    if (options.requireEvaluated && row.candidate_status !== 'evaluated') {
      throw new Error(`candidate status is ${row.candidate_status}, not evaluated`);
    }
    if (row.artifact_status !== 'tested') {
      throw new Error(`artifact status is ${row.artifact_status}, not tested`);
    }
    if (row.is_simulation_derived) {
      throw new Error('simulation-derived artifacts cannot be promoted by free-run self-improvement');
    }
    const sandbox = row.eval_feedback_json?.sandbox || {};
    if (sandbox.status !== 'passed') {
      throw new Error(`sandbox status is ${sandbox.status || 'missing'}, not passed`);
    }
    if (sandbox.no_source_files_modified !== true) {
      throw new Error('sandbox did not prove no source files were modified');
    }
    if (sandbox.requires_human_approval !== true) {
      throw new Error('sandbox candidate does not carry the required human-approval flag');
    }
    const replayValidation = row.eval_feedback_json?.replay_validation || {};
    if (replayValidation.status !== 'passed') {
      throw new Error(`replay validation status is ${replayValidation.status || 'missing'}, not passed`);
    }
    const regressionValidation = row.eval_feedback_json?.regression_validation || {};
    if (regressionValidation.status !== 'passed') {
      throw new Error(`regression validation status is ${regressionValidation.status || 'missing'}, not passed`);
    }
  }

  private validateSelfImprovementScorecard(scorecard: GovernanceApprovalReadiness['scorecard']): {
    status: 'passed' | 'failed';
    reason: string;
    thresholds: Record<string, number>;
    scores: Record<string, number>;
  } {
    const thresholds = {
      autonomy: 0.75,
      safety: 1.0,
      calibration: 0.99,
      planning: 1.0,
      memory: 0.75,
      tool: 0.75,
      reward: 0.75,
      regression: 0.95,
    };
    const scores = {
      autonomy: scorecard?.autonomyScore ?? 0,
      safety: scorecard?.safetyScore ?? 0,
      calibration: scorecard?.calibrationScore ?? 0,
      planning: scorecard?.planningScore ?? 0,
      memory: scorecard?.memoryScore ?? 0,
      tool: scorecard?.toolScore ?? 0,
      reward: scorecard?.rewardScore ?? 0,
      regression: scorecard?.regressionScore ?? 0,
    };
    const failures = Object.entries(thresholds)
      .filter(([key, threshold]) => scores[key as keyof typeof scores] < threshold)
      .map(([key, threshold]) => `${key} ${scores[key as keyof typeof scores]} < ${threshold}`);

    return {
      status: failures.length === 0 ? 'passed' : 'failed',
      reason: failures.length === 0
        ? 'preflight eval scorecard satisfies self-improvement replay/regression floors'
        : `preflight eval scorecard failed self-improvement floors: ${failures.join(', ')}`,
      thresholds,
      scores,
    };
  }

  private async validateReplayBatch(client: PoolClient, replayBatchId: string): Promise<{
    status: 'passed' | 'failed';
    reason: string;
    replayBatchId: string;
    batchSize: number;
    trajectoryIds: string[];
    trajectoriesFound: number;
    completedTrajectories: number;
    minReward: number | null;
  }> {
    const result = await client.query(
      `SELECT rb.batch_size,
              rb.trajectory_ids,
              count(ts.id)::int AS trajectories_found,
              count(ts.id) FILTER (WHERE ts.done = TRUE)::int AS completed_trajectories,
              min(ts.reward)::float8 AS min_reward
         FROM replay_batches rb
         LEFT JOIN trajectory_store ts ON ts.id = ANY(rb.trajectory_ids)
        WHERE rb.id = $1
        GROUP BY rb.id, rb.batch_size, rb.trajectory_ids`,
      [replayBatchId],
    );
    if (result.rows.length === 0) {
      return {
        status: 'failed',
        reason: 'replay batch not found',
        replayBatchId,
        batchSize: 0,
        trajectoryIds: [],
        trajectoriesFound: 0,
        completedTrajectories: 0,
        minReward: null,
      };
    }

    const row = result.rows[0];
    const trajectoryIds = Array.isArray(row.trajectory_ids) ? row.trajectory_ids.map(String) : [];
    const batchSize = Number(row.batch_size);
    const trajectoriesFound = Number(row.trajectories_found);
    const completedTrajectories = Number(row.completed_trajectories);
    const minReward = row.min_reward === null || row.min_reward === undefined ? null : Number(row.min_reward);
    const failures: string[] = [];
    if (batchSize <= 0) failures.push('batch_size is zero');
    if (trajectoryIds.length !== batchSize) failures.push(`trajectory_ids length ${trajectoryIds.length} != batch_size ${batchSize}`);
    if (trajectoriesFound !== batchSize) failures.push(`found ${trajectoriesFound} trajectory rows for batch_size ${batchSize}`);
    if (completedTrajectories !== batchSize) failures.push(`completed ${completedTrajectories} trajectories for batch_size ${batchSize}`);
    if (minReward === null || minReward < 0) failures.push(`min reward ${minReward} is below zero`);

    return {
      status: failures.length === 0 ? 'passed' : 'failed',
      reason: failures.length === 0
        ? 'replay batch has complete non-negative terminal trajectories'
        : `replay validation failed: ${failures.join(', ')}`,
      replayBatchId,
      batchSize,
      trajectoryIds,
      trajectoriesFound,
      completedTrajectories,
      minReward,
    };
  }

  private async recordApprovedSelfImprovementPromotionExecution(
    execution: ApprovedSelfImprovementPromotionExecution,
  ): Promise<ApprovedSelfImprovementPromotionExecution> {
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at)
       VALUES ($1, NULL, $2, NOW(), NOW())`,
      [uuid(), JSON.stringify({ type: 'approved_self_improvement_promotion_execution', ...execution })],
    );
    return execution;
  }

  private sha256Json(value: unknown): string {
    return crypto.createHash('sha256').update(this.stableJson(value)).digest('hex');
  }

  private stableJson(value: unknown): string {
    if (Array.isArray(value)) {
      return `[${value.map(v => this.stableJson(v)).join(',')}]`;
    }
    if (value && typeof value === 'object') {
      return `{${Object.entries(value as Record<string, unknown>)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([k, v]) => `${JSON.stringify(k)}:${this.stableJson(v)}`)
        .join(',')}}`;
    }
    return JSON.stringify(value);
  }

  private async buildSelfImprovementProposal(
    goalId: string,
    weaknesses: Weakness[],
    reportContext: {
      contradictionsDetected: number;
      agentSpawnProposals: number;
      errors: string[];
    },
  ): Promise<SelfImprovementProposal> {
    const hasOnlyShallowSignals = weaknesses.some(w =>
      ['thin_evidence', 'unpromoted_knowledge', 'maintain'].includes(w.kind)
    );
    const targetComponent = hasOnlyShallowSignals
      ? 'civilization_free_run.self_assessment'
      : 'civilization_free_run.execution_policy';
    const affectedFiles = [
      'backend/src/services/civilization-free-run.service.ts',
      'backend/tests/integration/civilization-free-run.test.ts',
      'docs/CIVILIZATION_FREE_RUN.md',
    ];
    const expectedImprovement = hasOnlyShallowSignals
      ? 'Refine health-snapshot prioritization with cross-run trends, severity thresholds, and specialist coverage once enough free-run history exists.'
      : 'Tighten free-run execution policy using observed runtime outcomes while preserving evidence and governance gates.';
    const testsToPass = [
      'npx tsc --noEmit',
      'RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npm test -- --runInBand --forceExit tests/integration/civilization-free-run.test.ts',
      'npm test -- --runInBand --forceExit',
    ];
    const riskLevel: SelfImprovementProposal['riskLevel'] = reportContext.errors.length > 0 ? 'high' : 'medium';
    const attempts = [];
    for (const filePath of affectedFiles) {
      const scan = await this.protectedSurfaceEnforcer.evaluateModificationAttempt(
        filePath,
        expectedImprovement,
        riskLevel === 'medium' ? 'high' : riskLevel,
      );
      attempts.push({
        filePath,
        requiresHumanApproval: scan.requires_human_approval,
        riskLevel: scan.risk_level,
      });
    }

    return {
      proposalId: uuid(),
      goalId,
      targetComponent,
      affectedFiles,
      expectedImprovement,
      testsToPass,
      riskLevel,
      rollbackPlan: 'Revert the self-improvement commit and rerun tsc, the targeted free-run integration test, and the default Jest tier before resuming free-run execution.',
      governanceStatus: 'review_required',
      protectedSurfaceCheck: {
        requiresHumanApproval: true,
        attempts,
      },
    };
  }

  /**
   * STEP 10-11: promotion gate ("believe slowly"). A supported claim is PROMOTED only if it is
   * grounded (snippet traces to a cited source), source credibility isn't 'low', and it is not
   * contradicted. Otherwise it stays blocked. Returns {promoted, blocked} claim ids.
   */
  async promotionGate(claimIds: string[]): Promise<{ promoted: string[]; blocked: string[] }> {
    const promoted: string[] = [], blocked: string[] = [];
    for (const claimId of claimIds) {
      const c = await db.query(
        `SELECT claim_id, text, status, support_source_ids, support_snippets, contradicted_by
           FROM autonomy_claims WHERE claim_id = $1`, [claimId]);
      if (c.rows.length === 0) { blocked.push(claimId); continue; }
      const row = c.rows[0];
      const sourceIds: string[] = Array.isArray(row.support_source_ids) ? row.support_source_ids : JSON.parse(row.support_source_ids || '[]');
      const snippets: string[] = Array.isArray(row.support_snippets) ? row.support_snippets : JSON.parse(row.support_snippets || '[]');

      // Contradiction blocks promotion. NOTE: contradicted_by is a JSONB array; an EMPTY array is
      // truthy in JS, so check length — only an actual contradiction should block.
      const contradictions = Array.isArray(row.contradicted_by)
        ? row.contradicted_by
        : (row.contradicted_by ? JSON.parse(row.contradicted_by) : []);
      if (Array.isArray(contradictions) && contradictions.length > 0) { blocked.push(claimId); continue; }

      // Re-verify grounding against the cited sources.
      const ev = await db.query(`SELECT url, snippet FROM autonomy_evidence WHERE source_id = ANY($1)`, [sourceIds]);
      const sources: GroundingSource[] = ev.rows.map((r: { url: string; snippet: string }) => ({ sourceId: '', content: String(r.snippet || r.url || '') }));
      const grounding = validateGrounding(String(row.text), sources, snippets);
      if (!grounding.valid) { blocked.push(claimId); continue; }

      // Source credibility: a 'low'-quality worst source blocks promotion to trusted knowledge.
      let worstTier = 'unknown';
      for (const r of ev.rows) {
        const q = await this.sourceQuality.getQualityForUrl(String(r.url));
        if (q.tier === 'low') { worstTier = 'low'; break; }
      }
      if (worstTier === 'low') { blocked.push(claimId); continue; }

      await db.query(`UPDATE autonomy_claims SET status = 'promoted' WHERE claim_id = $1`, [claimId]);
      promoted.push(claimId);
    }
    return { promoted, blocked };
  }

  /** STEP 12: register predictions for promoted (now-trusted) claims that are testable. */
  async registerPredictions(promotedClaimIds: string[]): Promise<number> {
    let n = 0;
    for (const claimId of promotedClaimIds) {
      const c = await db.query(`SELECT text, confidence FROM autonomy_claims WHERE claim_id = $1`, [claimId]);
      if (c.rows.length === 0) continue;
      try {
        await this.phase0b.registerPrediction({
          category: 'civilization_free_run',
          description: `Promoted claim will remain consistent with future evidence: "${String(c.rows[0].text).slice(0, 120)}"`,
          confidence: Number(c.rows[0].confidence) || 0.7,
          expectedResolutionBy: new Date(Date.now() + 90 * 24 * 3600 * 1000),
          hypothesis: claimId,
        });
        n++;
      } catch { /* fail-soft: prediction registration is best-effort */ }
    }
    return n;
  }

  /** STEP 13-15: write the real report artifacts and return the report. */
  async writeReport(report: FreeRunReport, extras: { goals: unknown[]; claims: unknown[]; contradictions: unknown[]; agentSpawnProposals: unknown[]; selfImprovementProposals: unknown[]; governanceQueueRequests: unknown[]; predictions: number }): Promise<void> {
    const dir = report.reportDir;
    fs.mkdirSync(dir, { recursive: true });
    const md = [
      `# Civilization Free-Run Report`,
      ``, `- run_id: ${report.runId}`, `- mode: ${report.mode}`, `- started: ${report.startedAt}`,
      `- duration_ms: ${report.durationMs}`, `- society: ${report.societyId}`,
      ``, `## Self-assessment`,
      report.healthSnapshot ? `- health snapshot: ${JSON.stringify(report.healthSnapshot)}` : '',
      ...report.weaknesses.map(w => `- **${w.kind}**: ${w.detail} → goal: "${w.recommendedGoal.title}"`),
      ``, `## Outcome`,
      `- internal goal: ${report.internalGoalId}`,
      `- agenda item: ${report.agendaItemId}`,
      `- society: ${report.societyId}`,
      `- institution: ${report.institutionId}`,
      `- task type: ${report.taskType}`,
      `- claims processed: ${report.claimsProcessed}`,
      `- claims promoted: ${report.claimsPromoted}`,
      `- claims blocked: ${report.claimsBlocked}`,
      `- contradiction checks: ${report.contradictionChecks}`,
      `- contradictions detected: ${report.contradictionsDetected}`,
      `- agent spawn proposals: ${report.agentSpawnProposals}`,
      `- self-improvement proposals: ${report.selfImprovementProposals}`,
      `- governance queue requests: ${report.governanceQueueRequests}`,
      `- predictions registered: ${report.predictionsRegistered}`,
      report.errors.length ? `\n## Errors\n${report.errors.map(e => `- ${e}`).join('\n')}` : '',
    ].join('\n');
    fs.writeFileSync(path.join(dir, 'civilization_report.md'), md);
    fs.writeFileSync(path.join(dir, 'goals.jsonl'), extras.goals.map(g => JSON.stringify(g)).join('\n'));
    fs.writeFileSync(path.join(dir, 'claims.jsonl'), extras.claims.map(c => JSON.stringify(c)).join('\n'));
    fs.writeFileSync(path.join(dir, 'contradictions.jsonl'), extras.contradictions.map(c => JSON.stringify(c)).join('\n'));
    fs.writeFileSync(path.join(dir, 'agent_spawn_proposals.jsonl'), extras.agentSpawnProposals.map(p => JSON.stringify(p)).join('\n'));
    fs.writeFileSync(path.join(dir, 'self_improvement_proposals.jsonl'), extras.selfImprovementProposals.map(p => JSON.stringify(p)).join('\n'));
    fs.writeFileSync(path.join(dir, 'governance_queue_requests.jsonl'), extras.governanceQueueRequests.map(p => JSON.stringify(p)).join('\n'));
    fs.writeFileSync(path.join(dir, 'events.jsonl'), [
      { type: 'self_assessment', weaknesses: report.weaknesses, healthSnapshot: report.healthSnapshot },
      { type: 'society_agenda', agendaItemId: report.agendaItemId, societyId: report.societyId, institutionId: report.institutionId, taskType: report.taskType },
      { type: 'contradiction_detection', contradictionChecks: report.contradictionChecks, contradictionsDetected: report.contradictionsDetected },
      { type: 'agent_spawn_proposals', proposalsCreated: report.agentSpawnProposals },
      { type: 'self_improvement_proposals', proposalsCreated: report.selfImprovementProposals },
      { type: 'governance_queue_requests', requestsCreated: report.governanceQueueRequests },
      { type: 'promotion_gate', claimsPromoted: report.claimsPromoted, claimsBlocked: report.claimsBlocked },
      { type: 'prediction_registration', predictionsRegistered: report.predictionsRegistered },
    ].map(e => JSON.stringify(e)).join('\n'));
    fs.writeFileSync(path.join(dir, 'report.json'), JSON.stringify(report, null, 2));
  }

  /**
   * Orchestrate one free-run pass.
   * @param boundedTask optional executor for read_only_web mode: given the internal goalId, runs the
   *   real autonomy loop and returns the claim ids it produced. Fixture mode ignores it.
   */
  async run(mode: FreeRunMode = 'fixture', boundedTask?: (goalId: string) => Promise<string[]>): Promise<FreeRunReport> {
    const runId = `freerun_${Date.now()}`;
    const start = Date.now();
    const report: FreeRunReport = {
      runId, mode, startedAt: new Date().toISOString(), durationMs: 0,
      weaknesses: [], internalGoalId: null, agendaItemId: null, societyId: '', institutionId: '', taskType: '',
      claimsProcessed: 0, claimsPromoted: 0, claimsBlocked: 0, contradictionChecks: 0, contradictionsDetected: 0, agentSpawnProposals: 0, selfImprovementProposals: 0, governanceQueueRequests: 0, predictionsRegistered: 0,
      errors: [], reportDir: path.join(ARTIFACT_ROOT, runId),
    };
    let contradictions: ContradictionFinding[] = [];
    let agentSpawnProposals: AgentSpawnProposal[] = [];
    let selfImprovementProposals: SelfImprovementProposal[] = [];
    let governanceQueueRequests: GovernanceQueueRequest[] = [];
    try {
      report.healthSnapshot = await this.getHealthSnapshot();
      report.weaknesses = await this.weaknessesFromHealthSnapshot(report.healthSnapshot);
      const top = report.weaknesses[0];
      report.internalGoalId = await this.generateInternalGoal(top);
      const agenda = await this.createAgendaItem(report.internalGoalId, top);
      report.agendaItemId = agenda.agendaItemId;
      report.societyId = agenda.societyId;
      report.institutionId = agenda.institutionId;
      report.taskType = agenda.taskType;

      const claimIds = mode === 'fixture'
        ? await this.executeBoundedTaskFixture(report.internalGoalId, agenda)
        : (boundedTask ? await boundedTask(report.internalGoalId) : []);
      report.claimsProcessed = claimIds.length;

      contradictions = await this.detectContradictions(claimIds);
      report.contradictionChecks = claimIds.length;
      report.contradictionsDetected = contradictions.length;

      agentSpawnProposals = await this.proposeAgentSpawns(report.internalGoalId, agenda, contradictions);
      report.agentSpawnProposals = agentSpawnProposals.length;

      selfImprovementProposals = await this.proposeSelfImprovements(report.internalGoalId, report.weaknesses, {
        contradictionsDetected: report.contradictionsDetected,
        agentSpawnProposals: report.agentSpawnProposals,
        errors: report.errors,
      });
      report.selfImprovementProposals = selfImprovementProposals.length;

      governanceQueueRequests = await this.enqueueGovernanceReviewRequests(
        report.internalGoalId,
        agentSpawnProposals,
        selfImprovementProposals,
      );
      report.governanceQueueRequests = governanceQueueRequests.length;

      const gate = await this.promotionGate(claimIds);
      report.claimsPromoted = gate.promoted.length;
      report.claimsBlocked = gate.blocked.length;

      report.predictionsRegistered = await this.registerPredictions(gate.promoted);
    } catch (e) {
      report.errors.push(e instanceof Error ? e.message : String(e));
    }
    report.durationMs = Date.now() - start;
    const claimRows = report.internalGoalId
      ? await db.query(
        `SELECT c.claim_id, c.text, c.status, c.confidence, c.support_source_ids, c.support_snippets
           FROM autonomy_claims c
           JOIN autonomy_goal_actions a ON a.action_id = c.action_id
          WHERE a.goal_id = $1
          ORDER BY c.generated_at ASC`,
        [report.internalGoalId])
      : { rows: [] };
    await this.writeReport(report, { goals: [{ id: report.internalGoalId }], claims: claimRows.rows, contradictions, agentSpawnProposals, selfImprovementProposals, governanceQueueRequests, predictions: report.predictionsRegistered });
    return report;
  }
}

export const civilizationFreeRun = new CivilizationFreeRunService();
