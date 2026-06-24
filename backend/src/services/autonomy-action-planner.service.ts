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
   * Call OpenAI API using native fetch
   */
  private async callOpenAI(messages: Array<{ role: string; content: string }>): Promise<string> {
    const apiUrl = 'https://api.openai.com/v1/chat/completions';

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
            model: 'gpt-4o-mini',
            messages,
            max_tokens: 400,
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
   */
  async planNextAction(
    goalId: string,
    currentState: {
      goalText: string;
      claimsGenerated: number;
      evidenceCount: number;
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

    // Use LLM to decide next action
    const prompt = this.buildDecisionPrompt(currentState);
    const systemPrompt = this.buildSystemPrompt();

    const content = await this.callOpenAI([
      {
        role: 'system',
        content: systemPrompt,
      },
      {
        role: 'user',
        content: prompt,
      },
    ]);

    // Parse LLM decision
    const actionData = this.parseLLMDecision(content);

    // Convert to ActionSpec
    return this.createActionSpecFromDecision(goalId, actionData);
  }

  /**
   * Build system prompt with specialist context
   */
  private buildSystemPrompt(): string {
    return `You are an autonomous research agent with access to specialized teams. Based on goal progress, decide the NEXT action.

Available action types:
- search, fetch, extract_evidence, generate_claim, update_memory, evaluate_progress, terminate
- spawn_specialist: Delegate work to a specialized agent

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

WHEN TO SPAWN A SPECIALIST:
1. You have evidence already (don't spawn empty)
2. Specialist role matches your current need
3. You want deeper analysis than inline execution

Return JSON with: action_type, objective, args, reasoning.
For spawn_specialist: include role, objective, and optional budget.`;
  }

  /**
   * Build decision prompt from current state
   */
  private buildDecisionPrompt(state: {
    goalText: string;
    claimsGenerated: number;
    evidenceCount: number;
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

    return {
      actionId: uuidv4(),
      actionType,
      goalId,
      objective: decision.objective,
      args: decision.args,
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
}
