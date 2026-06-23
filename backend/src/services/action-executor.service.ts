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
    if (this.webAdapter && (await this.webAdapter.isReady())) {
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
        console.warn(`Web search failed: ${error.message}, falling back to stub behavior`);
      }
    }

    // Fallback: stub behavior (record search intent only)
    const searchId = uuidv4();
    await db.query(
      `INSERT INTO autonomy_searches (id, action_id, query, status)
       VALUES ($1, $2, $3, $4)`,
      [searchId, spec.actionId, query, 'initiated']
    );

    result.observations.searchId = searchId;
    result.observations.query = query;
    result.observations.status = 'search_recorded';
  }

  private async handleFetchPage(spec: ActionSpec, result: ActionResult): Promise<void> {
    const url = spec.args.url;
    if (!url) {
      result.status = ActionStatus.BLOCKED;
      result.blockedReason = 'Fetch requires "url" argument';
      return;
    }

    // Try to use web adapter if available
    if (this.webAdapter && (await this.webAdapter.isReady())) {
      try {
        const fetchResult = await this.webAdapter.fetch(url);

        if (fetchResult) {
          // Store evidence in database with real content
          const sourceId = uuidv4();
          await db.query(
            `INSERT INTO autonomy_evidence (
              id, action_id, source_id, url, title, retrieved_at, content_hash,
              source_type, is_public_access, created_at
            ) VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7, $8, NOW())`,
            [
              uuidv4(),
              spec.actionId,
              sourceId,
              url,
              fetchResult.title || 'Fetched Page',
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
        console.warn(`Web fetch failed: ${error.message}, falling back to stub behavior`);
      }
    }

    // Fallback: stub behavior (record fetch intent only)
    const fetchId = uuidv4();
    try {
      const evidence: Evidence = {
        sourceId: uuidv4(),
        url,
        retrievedAt: new Date(),
        contentHash: `hash_${fetchId}`,
        sourceType: 'web',
        isPublicAccess: true,
      };

      await db.query(
        `INSERT INTO autonomy_evidence (
          id, action_id, source_id, url, retrieved_at, content_hash, source_type,
          is_public_access, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())`,
        [
          uuidv4(),
          spec.actionId,
          evidence.sourceId,
          url,
          evidence.retrievedAt,
          evidence.contentHash,
          evidence.sourceType,
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
        id, action_id, text, status, confidence, support_source_ids, derived_from_action_ids
      ) VALUES ($1, $2, $3, $4, $5, $6, $7)`,
      [
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

    result.observations.specialistId = specialist.specialistId;
    result.observations.role = specialist.role;
    result.observations.budget = specialist.budget;
    result.createdArtifacts.push(specialist.specialistId);
    result.observations.status = 'specialist_activated';
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
