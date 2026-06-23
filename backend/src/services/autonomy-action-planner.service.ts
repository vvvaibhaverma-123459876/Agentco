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

import { OpenAI } from 'openai';
import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/client';
import { ActionSpec, ActionType, RiskLevel } from '../types/action.types';
import { LoopDetectionResult } from './loop-detector.service';

export class AutonomyActionPlannerService {
  private openai: OpenAI;

  constructor() {
    this.openai = new OpenAI({
      apiKey: process.env.LLM_API_KEY,
    });
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
    const decision = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'system',
          content: `You are an autonomous research agent. Based on goal progress, decide the NEXT action.
Return JSON with: action_type, objective, args, reasoning.
Action types: search, fetch, extract_evidence, generate_claim, evaluate_progress, terminate.`,
        },
        {
          role: 'user',
          content: prompt,
        },
      ],
      max_tokens: 300,
      temperature: 0.7,
    });

    const content = decision.choices[0]?.message?.content;
    if (!content) {
      throw new Error('LLM returned empty decision');
    }

    // Parse LLM decision
    const actionData = this.parseLLMDecision(content);

    // Convert to ActionSpec
    return this.createActionSpecFromDecision(goalId, actionData);
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
3. When evidence is sufficient, generate claims (MUST be backed by sources)
4. When stuck or looping, terminate instead of repeating`;
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
