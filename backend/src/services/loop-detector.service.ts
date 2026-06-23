/**
 * Loop Detector Service
 * ====================
 * Detects repeated identical actions, no-progress streaks
 * Triggers forced replan or termination instead of silent looping
 */

import { ActionType } from '../types/action.types';

export interface ActionHistory {
  actionType: ActionType;
  timestamp: Date;
  args: Record<string, any>;
  resultStatus: string;
  newArtifacts: number;
}

export interface LoopDetectionResult {
  isLooping: boolean;
  loopType?: 'identical_action_repeat' | 'no_progress_streak' | 'identical_decision';
  streak: number;
  recommendation?: 'replan' | 'terminate' | 'proceed';
}

export class LoopDetectorService {
  private maxIdenticalActionRepeat = 3;
  private maxNoProgressStreak = 5;

  /**
   * Detect if we're in a loop
   */
  detectLoop(actionHistory: ActionHistory[]): LoopDetectionResult {
    if (actionHistory.length < 2) {
      return { isLooping: false, streak: 0 };
    }

    // Check for identical action repetition
    const identicalRepeat = this.checkIdenticalRepeat(actionHistory);
    if (identicalRepeat.isLooping) {
      return identicalRepeat;
    }

    // Check for no-progress streaks
    const noProgress = this.checkNoProgress(actionHistory);
    if (noProgress.isLooping) {
      return noProgress;
    }

    return { isLooping: false, streak: 0 };
  }

  /**
   * Detect if the same action was decided and executed multiple times
   */
  private checkIdenticalRepeat(history: ActionHistory[]): LoopDetectionResult {
    if (history.length < this.maxIdenticalActionRepeat) {
      return { isLooping: false, streak: 0 };
    }

    const recent = history.slice(-this.maxIdenticalActionRepeat);
    const actionTypes = recent.map(a => a.actionType);

    // All identical?
    if (actionTypes.every(t => t === actionTypes[0])) {
      // Are arguments also identical?
      const args = recent.map(a => JSON.stringify(a.args));
      if (args.every(a => a === args[0])) {
        return {
          isLooping: true,
          loopType: 'identical_action_repeat',
          streak: recent.length,
          recommendation: 'replan',
        };
      }
    }

    return { isLooping: false, streak: 0 };
  }

  /**
   * Detect if actions are being executed but producing no new artifacts
   */
  private checkNoProgress(history: ActionHistory[]): LoopDetectionResult {
    if (history.length < this.maxNoProgressStreak) {
      return { isLooping: false, streak: 0 };
    }

    const recent = history.slice(-this.maxNoProgressStreak);
    const noNewArtifacts = recent.filter(a => a.newArtifacts === 0);

    if (noNewArtifacts.length === recent.length) {
      return {
        isLooping: true,
        loopType: 'no_progress_streak',
        streak: recent.length,
        recommendation: 'terminate',
      };
    }

    return { isLooping: false, streak: 0 };
  }

  /**
   * Format loop detection for logging
   */
  formatDetection(result: LoopDetectionResult): string {
    if (!result.isLooping) {
      return 'No loop detected';
    }

    return `LOOP DETECTED: ${result.loopType} (streak: ${result.streak}). Recommendation: ${result.recommendation}`;
  }
}
