/**
 * Action Executor Service
 * =======================
 * Executes validated ActionSpecs and returns typed ActionResults
 * Each action type has a specific handler
 * Integrates web fetching, evidence storage, and claim generation
 */

import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/client';
import {
  ActionSpec,
  ActionResult,
  ActionStatus,
  ActionType,
  Evidence,
  Claim,
} from '../types/action.types';
import { WebAdapter } from '../adapters/web-adapter';
import { TeamActivationService } from './team-activation.service';

export class ActionExecutorService {
  private webAdapter: WebAdapter | null = null;
  private teamActivation = new TeamActivationService();

  /**
   * Inject web adapter (can be real or mock)
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

  private async handleWebSearch(spec: ActionSpec, result: ActionResult): Promise<void> {
    const query = spec.args.query;
    if (!query) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Web search requires "query" argument';
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
            const sourceId = uuidv4();
            await db.query(
              `INSERT INTO autonomy_evidence (
                id, source_id, action_id, url, title, snippet, retrieved_at,
                content_hash, source_type, is_public_access, created_at
              ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, $8, $9, NOW())`,
              [
                uuidv4(),
                sourceId,
                spec.actionId,
                searchResult.url,
                searchResult.title,
                searchResult.snippet,
                `hash_${searchResult.rank || 0}`,
                'web_search',
                true,
              ]
            );
            result.createdArtifacts.push(sourceId);
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

    // Search failed - BLOCKED (no synthetic fallback)
    // Return BLOCKED status instead of fake results
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

    // Try to use web adapter if available
    // Skip isReady() - it checks Google which may be unreachable
    if (this.webAdapter) {
      try {
        const fetchResult = await this.webAdapter.fetch(url);

        if (fetchResult) {
          // Store evidence in database with real content
          const sourceId = uuidv4();
          await db.query(
            `INSERT INTO autonomy_evidence (
              id, action_id, source_id, url, title, snippet, retrieved_at, content_hash,
              source_type, is_public_access, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, $8, $9, NOW())`,
            [
              uuidv4(),
              spec.actionId,
              sourceId,
              url,
              fetchResult.title || 'Fetched Page',
              fetchResult.content.substring(0, 2000),  // First 2000 chars for extraction
              fetchResult.contentHash,
              'web',
              true,
            ]
          );

          result.observations.url = url;
          result.observations.title = fetchResult.title;
          result.observations.contentLength = fetchResult.content.length;
          result.createdArtifacts.push(sourceId);
          result.observations.status = 'fetch_completed';
          return;
        } else {
          result.observations.url = url;
          result.observations.status = 'fetch_failed_http_error';
          result.errors = ['HTTP fetch failed'];
          return;
        }
      } catch (error: any) {
        console.warn(`Web fetch failed: ${error.message}, recording fetch attempt`);
      }
    }

    // Fallback: Record fetch attempt with placeholder content
    const fetchId = uuidv4();
    try {
      const evidence: Evidence = {
        sourceId: uuidv4(),
        url,
        retrievedAt: new Date(),
        contentHash: `hash_fallback_${fetchId}`,
        sourceType: 'web',
        isPublicAccess: true,
      };

      await db.query(
        `INSERT INTO autonomy_evidence (
          id, action_id, source_id, url, title, retrieved_at, content_hash, source_type,
          is_public_access, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())`,
        [
          uuidv4(),
          spec.actionId,
          evidence.sourceId,
          url,
          'Fetch Attempted (Unavailable)',
          evidence.retrievedAt,
          evidence.contentHash,
          'web',
          evidence.isPublicAccess,
        ]
      );

      result.observations.fetchId = fetchId;
      result.observations.url = url;
      result.createdArtifacts.push(evidence.sourceId);
      result.observations.status = 'fetch_recorded';
    } catch (error: any) {
      result.status = ActionStatus.FAILED;
      result.errors = [error.message];
    }
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

    // CRITICAL: Validate claim is grounded in source content, not hallucinated
    const groundingValidation = await this.validateClaimGrounding(claimText, supportSourceIds);
    if (!groundingValidation.valid) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = `Claim not grounded in sources: ${groundingValidation.reason}`;
      console.warn(`❌ REJECTED ungrounded claim: "${claimText.substring(0, 80)}..."`);
      console.warn(`   Reason: ${groundingValidation.reason}`);
      return;
    }

    const claimId = uuidv4();
    const claim: Claim = {
      claimId,
      text: claimText,
      status: 'supported',
      confidence: spec.args.confidence || 0.7,
      supportSourceIds,
      supportSnippets: spec.args.supportSnippets || [],
      derivedFromActionIds: [spec.actionId],
      generatedAt: new Date(),
      generatedBy: spec.decidedBy,
    };

    // Store claim in database
    await db.query(
      `INSERT INTO autonomy_claims (
        id, claim_id, action_id, text, status, confidence, support_source_ids, derived_from_action_ids
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
      [
        uuidv4(),
        claimId,
        spec.actionId,
        claim.text,
        claim.status,
        claim.confidence,
        JSON.stringify(claim.supportSourceIds),
        JSON.stringify(claim.derivedFromActionIds),
      ]
    );

    result.observations.claimId = claimId;
    result.createdArtifacts.push(claimId);
    result.observations.claimText = claimText;
    result.observations.supportedBySources = supportSourceIds.length;
    console.log(`✅ ACCEPTED grounded claim: "${claimText.substring(0, 80)}..."`);
  }

  /**
   * Validate that a claim is actually grounded in source material
   * Reject hallucinated claims that fabricate concepts not in the sources
   */
  private async validateClaimGrounding(
    claimText: string,
    sourceIds: string[]
  ): Promise<{ valid: boolean; reason?: string }> {
    // Fetch source content (abstracts) from evidence table
    const result = await db.query(
      `SELECT id, url, snippet FROM autonomy_evidence
       WHERE id = ANY($1)`,
      [sourceIds]
    );

    if (result.rows.length === 0) {
      return { valid: false, reason: 'No sources found in database' };
    }

    const sourceContents = result.rows.map(r => r.snippet || r.url).join(' ');

    // Check: claim must reference terms/concepts actually present in sources
    // Look for proper names, theorems, key concepts that should be grounded
    const claimLower = claimText.toLowerCase();

    // Red flag patterns: unverifiable theorems or invented proper nouns
    const redFlags = [
      /(\d+[a-z]m?\s+theorem)/i,  // "6m Theorem", "3x Theorem" - likely fabricated
      /theorem for\s+[a-z\s]+that\s+doesn't exist/i,
      /newly discovered [a-z\s]+theorem/i,
    ];

    for (const pattern of redFlags) {
      if (pattern.test(claimText)) {
        // Check if this specific theorem is mentioned in the sources
        const theoremMatch = claimText.match(/(\w+\s+theorem)/i);
        if (theoremMatch) {
          const theorem = theoremMatch[1];
          if (!sourceContents.toLowerCase().includes(theorem.toLowerCase())) {
            return {
              valid: false,
              reason: `Theorem "${theorem}" not found in sources`
            };
          }
        }
      }
    }

    // Basic check: claim should have some overlap with source terms
    // Extract key terms from claim
    const claimTerms = claimText.match(/\b[a-z]{4,}\b/gi) || [];
    const sourceTerms = sourceContents.toLowerCase();

    let matchCount = 0;
    for (const term of claimTerms) {
      if (sourceTerms.includes(term.toLowerCase())) {
        matchCount++;
      }
    }

    // If less than 30% of claim terms appear in sources, likely hallucinated
    const matchRatio = claimTerms.length > 0 ? matchCount / claimTerms.length : 0;
    if (matchRatio < 0.3 && claimTerms.length > 5) {
      return {
        valid: false,
        reason: `Only ${(matchRatio * 100).toFixed(0)}% of claim terms found in sources`
      };
    }

    return { valid: true };
  }

  private async handleUpdateMemory(spec: ActionSpec, result: ActionResult): Promise<void> {
    const memoryContent = spec.args.content;
    if (!memoryContent) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Update memory requires "content" argument';
      return;
    }

    const memoryId = uuidv4();
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, timestamp)
       VALUES ($1, $2, $3, NOW())`,
      [memoryId, spec.actionId, JSON.stringify(memoryContent)]
    );

    result.observations.memoryId = memoryId;
    result.createdArtifacts.push(memoryId);
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
    const objective = spec.args.objective;
    const parentGoalId = spec.goalId;
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
      // Wait for specialist to complete (with timeout)
      const specialistResults = await this.waitForSpecialistCompletion(specialist);

      if (specialistResults) {
        // Persist specialist results to database
        await this.persistSpecialistResults(parentGoalId, specialistResults);

        result.observations = {
          ...result.observations,
          specialistId: specialist.specialistId,
          role: specialist.role,
          status: 'specialist_completed',
          artifactsCreated: specialistResults.artifacts?.length || 0,
          claimsGenerated: specialistResults.claims?.length || 0,
          evidenceCollected: specialistResults.evidence?.length || 0,
        };
        result.createdArtifacts.push(...(specialistResults.artifacts || []));
        result.status = ActionStatus.COMPLETED;
      } else {
        result.observations.status = 'specialist_timeout';
        result.observations.specialistId = specialist.specialistId;
        result.status = ActionStatus.FAILED;
        if (!result.errors) result.errors = [];
        result.errors.push('Specialist timed out before completion');
      }
    } catch (error: any) {
      result.status = ActionStatus.FAILED;
      result.observations.specialistId = specialist.specialistId;
      if (!result.errors) result.errors = [];
      result.errors.push(`Specialist execution failed: ${error.message}`);
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
