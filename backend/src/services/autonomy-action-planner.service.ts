/**
 * Autonomy Action Planner Service
 * ===============================
 * Decides what action to take next given:
 * - Current goal
 * - Available evidence
 * - Claims generated so far
 * - Loop detection results
 *
 * Uses LLM to decide, returns typed ActionSpec
 */

import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/client';
import { ActionSpec, ActionType, RiskLevel } from '../types/action.types';
import { LoopDetectionResult } from './loop-detector.service';

export class AutonomyActionPlannerService {
  private apiKey: string;

  constructor() {
    this.apiKey = process.env.LLM_API_KEY || '';
    if (!this.apiKey) {
      throw new Error('LLM_API_KEY environment variable not set');
    }
  }

  /**
   * Validate required parameters for each action type
   */
  private validateActionParameters(actionType: string, args: any): { valid: boolean; error?: string } {
    const requiredParams: Record<string, string[]> = {
      web_search: ['query'],
      fetch_page: ['url'],
      extract_evidence: ['content', 'source'],
      generate_claim: ['claimText', 'supportSourceIds'],
      update_memory: ['content'],
      evaluate_progress: [],
      spawn_specialist: ['role', 'objective', 'goalId'],
      replan: [],
      terminate: [],
    };

    const required = requiredParams[actionType] || [];
    for (const param of required) {
      if (!args || !(param in args) || !args[param]) {
        return {
          valid: false,
          error: `Missing required parameter: "${param}" for action type "${actionType}"`,
        };
      }
    }

    return { valid: true };
  }

  /**
   * Call OpenAI API using native fetch with parameter validation
   */
  private async callOpenAI(
    messages: Array<{ role: string; content: string }>,
    attemptNumber: number = 0,
    previousError?: string
  ): Promise<string> {
    // Use configured LLM provider, default to OpenAI
    const baseUrl = process.env.LLM_BASE_URL || 'https://api.openai.com/v1';
    const apiUrl = `${baseUrl}/chat/completions`;

    // Add error feedback to messages on retry
    let messagesWithFeedback = [...messages];
    if (attemptNumber > 0 && previousError) {
      messagesWithFeedback = [
        ...messages.slice(0, -1),
        {
          role: 'user',
          content: `${messages[messages.length - 1].content}\n\nIMPORTANT: Your previous response had an issue: ${previousError}\nPlease provide a corrected response with all required parameters.`,
        },
      ];
    }

    let lastError;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);

        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: process.env.LLM_MODEL_DEFAULT || 'gpt-4o-mini',
            messages: messagesWithFeedback,
            max_tokens: 500,
            temperature: 0.7,
          }),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`API error: ${response.status} ${response.statusText}`);
        }

        const data: any = await response.json();
        const content = data.choices?.[0]?.message?.content;
        if (!content) {
          throw new Error('Empty response from API');
        }

        return content;
      } catch (error) {
        lastError = error;
        if (attempt < 2) {
          const delay = Math.pow(2, attempt) * 1000;
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    throw new Error(`LLM call failed after 3 retries: ${lastError}`);
  }

  /**
   * Evaluate if a specialist could help with the current goal
   */
  private evaluateSpecialistFit(
    goalText: string,
    evidenceCount: number,
    claimsGenerated: number
  ): {
    shouldConsider: boolean;
    recommendedRoles: string[];
  } {
    const goal = goalText.toLowerCase();
    const recommended: string[] = [];

    // Don't recommend if no evidence yet
    if (evidenceCount === 0) {
      return { shouldConsider: false, recommendedRoles: [] };
    }

    // Pattern matching for specialist recommendation
    if (goal.includes('code') || goal.includes('bug') || goal.includes('review')) {
      recommended.push('code_reviewer');
    }
    if (goal.includes('pdf') || goal.includes('document') || goal.includes('spec')) {
      recommended.push('doc_analyzer');
    }
    if (goal.includes('opinion') || goal.includes('sentiment') || goal.includes('bias')) {
      recommended.push('sentiment_analyzer');
    }
    if (goal.includes('compare') || goal.includes('vs') || goal.includes('difference')) {
      recommended.push('comparative_analyst');
    }
    if (goal.includes('time') || goal.includes('timeline') || goal.includes('history')) {
      recommended.push('temporal_analyst');
    }
    if (goal.includes('quality') || goal.includes('standard') || goal.includes('compliance')) {
      recommended.push('quality_auditor');
    }
    if (goal.includes('data') || goal.includes('statistic') || goal.includes('metric')) {
      recommended.push('data_analyst');
    }
    if (goal.includes('credibility') || goal.includes('source') || goal.includes('valid')) {
      recommended.push('source_validator');
    }
    if (goal.includes('contradiction') || goal.includes('conflict')) {
      recommended.push('contradiction_hunter');
    }
    if (goal.includes('synthesis') || goal.includes('summary') || goal.includes('conclusion')) {
      recommended.push('synthesizer');
    }

    // Default recommendation if goal is generic
    if (recommended.length === 0) {
      recommended.push('background_researcher');
    }

    return {
      shouldConsider: recommended.length > 0,
      recommendedRoles: recommended.slice(0, 3), // Top 3 recommendations
    };
  }

  /**
   * Decide the next action given goal context and loop status
   * Includes parameter validation and fallback strategy
   */
  async planNextAction(
    goalId: string,
    currentState: {
      goalText: string;
      claimsGenerated: number;
      evidenceCount: number;
      evidenceSources?: Array<{ sourceId: string; url: string; snippet: string }>;
      loopDetection: LoopDetectionResult;
      reflectionContext?: string;
      previousActions: Array<{ type: ActionType; result: string }>;
    }
  ): Promise<ActionSpec> {
    // If loop detected, force replan or termination
    if (currentState.loopDetection.isLooping) {
      if (currentState.loopDetection.recommendation === 'terminate') {
        return this.createTerminateAction(
          goalId,
          `Loop detected: ${currentState.loopDetection.loopType}. Terminating autonomy loop.`
        );
      } else if (currentState.loopDetection.recommendation === 'replan') {
        return this.createReplanAction(goalId, currentState.loopDetection);
      }
    }

    // Use LLM to decide next action with parameter validation and retry
    const prompt = this.buildDecisionPrompt(currentState);
    const systemPrompt = this.buildSystemPrompt();

    let actionData: any = null;
    let lastValidationError: string | undefined;
    let attemptCount = 0;

    // Try up to 2 times with feedback
    while (attemptCount < 2 && !actionData) {
      try {
        const content = await this.callOpenAI(
          [
            {
              role: 'system',
              content: systemPrompt,
            },
            {
              role: 'user',
              content: prompt,
            },
          ],
          attemptCount,
          lastValidationError
        );

        // Parse LLM decision
        actionData = this.parseLLMDecision(content);

        // Validate parameters
        if (actionData && actionData.action_type) {
          const validation = this.validateActionParameters(actionData.action_type, actionData.args);
          if (!validation.valid) {
            lastValidationError = validation.error;
            actionData = null;
            attemptCount++;
            console.log(`Parameter validation failed (attempt ${attemptCount}): ${validation.error}`);
          }
        }
      } catch (error) {
        console.error(`LLM call error: ${error}`);
        throw error;
      }
    }

    // If LLM failed to provide valid parameters after retries, use fallback
    if (!actionData) {
      console.log(`Fallback: LLM failed to generate valid parameters after ${attemptCount} attempts. Using safe default.`);
      return this.createFallbackAction(goalId, lastValidationError);
    }

    // Convert to ActionSpec
    return this.createActionSpecFromDecision(goalId, actionData);
  }

  /**
   * Build system prompt with specialist context and detailed examples
   */
  private buildSystemPrompt(): string {
    return `You are an autonomous research agent with access to specialized teams. Based on goal progress, decide the NEXT action.

CRITICAL: Return valid JSON with ALL required parameters. Missing parameters will cause action to be BLOCKED.

Available action types with REQUIRED parameters:

1. web_search [REQUIRED: query]
   Example: {"action_type": "web_search", "objective": "Find articles on topic", "args": {"query": "AI safety trends 2026"}}

2. fetch_page [REQUIRED: url]
   Example: {"action_type": "fetch_page", "objective": "Read the article", "args": {"url": "https://example.com/article"}}

3. extract_evidence [REQUIRED: content, source]
   Example: {"action_type": "extract_evidence", "objective": "Extract key points", "args": {"content": "text...", "source": "url"}}

4. generate_claim [REQUIRED: claimText, supportSourceIds, supportSnippets]
   Example: {"action_type": "generate_claim", "objective": "Create supported claim", "args": {"claimText": "claim text", "supportSourceIds": ["source1", "source2"], "supportSnippets": ["exact quote from the source evidence"]}}

5. update_memory [REQUIRED: content]
   Example: {"action_type": "update_memory", "objective": "Store learning", "args": {"content": {"type": "learning", "text": "..."}}}

6. evaluate_progress [No required parameters]
   Example: {"action_type": "evaluate_progress", "objective": "Check progress", "args": {}}

7. spawn_specialist [REQUIRED: role, objective, goalId]
   Example: {"action_type": "spawn_specialist", "objective": "delegate work", "args": {"role": "researcher", "objective": "find more sources", "goalId": "goal-uuid"}}

8. replan [No required parameters]
   Example: {"action_type": "replan", "objective": "Change strategy", "args": {}}

9. terminate [No required parameters]
   Example: {"action_type": "terminate", "objective": "End autonomy", "args": {}}

SPECIALIST ROLES (delegate when you need specialized analysis):
- researcher: General research (search, fetch, extract)
- data_analyst: Statistical analysis and pattern detection
- source_validator: Verify source credibility and bias
- evidence_linker: Cross-reference evidence patterns
- contradiction_hunter: Find contradictions in claims
- synthesizer: Combine claims into conclusions
- background_researcher: Deep historical/contextual research
- code_reviewer: Code analysis and bug detection
- doc_analyzer: Extract from PDFs and specifications
- sentiment_analyzer: Analyze opinion and bias
- comparative_analyst: Compare entities across dimensions
- temporal_analyst: Timeline and causality analysis
- quality_auditor: Compliance and standards auditing
- fetcher: Read-only page fetching
- claim_validator: Validate claims with evidence backing
- evidence_summarizer: Summarize evidence
- reviewer: Progress evaluation

CRITICAL RULES:
1. web_search MUST include args.query (NOT just objective)
2. fetch_page MUST include args.url (NOT just objective)
3. spawn_specialist MUST include role, objective, AND goalId
4. Return ONLY valid JSON, no other text
5. Every required parameter MUST be present and non-empty

Return JSON with: action_type, objective, args, reasoning.`;
  }

  /**
   * Build decision prompt from current state
   */
  private buildDecisionPrompt(state: {
    goalText: string;
    claimsGenerated: number;
    evidenceCount: number;
    evidenceSources?: Array<{ sourceId: string; url: string; snippet: string }>;
    loopDetection: LoopDetectionResult;
    reflectionContext?: string;
    previousActions: Array<{ type: ActionType; result: string }>;
  }): string {
    let prompt = `
Goal: ${state.goalText}

Progress:
- Claims generated: ${state.claimsGenerated}
- Evidence collected: ${state.evidenceCount}
- Previous actions: ${state.previousActions.map(a => `${a.type}(${a.result})`).join(', ') || 'none'}

Loop status: ${state.loopDetection.isLooping ? `DETECTED: ${state.loopDetection.loopType}` : 'clear'}`;

    // Include evidence details if available
    if (state.evidenceSources && state.evidenceSources.length > 0) {
      prompt += `

Available Evidence Sources (USE THESE IDs FOR CLAIMS):`;
      state.evidenceSources.forEach((src, i) => {
        prompt += `\n${i + 1}. [${src.sourceId}] ${src.url}\n   Snippet: ${src.snippet?.substring(0, 100) || 'N/A'}`;
      });
      prompt += `\n\nYou can now generate claims using these source IDs in supportSourceIds parameter.`;
    }

    if (state.reflectionContext) {
      prompt += `

${state.reflectionContext}

Given these learnings from previous attempts, what is the NEXT ACTION to take? Choose differently from what you've tried before.`;
    } else {
      prompt += `

What is the next action to take?
Consider:
1. If no evidence yet, search for relevant information
2. If evidence exists, fetch specific pages and extract details
3. If you have evidence but need specialized analysis, consider spawning a specialist
4. When evidence is sufficient, generate claims (MUST be backed by sources)
5. When stuck or looping, terminate instead of repeating`;
    }

    // Add specialist recommendation if evidence exists
    if (state.evidenceCount > 0) {
      const specialistFit = this.evaluateSpecialistFit(state.goalText, state.evidenceCount, state.claimsGenerated);
      if (specialistFit.shouldConsider) {
        prompt += `

SPECIALIST OPPORTUNITY: Based on your goal, consider delegating to:
- ${specialistFit.recommendedRoles.join('\n- ')}

Use spawn_specialist action with role and objective if you want to delegate.`;
      }
    }

    prompt += `

Decide now:
    `;

    return prompt;
  }

  /**
   * Parse LLM decision from content
   */
  private parseLLMDecision(
    content: string
  ): {
    actionType: string;
    objective: string;
    args: Record<string, any>;
    reasoning: string;
  } {
    try {
      // Try to extract JSON from content
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (!jsonMatch) {
        throw new Error('No JSON found in LLM response');
      }

      const parsed = JSON.parse(jsonMatch[0]);
      return {
        actionType: parsed.action_type || 'evaluate_progress',
        objective: parsed.objective || '',
        args: parsed.args || {},
        reasoning: parsed.reasoning || '',
      };
    } catch {
      // Fallback: default to evaluate_progress if parsing fails
      return {
        actionType: 'evaluate_progress',
        objective: 'Evaluate current progress',
        args: {},
        reasoning: 'LLM decision parsing failed, using safe default',
      };
    }
  }

  /**
   * Convert LLM decision to ActionSpec
   */
  private createActionSpecFromDecision(
    goalId: string,
    decision: {
      actionType: string;
      objective: string;
      args: Record<string, any>;
      reasoning: string;
    }
  ): ActionSpec {
    const actionType = this.normalizeActionType(decision.actionType);

    // For spawn_specialist, ensure args has real goalId and objective
    let args = decision.args;
    if (actionType === ActionType.SPAWN_SPECIALIST) {
      args = {
        ...args,
        goalId,
        objective: args.objective || decision.objective,
      };
    }

    return {
      actionId: uuidv4(),
      actionType,
      goalId,
      objective: decision.objective,
      args,
      successCriteria: this.getSuccessCriteria(actionType),
      riskLevel: RiskLevel.LOW,
      decidedBy: 'autonomy_planner',
      decidedAt: new Date(),
      reasoning: decision.reasoning,
    };
  }

  /**
   * Normalize action type from LLM output
   */
  private normalizeActionType(type: string): ActionType {
    const normalized = type.toLowerCase().replace(/[_\s]/g, '_');

    switch (normalized) {
      case 'search':
      case 'web_search':
        return ActionType.WEB_SEARCH;
      case 'fetch':
      case 'fetch_page':
        return ActionType.FETCH_PAGE;
      case 'extract':
      case 'extract_evidence':
        return ActionType.EXTRACT_EVIDENCE;
      case 'claim':
      case 'generate_claim':
        return ActionType.GENERATE_CLAIM;
      case 'memory':
      case 'update_memory':
        return ActionType.UPDATE_MEMORY;
      case 'evaluate':
      case 'evaluate_progress':
        return ActionType.EVALUATE_PROGRESS;
      case 'spawn':
      case 'spawn_specialist':
        return ActionType.SPAWN_SPECIALIST;
      case 'terminate':
        return ActionType.TERMINATE;
      default:
        return ActionType.EVALUATE_PROGRESS;
    }
  }

  /**
   * Get success criteria for an action type
   */
  private getSuccessCriteria(actionType: ActionType): string[] {
    switch (actionType) {
      case ActionType.WEB_SEARCH:
        return [
          'Search query recorded',
          'Search decision documented',
        ];
      case ActionType.FETCH_PAGE:
        return [
          'Page URL is accessible',
          'Page content retrieved and stored',
        ];
      case ActionType.EXTRACT_EVIDENCE:
        return [
          'Evidence extracted from content',
          'Evidence stored in database',
        ];
      case ActionType.GENERATE_CLAIM:
        return [
          'Claim is backed by at least one evidence source',
          'Claim confidence is documented',
          'Claim stored in database',
        ];
      case ActionType.EVALUATE_PROGRESS:
        return [
          'Progress metrics calculated',
          'Next step hint provided',
        ];
      case ActionType.SPAWN_SPECIALIST:
        return [
          'Specialist role validated',
          'Budget allocated',
          'Specialist instance created',
        ];
      case ActionType.TERMINATE:
        return ['Autonomy loop terminated with reason'];
      default:
        return [];
    }
  }

  /**
   * Create terminate action
   */
  private createTerminateAction(goalId: string, reason: string): ActionSpec {
    return {
      actionId: uuidv4(),
      actionType: ActionType.TERMINATE,
      goalId,
      objective: 'Terminate autonomy loop',
      args: { reason },
      successCriteria: ['Loop terminated cleanly'],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'loop_detector',
      decidedAt: new Date(),
      reasoning: reason,
    };
  }

  /**
   * Create replan action
   */
  private createReplanAction(
    goalId: string,
    loopDetection: LoopDetectionResult
  ): ActionSpec {
    return {
      actionId: uuidv4(),
      actionType: ActionType.REPLAN,
      goalId,
      objective: 'Replan due to loop detection',
      args: { loopType: loopDetection.loopType, streak: loopDetection.streak },
      successCriteria: ['New plan generated', 'Next action decided'],
      riskLevel: RiskLevel.MEDIUM,
      decidedBy: 'loop_detector',
      decidedAt: new Date(),
      reasoning: `Loop detected: ${loopDetection.loopType} (${loopDetection.streak} iterations)`,
    };
  }

  /**
   * Create fallback action when LLM fails to provide valid parameters
   */
  private createFallbackAction(goalId: string, reason?: string): ActionSpec {
    return {
      actionId: uuidv4(),
      actionType: ActionType.EVALUATE_PROGRESS,
      goalId,
      objective: 'Safe fallback: Evaluate current progress',
      args: {},
      successCriteria: ['Progress metrics calculated', 'Status updated'],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'autonomy_planner_fallback',
      decidedAt: new Date(),
      reasoning: `LLM parameter validation failed: ${reason || 'Unknown error'}. Using safe default action.`,
    };
  }
}
