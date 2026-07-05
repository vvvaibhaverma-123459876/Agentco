/**
 * Action Executor Service
 * =======================
 * Executes validated ActionSpecs and returns typed ActionResults
 * Each action type has a specific handler
 * Integrates web fetching, evidence storage, and claim generation
 */

import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/client';
import {
  ActionSpec,
  ActionResult,
  ActionStatus,
  ActionType,
  Claim,
} from '../types/action.types';
import { WebAdapter } from '../adapters/web-adapter';
import { RealWebAdapter } from '../adapters/real-web-adapter';
import { TeamActivationService } from './team-activation.service';
import { evidenceRegistry } from './evidence-registry.service';
import { claimGrounding } from './claim-grounding.service';
import { coreAssertionTokens } from './falsifiable-prediction.service';
import { relevanceScore, CLAIM_RELEVANCE_THRESHOLD } from './goal-source-discovery.service';
import { inputValidatorService as inputValidator } from './input-validator.service';

export class ActionExecutorService {
  // Default to a real web adapter so the direct-fetch (fetch_page) evidence
  // path works with zero configuration (GA2). Tests override via
  // setWebAdapter(new MockWebAdapter()). All fetches pass the SSRF guard.
  private webAdapter: WebAdapter | null = new RealWebAdapter();
  private teamActivation = new TeamActivationService();

  /**
   * Inject web adapter implementation.
   */
  setWebAdapter(adapter: WebAdapter): void {
    this.webAdapter = adapter;
  }
  /**
   * Execute a validated action and return typed result
   */
  async executeAction(spec: ActionSpec): Promise<ActionResult> {
    const result: ActionResult = {
      actionId: spec.actionId,
      status: ActionStatus.EXECUTING,
      startedAt: new Date(),
      observations: {},
      createdArtifacts: [],
      toolCalls: [],
    };

    try {
      await this.ensureActionRecord(spec);

      switch (spec.actionType) {
        case ActionType.WEB_SEARCH:
          await this.handleWebSearch(spec, result);
          break;
        case ActionType.FETCH_PAGE:
          await this.handleFetchPage(spec, result);
          break;
        case ActionType.EXTRACT_EVIDENCE:
          await this.handleExtractEvidence(spec, result);
          break;
        case ActionType.GENERATE_CLAIM:
          await this.handleGenerateClaim(spec, result);
          break;
        case ActionType.UPDATE_MEMORY:
          await this.handleUpdateMemory(spec, result);
          break;
        case ActionType.EVALUATE_PROGRESS:
          await this.handleEvaluateProgress(spec, result);
          break;
        case ActionType.SPAWN_SPECIALIST:
          await this.handleSpawnSpecialist(spec, result);
          break;
        case ActionType.TERMINATE:
          await this.handleTerminate(spec, result);
          break;
        case ActionType.REPLAN:
          await this.handleReplan(spec, result);
          break;
        default:
          result.status = ActionStatus.BLOCKED;
          result.blockedReason = `Unknown action type: ${spec.actionType}`;
      }
    } catch (error: any) {
      result.status = ActionStatus.FAILED;
      result.errors = [error.message];
      result.completedAt = new Date();
    }

    if (result.status === ActionStatus.EXECUTING) {
      result.status = ActionStatus.COMPLETED;
    }

    // Ensure completedAt is always set for completed/terminal actions
    if (!result.completedAt) {
      result.completedAt = new Date();
    }

    return result;
  }

  private async ensureActionRecord(spec: ActionSpec): Promise<void> {
    if (!this.isUuid(spec.actionId)) {
      return;
    }

    if (this.isUuid(spec.goalId)) {
      // autonomy_goal_actions.goal_id carries an FK to autonomy_goals; callers
      // may execute actions under a goal id that was minted outside the goal
      // manager, so guarantee the referenced goal row exists first.
      await db.query(
        `INSERT INTO autonomy_goals (id, title, source, proposed_by, domain, risk_level, status)
         VALUES ($1, $2, 'agent_proposed', $3, 'action_loop', COALESCE($4, 'medium')::risk_level, 'active')
         ON CONFLICT (id) DO NOTHING`,
        [
          spec.goalId,
          spec.objective || spec.actionType,
          spec.decidedBy || 'action_executor',
          spec.riskLevel || null,
        ]
      );
      await db.query(
        `INSERT INTO autonomy_goal_actions (
          action_id, goal_id, action_type, objective, args, success_criteria,
          risk_level, decided_by, decided_at, reasoning, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'executing')
        ON CONFLICT (action_id) DO NOTHING`,
        [
          spec.actionId,
          spec.goalId,
          spec.actionType,
          spec.objective || spec.actionType,
          JSON.stringify(spec.args || {}),
          JSON.stringify(spec.successCriteria || []),
          spec.riskLevel || null,
          spec.decidedBy || null,
          spec.decidedAt || new Date(),
          spec.reasoning || null,
        ]
      );
    }

    const episodeId = uuidv4();
    await db.query(
      `INSERT INTO autonomy_episodes (
        id, run_id, agent_id, title, domain, risk_level, autonomy_level,
        intervention_required, trace_id, metadata
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, false, $8, $9)
      ON CONFLICT (id) DO NOTHING`,
      [
        episodeId,
        `action_executor_${spec.goalId}`,
        spec.decidedBy || 'action_executor',
        spec.objective || spec.actionType,
        'action_loop',
        spec.riskLevel || 'low',
        1,
        uuidv4(),
        JSON.stringify({ goalId: spec.goalId }),
      ]
    );

    await db.query(
      `INSERT INTO autonomy_actions (
        id, episode_id, step_index, action_type, tool_name, success, metadata
      ) VALUES ($1, $2, 0, $3, $4, false, $5)
      ON CONFLICT (id) DO NOTHING`,
      [
        spec.actionId,
        episodeId,
        this.toCanonicalAutonomyActionType(spec.actionType),
        spec.actionType,
        JSON.stringify({ objective: spec.objective, actionType: spec.actionType, args: spec.args || {} }),
      ]
    );
  }

  private toCanonicalAutonomyActionType(actionType: ActionType): string {
    if (actionType === ActionType.UPDATE_MEMORY) {
      return 'memory_write';
    }
    if (actionType === ActionType.TERMINATE || actionType === ActionType.REPLAN) {
      return 'decision';
    }
    return 'tool_call';
  }

  private isUuid(value?: string): boolean {
    return Boolean(
      value &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
    );
  }

  private actorIdFromSpec(spec: ActionSpec): string | null {
    return this.isUuid(spec.decidedBy) ? spec.decidedBy : null;
  }

  private contentHash(...parts: string[]): string {
    return crypto.createHash('sha256').update(parts.join('\n')).digest('hex');
  }

  private async handleWebSearch(spec: ActionSpec, result: ActionResult): Promise<void> {
    const query = spec.args.query;
    if (!query) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Web search requires "query" argument';
      return;
    }
    // Input validation (E4/G11): length caps + injection patterns.
    const queryCheck = inputValidator.validateSearchQuery(query);
    if (!queryCheck.valid) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = `Search query rejected: ${queryCheck.error}`;
      return;
    }

    // Try to use web adapter if available
    // Skip isReady() - it checks Google which may be unreachable
    if (this.webAdapter) {
      try {
        const searchResults = await this.webAdapter.search(query);

        if (searchResults.length > 0) {
          // Store each search result as evidence
          for (const searchResult of searchResults) {
            const evidence = await evidenceRegistry.register({
              action_id: spec.actionId,
              actor_id: this.actorIdFromSpec(spec),
              url: searchResult.url,
              title: searchResult.title,
              snippet: searchResult.snippet,
              content_hash: this.contentHash(searchResult.url, searchResult.snippet ?? '', String(searchResult.rank ?? 0)),
              source_type: 'web_search',
              is_public_access: true,
              metadata: { query, rank: searchResult.rank ?? null },
            });
            result.createdArtifacts.push(evidence.source_id);
          }

          result.observations.searchQuery = query;
          result.observations.resultsFound = searchResults.length;
          result.observations.status = 'search_completed';
        } else {
          result.observations.searchQuery = query;
          result.observations.resultsFound = 0;
          result.observations.status = 'search_completed_no_results';
        }
        return;
      } catch (error: any) {
        console.warn(`Web search failed: ${error.message}, trying fallback search`);
      }
    }

    // Search failed: block without creating synthetic artifacts.
    result.status = ActionStatus.BLOCKED;
    result.blockedReason = `Web search failed for query: "${query}". No real search results available. Configure SEARCH_ENGINE_API_KEY or BING_SEARCH_API_KEY for real search capability.`;
    result.observations.searchQuery = query;
    result.observations.resultsFound = 0;
    result.observations.status = 'search_blocked_no_real_results';
    result.errors = [result.blockedReason];
  }


  private async handleFetchPage(spec: ActionSpec, result: ActionResult): Promise<void> {
    const url = spec.args.url;
    if (!url) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Fetch requires "url" argument';
      return;
    }
    // Input validation (E4/G11): scheme/length/shape checks up front; the
    // DNS-resolving SSRF guard in url-safety.ts still runs inside the fetch.
    // Loopback is allowed only under the test-fixture flag the SSRF guard
    // itself honors.
    if (process.env.AGENTCO_ALLOW_LOOPBACK_FETCH !== '1') {
      const urlCheck = inputValidator.validateUrl(url);
      if (!urlCheck.valid) {
        result.status = ActionStatus.BLOCKED;
        result.blockedReason = `Fetch URL rejected: ${urlCheck.error}`;
        return;
      }
    }

    // Try to use web adapter if available
    // Skip isReady() - it checks Google which may be unreachable
    if (this.webAdapter) {
      try {
        const fetchResult = await this.webAdapter.fetch(url);

        if (fetchResult) {
          // Store evidence in database with real content
          // Store readable prose (not raw HTML) as the snippet so claim
          // grounding has quotable text; keep the raw-content hash for
          // exact-byte provenance.
          const readable = (fetchResult.textContent && fetchResult.textContent.length > 0
            ? fetchResult.textContent
            : fetchResult.content
          ).substring(0, 2000);
          const evidence = await evidenceRegistry.register({
            action_id: spec.actionId,
            actor_id: this.actorIdFromSpec(spec),
            url,
            title: fetchResult.title || 'Fetched Page',
            snippet: readable,
            content_hash: fetchResult.contentHash,
            source_type: 'web',
            is_public_access: true,
          });

          result.observations.url = url;
          result.observations.title = fetchResult.title;
          result.observations.contentLength = fetchResult.content.length;
          result.createdArtifacts.push(evidence.source_id);
          result.observations.status = 'fetch_completed';
          return;
        } else {
          // A null fetch means the SSRF guard rejected the target or the HTTP
          // fetch failed. Either way no evidence was created, so the action is
          // BLOCKED (honest) rather than silently "completed".
          result.status = ActionStatus.BLOCKED;
          result.blockedReason = `Fetch produced no evidence for URL "${url}" (SSRF-blocked or HTTP failure)`;
          result.observations.url = url;
          result.observations.status = 'fetch_blocked_no_real_content';
          result.errors = [result.blockedReason];
          return;
        }
      } catch (error: any) {
        console.warn(`Web fetch failed: ${error.message}; no artifact will be recorded without real content`);
      }
    }

    result.status = ActionStatus.BLOCKED;
    result.blockedReason = `Fetch failed for URL: "${url}". No real page content available, so no evidence artifact was created.`;
    result.observations.url = url;
    result.observations.status = 'fetch_blocked_no_real_content';
    result.errors = [result.blockedReason];
  }

  private async handleExtractEvidence(spec: ActionSpec, result: ActionResult): Promise<void> {
    const sourceId = spec.args.sourceId;
    if (!sourceId) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Extract requires "sourceId" argument';
      return;
    }

    // Record extraction decision
    result.observations.sourceId = sourceId;
    result.observations.status = 'extraction_recorded';
  }

  private async handleGenerateClaim(spec: ActionSpec, result: ActionResult): Promise<void> {
    const claimText = spec.args.claimText;
    const supportSourceIds = spec.args.supportSourceIds || [];

    if (!claimText) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Generate claim requires "claimText" argument';
      return;
    }

    if (supportSourceIds.length === 0) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Claims must be supported by at least one source (no unsupported claims)';
      return;
    }

    const grounding = await claimGrounding.validate({
      claimText,
      supportSourceIds,
      supportSnippets: spec.args.supportSnippets || [],
    });
    if (!grounding.valid) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = `Claim grounding failed: ${grounding.errors.join('; ')}`;
      return;
    }

    // Relevance gate (Phase B/G4): a claim must be about the GOAL, not just
    // quotable from some fetched page. Grounded-but-off-goal claims are
    // downgraded to weakly_supported so they never feed predictions or
    // deliverables as findings.
    let relevance: number | null = null;
    let relevanceReason = 'no goal text available for relevance scoring';
    let claimStatus: 'supported' | 'weakly_supported' = 'supported';
    if (spec.goalId) {
      // Only gate on a genuine goal description. Ad-hoc executor calls create
      // goals whose title is just the action objective; scoring a claim
      // against that is meaningless, so those claims are not downgraded.
      const goalRow = await db.query<{ description: string | null }>(
        `SELECT description FROM autonomy_goals WHERE id = $1`,
        [spec.goalId]
      );
      const goalText = goalRow.rows[0]?.description ?? undefined;
      if (goalText) {
        const goalTokens = coreAssertionTokens(goalText, 12);
        const snippets = (spec.args.supportSnippets || []).join(' ');
        relevance = relevanceScore(goalTokens, `${claimText} ${snippets}`);
        if (relevance < CLAIM_RELEVANCE_THRESHOLD) {
          claimStatus = 'weakly_supported';
          relevanceReason = `grounded but off-goal: ${(relevance * 100).toFixed(0)}% goal-token overlap (< ${CLAIM_RELEVANCE_THRESHOLD * 100}%)`;
          result.observations.relevanceDowngrade = relevanceReason;
        } else {
          relevanceReason = `${(relevance * 100).toFixed(0)}% goal-token overlap`;
        }
      }
    }

    const claimId = uuidv4();
    const claim: Claim = {
      claimId,
      text: claimText,
      status: claimStatus,
      confidence: spec.args.confidence || 0.7,
      supportSourceIds,
      supportSnippets: spec.args.supportSnippets || [],
      derivedFromActionIds: [spec.actionId],
      generatedAt: new Date(),
      generatedBy: spec.decidedBy,
    };

    // Store claim in database with its goal-relevance decision (Phase B/G4)
    await db.query(
      `INSERT INTO autonomy_claims (
        id, claim_id, action_id, goal_id, text, status, confidence, support_source_ids, support_snippets, derived_from_action_ids,
        relevance_score, relevance_reason
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
      [
        uuidv4(),
        claimId,
        spec.actionId,
        spec.goalId ?? null,
        claim.text,
        claim.status,
        claim.confidence,
        JSON.stringify(claim.supportSourceIds),
        JSON.stringify(claim.supportSnippets),
        JSON.stringify(claim.derivedFromActionIds),
        relevance,
        relevanceReason,
      ]
    );

    result.observations.claimId = claimId;
    result.createdArtifacts.push(claimId);
    result.observations.claimText = claimText;
    result.observations.supportedBySources = supportSourceIds.length;
  }

  private async handleUpdateMemory(spec: ActionSpec, result: ActionResult): Promise<void> {
    const memoryContent = spec.args.content;
    if (!memoryContent) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Update memory requires "content" argument';
      return;
    }

    const memoryId = uuidv4();
    // Preserve the autonomy_memory write (reflection/metrics read this table).
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, timestamp)
       VALUES ($1, $2, $3, NOW())`,
      [memoryId, spec.actionId, JSON.stringify(memoryContent)]
    );

    // Dual-write into agent_memories so the planner's retrieval path can reuse
    // this self-generated memory in a later run (GA1). It enters as a
    // self-derived HYPOTHESIS, not verified knowledge: episodic type,
    // 'autonomous_self' namespace, explicit provenance, and a low importance
    // so promoted/verified knowledge always outranks it. task_id links back to
    // the autonomy_memory row for idempotency/traceability.
    try {
      const summary = this.summarizeMemoryContent(memoryContent);
      if (summary) {
        const domain = await this.goalDomain(spec.goalId);
        await db.query(
          `INSERT INTO agent_memories
             (agent_id, memory_type, namespace, task_id, domain, summary, content, importance)
           VALUES ('autonomy-loop','episodic','autonomous_self',$1,$2,$3,$4::jsonb,0.4)`,
          [
            memoryId,
            domain,
            summary,
            JSON.stringify({
              source: 'autonomous_update_memory',
              action_id: spec.actionId,
              goal_id: spec.goalId ?? null,
              autonomy_memory_id: memoryId,
              original: memoryContent,
            }),
          ]
        );
      }
    } catch (error) {
      // Retrieval mirroring is best-effort; the canonical autonomy_memory row
      // is already written. Log loudly so a broken mirror is never silent.
      console.error(`[handleUpdateMemory] agent_memories mirror failed (self-memory not retrievable): ${error}`);
    }

    result.observations.memoryId = memoryId;
    result.createdArtifacts.push(memoryId);
  }

  private summarizeMemoryContent(content: unknown): string | null {
    if (typeof content === 'string') return content.slice(0, 2000) || null;
    if (content && typeof content === 'object') {
      const text = (content as Record<string, unknown>).text;
      if (typeof text === 'string' && text.trim()) return text.slice(0, 2000);
      try {
        return JSON.stringify(content).slice(0, 2000);
      } catch {
        return null;
      }
    }
    return null;
  }

  private async goalDomain(goalId?: string): Promise<string | null> {
    if (!goalId) return null;
    const row = await db.query<{ domain: string }>(`SELECT domain FROM autonomy_goals WHERE id = $1`, [goalId]);
    return row.rows[0]?.domain ?? null;
  }

  private async handleEvaluateProgress(spec: ActionSpec, result: ActionResult): Promise<void> {
    const goalId = spec.args.goalId;

    // Query artifacts generated in this goal
    const claimsResult = await db.query(
      `SELECT COUNT(*) as count FROM autonomy_claims
       WHERE derived_from_action_ids @> $1::jsonb`,
      [JSON.stringify([spec.actionId])]
    );

    const claimCount = parseInt(claimsResult.rows[0]?.count || 0);

    result.observations.goalId = goalId;
    result.observations.claimsGenerated = claimCount;
    result.observations.status = 'progress_evaluated';
    result.nextStepHint =
      claimCount > 0
        ? 'Good progress. Consider searching for contradictions or evidence gaps.'
        : 'No claims yet. Continue gathering evidence.';
  }

  private async handleSpawnSpecialist(spec: ActionSpec, result: ActionResult): Promise<void> {
    const role = spec.args.role;
    const objective = spec.args.objective || spec.objective;
    const parentGoalId = spec.goalId || spec.args.goalId;
    const customBudget = spec.args.budget;

    if (!role || !objective || !parentGoalId) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Spawn specialist requires "role", "objective", and "goalId"';
      return;
    }

    // Activate specialist
    const specialist = await this.teamActivation.activateSpecialist({
      parentGoalId,
      role,
      objective,
      customBudget,
    });

    if (!specialist) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = `Failed to activate specialist with role "${role}"`;
      return;
    }

    try {
      // Choose the right action type based on the specialist role's allowed actions
      const searchRoles = new Set([
        'researcher', 'background_researcher', 'data_analyst',
        'comparative_analyst', 'temporal_analyst', 'sentiment_analyzer', 'fetcher',
      ]);
      const primaryActionType = searchRoles.has(role) ? 'WEB_SEARCH' : 'EXTRACT_EVIDENCE';
      const primaryArgs = primaryActionType === 'WEB_SEARCH'
        ? { query: objective }
        : { content: objective, source: parentGoalId };

      // Send the task directly to the specialist's HTTP /execute endpoint
      const taskPayload = {
        actionType: primaryActionType,
        objective,
        args: primaryArgs,
        goalId: parentGoalId,
        specialistId: specialist.specialistId,
      };

      const execResponse = await fetch(`${specialist.httpEndpoint}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskPayload),
        signal: AbortSignal.timeout(25000),
      });

      if (!execResponse.ok) {
        const errBody = await execResponse.text();
        throw new Error(`Specialist /execute returned ${execResponse.status}: ${errBody}`);
      }

      const execResult = await execResponse.json() as {
        status: string;
        observations?: Record<string, any>;
        artifacts?: string[];
        errors?: string[];
      };

      // Kill the specialist subprocess after it responds
      await this.teamActivation.terminateSpecialist(specialist.specialistId, {
        artifacts: execResult.artifacts || [],
        evidence: [],
        claims: [],
      }).catch(() => {/* ignore cleanup errors */});

      if (execResult.status === 'completed') {
        result.observations = {
          ...result.observations,
          specialistId: specialist.specialistId,
          role: specialist.role,
          status: 'specialist_completed',
          ...execResult.observations,
          artifactsCreated: execResult.artifacts?.length || 0,
        };
        result.createdArtifacts.push(...(execResult.artifacts || []));
        result.status = ActionStatus.COMPLETED;
      } else {
        result.status = ActionStatus.FAILED;
        if (!result.errors) result.errors = [];
        result.errors.push(...(execResult.errors || [`Specialist returned status: ${execResult.status}`]));
      }
    } catch (error: any) {
      result.status = ActionStatus.FAILED;
      result.observations.specialistId = specialist.specialistId;
      if (!result.errors) result.errors = [];
      result.errors.push(`Specialist execution failed: ${error.message}`);
      // Attempt cleanup
      await this.teamActivation.terminateSpecialist(specialist.specialistId, {
        artifacts: [],
        evidence: [],
        claims: [],
        error: error.message,
      }).catch(() => {/* ignore */});
    }
  }

  /**
   * Wait for specialist to complete and return results
   */
  private async waitForSpecialistCompletion(
    specialist: any,
    timeoutMs: number = 30000
  ): Promise<{ artifacts: string[]; evidence: string[]; claims: string[] } | null> {
    const startTime = Date.now();
    const pollInterval = 500; // Poll every 500ms

    while (Date.now() - startTime < timeoutMs) {
      try {
        // Query database for specialist record
        const query = await db.query(
          `SELECT status, results FROM autonomy_team_activations WHERE specialist_id = $1`,
          [specialist.specialistId]
        );

        if (query.rows.length === 0) {
          console.warn(`Specialist record not found: ${specialist.specialistId}`);
          return null;
        }

        const row = query.rows[0];

        // Check if specialist has completed
        if (row.status === 'completed' || row.status === 'failed') {
          if (row.results) {
            try {
              return JSON.parse(row.results);
            } catch (e) {
              console.error(`Failed to parse specialist results: ${e}`);
              throw new Error('Invalid JSON in specialist results');
            }
          }
          return null;
        }

        // Still running, wait before polling again
        await new Promise((resolve) => setTimeout(resolve, pollInterval));
      } catch (error: any) {
        console.error(`Error polling specialist status: ${error.message}`);
        return null;
      }
    }

    // Timeout reached
    console.warn(`Specialist did not complete within ${timeoutMs}ms`);
    return null;
  }

  /**
   * Persist specialist results back to parent goal
   */
  private async persistSpecialistResults(
    parentGoalId: string,
    results: { artifacts: string[]; evidence: string[]; claims: string[] }
  ): Promise<void> {
    // Link evidence artifacts to parent goal
    for (const evidenceId of results.evidence || []) {
      try {
        await db.query(
          `UPDATE autonomy_evidence SET goal_id = $1 WHERE id = $2`,
          [parentGoalId, evidenceId]
        );
      } catch (error: any) {
        console.warn(`Failed to link evidence ${evidenceId} to goal: ${error.message}`);
      }
    }

    // Link claims to parent goal
    for (const claimId of results.claims || []) {
      try {
        await db.query(
          `UPDATE autonomy_claims SET goal_id = $1 WHERE id = $2`,
          [parentGoalId, claimId]
        );
      } catch (error: any) {
        console.warn(`Failed to link claim ${claimId} to goal: ${error.message}`);
      }
    }

    console.log(
      `[Specialist] Persisted ${results.artifacts?.length || 0} artifacts ` +
        `${results.evidence?.length || 0} evidence, ${results.claims?.length || 0} claims to goal ${parentGoalId}`
    );
  }

  private async handleTerminate(spec: ActionSpec, result: ActionResult): Promise<void> {
    const reason = spec.args.reason || 'Autonomy loop terminated';
    result.observations.terminationReason = reason;
    result.observations.status = 'terminated';
  }

  private async handleReplan(spec: ActionSpec, result: ActionResult): Promise<void> {
    const loopType = spec.args.loopType || 'unknown';
    const streak = spec.args.streak || 0;

    // Record replan decision in database
    const replanId = uuidv4();
    await db.query(
      `INSERT INTO autonomy_loop_detection (id, goal_id, is_looping, loop_type, streak, recommendation, detected_at, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())`,
      [replanId, spec.goalId, true, loopType, streak, 'replan']
    );

    result.observations.replanId = replanId;
    result.observations.loopType = loopType;
    result.observations.streak = streak;
    result.observations.status = 'replan_triggered';
    result.createdArtifacts.push(replanId);
  }
}
