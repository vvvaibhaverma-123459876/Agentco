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

    reflection.failurePattern = `Repeated ${action.actionType} with args ${JSON.stringify(action.args)} ${detection.streak} times`;

    reflection.summary = `LOOP: Identical action repeat
Action: ${action.actionType}(${JSON.stringify(action.args).substring(0, 50)})
Repeated: ${detection.streak} times
Result: No new artifacts each time`;

    // Suggest different strategy based on action type
    if (action.actionType === 'web_search') {
      reflection.suggestedStrategy =
        'Try different search query terms, or use FETCH_PAGE directly if you have a URL';
    } else if (action.actionType === 'fetch_page') {
      reflection.suggestedStrategy =
        'Fetched page may not have useful content. Try WEB_SEARCH with different query terms';
    } else if (action.actionType === 'extract_evidence' || action.actionType === 'evaluate_progress') {
      reflection.suggestedStrategy =
        'Evidence extraction produced nothing new. Gather more evidence with WEB_SEARCH or FETCH_PAGE';
    } else {
      reflection.suggestedStrategy =
        'Try a different action type. Current approach is not producing results';
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

    const lines = ['## Recent Learnings from This Goal:'];
    reflections.forEach((r, i) => {
      lines.push(`\n### Learning ${i + 1} (confidence: ${(r.confidence * 100).toFixed(0)}%)`);
      lines.push(`Pattern: ${r.failurePattern}`);
      lines.push(`Suggestion: ${r.suggestedStrategy}`);
    });

    return lines.join('\n');
  }
}
