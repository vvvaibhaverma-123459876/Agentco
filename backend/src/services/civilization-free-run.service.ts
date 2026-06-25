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
import fs from 'fs';
import path from 'path';
import { v4 as uuid } from 'uuid';
import { goalManager } from './goal-manager.service';
import { Phase0bCalibrationService } from './phase0b-calibration.service';
import { validateGrounding, GroundingSource } from './claim-grounding';
import { SourceQualityService } from './source-quality.service';
import { getSpecialistRole } from '../types/specialist-roles';
import { ProtectedSurfaceEnforcerService } from './protected-surface-enforcer.service';

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
  predictionsRegistered: number;
  errors: string[];
  reportDir: string;
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

const ARTIFACT_ROOT = path.resolve(__dirname, '..', '..', '..', 'audit_artifacts', 'civilization_free_run');

export class CivilizationFreeRunService {
  private phase0b = new Phase0bCalibrationService();
  private sourceQuality = new SourceQualityService();
  private protectedSurfaceEnforcer = new ProtectedSurfaceEnforcerService();

  /** STEP 1: inspect civilization state and identify the most salient weakness + a recommended goal. */
  async selfAssess(): Promise<Weakness[]> {
    const weaknesses: Weakness[] = [];

    const totals = await db.query(
      `SELECT
         (SELECT count(*) FROM autonomy_claims) AS claims,
         (SELECT count(*) FROM autonomy_claims WHERE status = 'promoted') AS promoted,
         (SELECT count(*) FROM autonomy_claims WHERE status = 'supported') AS supported,
         (SELECT count(*) FROM autonomy_evidence) AS evidence`
    );
    const t = totals.rows[0];
    const claims = Number(t.claims), promoted = Number(t.promoted), supported = Number(t.supported);

    // Weakness: knowledge exists but little is promoted to trusted knowledge ("believe slowly" backlog).
    if (supported > promoted) {
      weaknesses.push({
        kind: 'unpromoted_knowledge',
        detail: `${supported} supported claims vs ${promoted} promoted — a promotion backlog`,
        recommendedGoal: {
          title: 'Validate and promote high-confidence supported claims',
          description: 'Run the evidence promotion gate over supported claims and promote those that pass.',
          domain: 'calibration',
        },
      });
    }

    // Weakness: thin evidence base → go gather more.
    if (claims < 10) {
      weaknesses.push({
        kind: 'thin_evidence',
        detail: `only ${claims} claims in the knowledge base`,
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
      ? 'Deepen self-assessment beyond claim counts by including stale predictions, weak domains, unresolved contradictions, and specialist coverage.'
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
  async writeReport(report: FreeRunReport, extras: { goals: unknown[]; claims: unknown[]; contradictions: unknown[]; agentSpawnProposals: unknown[]; selfImprovementProposals: unknown[]; predictions: number }): Promise<void> {
    const dir = report.reportDir;
    fs.mkdirSync(dir, { recursive: true });
    const md = [
      `# Civilization Free-Run Report`,
      ``, `- run_id: ${report.runId}`, `- mode: ${report.mode}`, `- started: ${report.startedAt}`,
      `- duration_ms: ${report.durationMs}`, `- society: ${report.societyId}`,
      ``, `## Self-assessment`,
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
      `- predictions registered: ${report.predictionsRegistered}`,
      report.errors.length ? `\n## Errors\n${report.errors.map(e => `- ${e}`).join('\n')}` : '',
    ].join('\n');
    fs.writeFileSync(path.join(dir, 'civilization_report.md'), md);
    fs.writeFileSync(path.join(dir, 'goals.jsonl'), extras.goals.map(g => JSON.stringify(g)).join('\n'));
    fs.writeFileSync(path.join(dir, 'claims.jsonl'), extras.claims.map(c => JSON.stringify(c)).join('\n'));
    fs.writeFileSync(path.join(dir, 'contradictions.jsonl'), extras.contradictions.map(c => JSON.stringify(c)).join('\n'));
    fs.writeFileSync(path.join(dir, 'agent_spawn_proposals.jsonl'), extras.agentSpawnProposals.map(p => JSON.stringify(p)).join('\n'));
    fs.writeFileSync(path.join(dir, 'self_improvement_proposals.jsonl'), extras.selfImprovementProposals.map(p => JSON.stringify(p)).join('\n'));
    fs.writeFileSync(path.join(dir, 'events.jsonl'), [
      { type: 'self_assessment', weaknesses: report.weaknesses },
      { type: 'society_agenda', agendaItemId: report.agendaItemId, societyId: report.societyId, institutionId: report.institutionId, taskType: report.taskType },
      { type: 'contradiction_detection', contradictionChecks: report.contradictionChecks, contradictionsDetected: report.contradictionsDetected },
      { type: 'agent_spawn_proposals', proposalsCreated: report.agentSpawnProposals },
      { type: 'self_improvement_proposals', proposalsCreated: report.selfImprovementProposals },
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
      claimsProcessed: 0, claimsPromoted: 0, claimsBlocked: 0, contradictionChecks: 0, contradictionsDetected: 0, agentSpawnProposals: 0, selfImprovementProposals: 0, predictionsRegistered: 0,
      errors: [], reportDir: path.join(ARTIFACT_ROOT, runId),
    };
    let contradictions: ContradictionFinding[] = [];
    let agentSpawnProposals: AgentSpawnProposal[] = [];
    let selfImprovementProposals: SelfImprovementProposal[] = [];
    try {
      report.weaknesses = await this.selfAssess();
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
    await this.writeReport(report, { goals: [{ id: report.internalGoalId }], claims: claimRows.rows, contradictions, agentSpawnProposals, selfImprovementProposals, predictions: report.predictionsRegistered });
    return report;
  }
}

export const civilizationFreeRun = new CivilizationFreeRunService();
