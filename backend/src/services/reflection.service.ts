/**
 * Reflection Service
 * ==================
 * Generates reflection summaries when loops are detected.
 * Stores reflections in memory so planner can learn from past failures.
 */

import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/client';
import { LoopDetectionResult, ActionHistory } from './loop-detector.service';

export interface Reflection {
  id: string;
  goalId: string;
  loopDetectionId?: string;
  summary: string;
  loopType?: string;
  streak?: number;
  failurePattern: string;
  suggestedStrategy: string;
  confidence: number;
  createdAt: Date;
}

export class ReflectionService {
  /**
   * Generate a reflection when a loop is detected
   * Produces a compact, actionable summary of why the loop occurred
   * and what strategy might break it
   */
  generateReflection(
    goalId: string,
    loopDetection: LoopDetectionResult,
    actionHistory: ActionHistory[],
    loopDetectionId?: string
  ): Reflection {
    const reflection: Reflection = {
      id: uuidv4(),
      goalId,
      loopDetectionId,
      loopType: loopDetection.loopType,
      streak: loopDetection.streak,
      confidence: 0,
      createdAt: new Date(),
      summary: '',
      failurePattern: '',
      suggestedStrategy: '',
    };

    if (loopDetection.loopType === 'identical_action_repeat') {
      this.analyzeIdenticalRepeat(reflection, actionHistory, loopDetection);
    } else if (loopDetection.loopType === 'no_progress_streak') {
      this.analyzeNoProgress(reflection, actionHistory, loopDetection);
    }

    // Only store high-confidence reflections
    reflection.confidence = Math.min(0.95, 0.6 + loopDetection.streak * 0.05);

    return reflection;
  }

  /**
   * Analyze identical action repeat loop
   */
  private analyzeIdenticalRepeat(
    reflection: Reflection,
    history: ActionHistory[],
    detection: LoopDetectionResult
  ): void {
    if (history.length < 3) return;

    const recent = history.slice(-3);
    const action = recent[0];
    const actionArgs = JSON.stringify(action.args);

    reflection.failurePattern = `${action.actionType} was repeated ${detection.streak} times with args: ${actionArgs}`;

    reflection.summary = `LOOP: Identical action repeat (${detection.streak}x)
Action type: ${action.actionType}
Arguments: ${actionArgs}
Outcome: Blocked every time, zero artifacts created`;

    // Suggest different strategy based on action type - VERY SPECIFIC
    if (action.actionType === 'web_search' && actionArgs.includes('query') === false) {
      reflection.suggestedStrategy = 'ERROR: web_search needs args.query parameter. TRY: {"action_type": "evaluate_progress", "args": {}} OR {"action_type": "fetch_page", "args": {"url": "..."}}';
    } else if (action.actionType === 'web_search') {
      reflection.suggestedStrategy = 'web_search with that query failed. TRY: {"action_type": "evaluate_progress", "objective": "check progress", "args": {}}';
    } else if (action.actionType === 'fetch_page' && actionArgs.includes('url') === false) {
      reflection.suggestedStrategy = 'ERROR: fetch_page needs args.url parameter. TRY: {"action_type": "web_search", "objective": "search for content", "args": {"query": "your search terms"}}';
    } else if (action.actionType === 'fetch_page') {
      reflection.suggestedStrategy = 'fetch_page with that URL returned no useful content. TRY: {"action_type": "web_search", "objective": "find better sources", "args": {"query": "topic name"}}';
    } else if (action.actionType === 'evaluate_progress') {
      reflection.suggestedStrategy = 'evaluate_progress with no data changed nothing. TRY: {"action_type": "web_search", "objective": "gather initial evidence", "args": {"query": "search term"}}';
    } else if (action.actionType === 'spawn_specialist') {
      reflection.suggestedStrategy = 'spawn_specialist failed due to missing parameters. TRY: {"action_type": "evaluate_progress", "objective": "check current state", "args": {}}';
    } else {
      reflection.suggestedStrategy = `CHANGE ACTION TYPE: Do not use ${action.actionType} again. TRY: "evaluate_progress" or "web_search" with proper arguments`;
    }
  }

  /**
   * Analyze no-progress streak loop
   */
  private analyzeNoProgress(
    reflection: Reflection,
    history: ActionHistory[],
    detection: LoopDetectionResult
  ): void {
    if (history.length < 5) return;

    const recent = history.slice(-5);
    const actionTypes = recent.map((h) => h.actionType);
    const uniqueTypes = new Set(actionTypes).size;

    reflection.failurePattern = `No progress: ${detection.streak} consecutive actions with zero new artifacts`;

    reflection.summary = `LOOP: No progress detected
Actions: ${actionTypes.join(' → ')}
Consecutive steps: ${detection.streak}
New artifacts: 0
Action variety: ${uniqueTypes === 1 ? 'single type repeated' : 'multiple types, all failed'}`;

    if (uniqueTypes === 1) {
      reflection.suggestedStrategy =
        'Same action type is not working. Try a completely different action (search vs fetch vs analyze)';
    } else {
      reflection.suggestedStrategy =
        'Multiple action types failed to produce progress. Goal may be unapproachable or already resolved';
    }
  }

  /**
   * Store reflection in database (autonomy_memory table)
   */
  async storeReflection(reflection: Reflection): Promise<void> {
    try {
      const actionId = undefined; // Reflection is goal-level, not action-level
      await db.query(
        `INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at)
         VALUES ($1, $2, $3, NOW(), NOW())`,
        [
          reflection.id,
          actionId,
          JSON.stringify({
            type: 'reflection',
            goalId: reflection.goalId,
            loopType: reflection.loopType,
            streak: reflection.streak,
            failurePattern: reflection.failurePattern,
            suggestedStrategy: reflection.suggestedStrategy,
            confidence: reflection.confidence,
            summary: reflection.summary,
          }),
        ]
      );
    } catch (error) {
      console.error(`Failed to store reflection: ${error}`);
      // Don't throw - reflection storage failure shouldn't block autonomy loop
    }
  }

  /**
   * Retrieve recent reflections for a goal
   * Useful for planner context
   */
  async getRecentReflections(goalId: string, limit: number = 3): Promise<Reflection[]> {
    try {
      const result = await db.query(
        `SELECT id, content, created_at FROM autonomy_memory
         WHERE content->>'type' = 'reflection'
         AND content->>'goalId' = $1
         ORDER BY created_at DESC
         LIMIT $2`,
        [goalId, limit]
      );

      return result.rows.map((row) => {
        const content = row.content;
        return {
          id: row.id,
          goalId,
          summary: content.summary,
          loopType: content.loopType,
          streak: content.streak,
          failurePattern: content.failurePattern,
          suggestedStrategy: content.suggestedStrategy,
          confidence: content.confidence,
          createdAt: row.created_at,
        };
      });
    } catch (error) {
      console.error(`Failed to retrieve reflections: ${error}`);
      return [];
    }
  }

  /**
   * Format reflection for LLM context
   */
  formatForContext(reflections: Reflection[]): string {
    if (reflections.length === 0) {
      return '';
    }

    const lines = [
      'CRITICAL LEARNINGS FROM PREVIOUS ATTEMPTS:',
      '(Use these to make DIFFERENT decisions this iteration)',
      ''
    ];

    reflections.slice(0, 3).forEach((r, i) => {
      lines.push(`Learning ${i + 1} (confidence: ${(r.confidence * 100).toFixed(0)}%):`);
      lines.push(`  ❌ What FAILED: ${r.failurePattern}`);
      lines.push(`  💡 Try INSTEAD: ${r.suggestedStrategy}`);

      // Add specific guidance based on loop type
      if (r.loopType === 'identical_action_repeat') {
        lines.push(`  ⚠️  The same action was repeated ${r.streak || 3}+ times.`);
        lines.push(`  ✅ MUST choose a DIFFERENT action type this iteration.`);
      } else if (r.loopType === 'no_progress_streak') {
        lines.push(`  ⚠️  No goal progress for ${r.streak || 5} consecutive actions.`);
        lines.push(`  ✅ Must take action that generates NEW evidence or claims.`);
      }
      lines.push('');
    });

    lines.push('CONSTRAINTS TO RESPECT:');
    lines.push('- If previous attempt used web_search, try fetch_page or evaluate_progress instead');
    lines.push('- If previous attempt used evaluate_progress, try web_search or fetch_page');
    lines.push('- Ensure ALL required parameters are provided in your action');
    lines.push('- DIFFERENT action = choose different action_type than before');
    lines.push('');

    return lines.join('\n');
  }
}
