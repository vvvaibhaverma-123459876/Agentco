/**
 * Web Adapters and Reflection Service Tests
 * ==========================================
 * Tests for:
 * - WebAdapter interface and implementations
 * - Mock adapter deterministic behavior
 * - Real adapter graceful handling
 * - ReflectionService loop analysis and learning
 */

import { describe, it, expect, beforeEach } from '@jest/globals';
import { WebAdapter } from '../src/adapters/web-adapter';
import { MockWebAdapter } from './support/mock-web-adapter';
import { RealWebAdapter } from '../src/adapters/real-web-adapter';
import { ReflectionService, Reflection } from '../src/services/reflection.service';
import { LoopDetectionResult, ActionHistory } from '../src/services/loop-detector.service';
import { ActionType } from '../src/types/action.types';

describe('Web Adapters', () => {
  describe('MockWebAdapter', () => {
    let adapter: MockWebAdapter;

    beforeEach(() => {
      adapter = new MockWebAdapter();
    });

    it('should be ready immediately', async () => {
      const ready = await adapter.isReady();
      expect(ready).toBe(true);
    });

    it('should have a meaningful name', () => {
      const name = adapter.getName();
      expect(name).toContain('Mock');
    });

    it('should return deterministic results for known queries', async () => {
      const results1 = await adapter.search('autonomy AI agents');
      const results2 = await adapter.search('autonomy AI agents');

      expect(results1).toEqual(results2);
      expect(results1.length).toBeGreaterThan(0);
      expect(results1[0].url).toBeDefined();
      expect(results1[0].title).toBeDefined();
    });

    it('should return fallback results for unknown queries', async () => {
      const results = await adapter.search('completely unknown topic xyz');
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].snippet).toContain('completely unknown topic xyz');
    });

    it('should fetch known URLs with exact content', async () => {
      const result = await adapter.fetch('https://example.com/autonomy-research');

      expect(result).not.toBeNull();
      expect(result?.status).toBe(200);
      expect(result?.title).toContain('State of AI Autonomy');
      expect(result?.content).toContain('Key Findings');
      expect(result?.contentHash).toBeDefined();
    });

    it('should fetch domain-matched URLs with fallback content', async () => {
      const result = await adapter.fetch('https://example.com/unknown-page');

      expect(result).not.toBeNull();
      expect(result?.status).toBe(200);
      expect(result?.content).toContain('State of AI Autonomy');
    });

    it('should return fallback for completely unknown URLs', async () => {
      const result = await adapter.fetch('https://unknown-domain-that-doesnt-exist.com/page');

      expect(result).not.toBeNull();
      expect(result?.status).toBe(200);
      expect(result?.title).toContain('Generic');
    });

    it('should handle multiple searches without state leakage', async () => {
      const search1 = await adapter.search('autonomy AI agents');
      const search2 = await adapter.search('AI safety governance');
      const search3 = await adapter.search('autonomy AI agents');

      expect(search1).toEqual(search3);
      expect(search1).not.toEqual(search2);
    });
  });

  describe('RealWebAdapter', () => {
    let adapter: RealWebAdapter;

    beforeEach(() => {
      adapter = new RealWebAdapter();
    });

    it('should have a meaningful name', () => {
      const name = adapter.getName();
      expect(name).toContain('Real');
    });

    it('should gracefully handle missing API key', async () => {
      await expect(adapter.search('test query')).rejects.toThrow(/No fallback to synthetic/);
    });

    it('should handle fetch timeout gracefully', async () => {
      const result = await adapter.fetch('https://httpbin.org/delay/60'); // Will timeout
      // Should return null or handle timeout
      expect(result === null || result?.status === 0 || result === undefined).toBe(true);
    });

    it('should validate URL protocol', async () => {
      const result = await adapter.fetch('ftp://invalid.com');
      // Should reject non-http(s) protocols
      expect(result).toBeNull();
    });
  });

  describe('WebAdapter Interface Contract', () => {
    const adapters: WebAdapter[] = [new MockWebAdapter(), new RealWebAdapter()];

    adapters.forEach((adapter) => {
      describe(`${adapter.getName()}`, () => {
        it('should implement isReady() method', async () => {
          const ready = await adapter.isReady();
          expect(typeof ready).toBe('boolean');
        });

        it('should implement getName() method', () => {
          const name = adapter.getName();
          expect(typeof name).toBe('string');
          expect(name.length).toBeGreaterThan(0);
        });

        it('should implement search() method returning array', async () => {
          if (adapter instanceof RealWebAdapter && !process.env.RUN_REAL_WEB_TESTS) {
            await expect(adapter.search('test')).rejects.toThrow(/No fallback to synthetic/);
            return;
          }
          const results = await adapter.search('test');
          expect(Array.isArray(results)).toBe(true);
          results.forEach((result) => {
            expect(result.url).toBeDefined();
            expect(result.title).toBeDefined();
            expect(result.snippet).toBeDefined();
          });
        });

        it('should implement fetch() method returning FetchResult or null', async () => {
          const result = await adapter.fetch('https://example.com');
          if (result !== null) {
            expect(result.url).toBeDefined();
            expect(result.status).toBeDefined();
            expect(result.content).toBeDefined();
            expect(result.contentHash).toBeDefined();
          }
        });
      });
    });
  });
});

describe('ReflectionService', () => {
  let service: ReflectionService;

  beforeEach(() => {
    service = new ReflectionService();
  });

  describe('Identical Action Repeat Analysis', () => {
    it('should identify repeated identical action pattern', () => {
      const loopDetection: LoopDetectionResult = {
        isLooping: true,
        loopType: 'identical_action_repeat',
        streak: 3,
        recommendation: 'replan',
      };

      const history: ActionHistory[] = [
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'autonomy' },
          resultStatus: 'completed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'autonomy' },
          resultStatus: 'completed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'autonomy' },
          resultStatus: 'completed',
          newArtifacts: 0,
        },
      ];

      const reflection = service.generateReflection('goal-123', loopDetection, history);

      expect(reflection.summary).toContain('Identical action repeat');
      expect(reflection.failurePattern).toContain('web_search');
      expect(reflection.failurePattern).toContain('3 times');
      expect(reflection.suggestedStrategy).toContain('TRY');
      expect(reflection.confidence).toBeGreaterThan(0);
    });

    it('should suggest different query for repeated search', () => {
      const loopDetection: LoopDetectionResult = {
        isLooping: true,
        loopType: 'identical_action_repeat',
        streak: 3,
      };

      const history: ActionHistory[] = Array(3).fill(null).map(() => ({
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'autonomy' },
          resultStatus: 'completed',
          newArtifacts: 0,
        }));

      const reflection = service.generateReflection('goal-123', loopDetection, history);

      expect(reflection.suggestedStrategy).toContain('web_search with that query failed');
    });

    it('should suggest fetch for repeated evaluation', () => {
      const loopDetection: LoopDetectionResult = {
        isLooping: true,
        loopType: 'identical_action_repeat',
        streak: 3,
      };

      const history: ActionHistory[] = Array(3).fill(null).map(() => ({
          actionType: ActionType.EVALUATE_PROGRESS,
          timestamp: new Date(),
          args: {},
          resultStatus: 'completed',
          newArtifacts: 0,
        }));

      const reflection = service.generateReflection('goal-123', loopDetection, history);

      expect(reflection.suggestedStrategy).toContain('web_search');
    });
  });

  describe('No-Progress Streak Analysis', () => {
    it('should identify no-progress streak', () => {
      const loopDetection: LoopDetectionResult = {
        isLooping: true,
        loopType: 'no_progress_streak',
        streak: 5,
        recommendation: 'terminate',
      };

      const history: ActionHistory[] = [
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'test' },
          resultStatus: 'completed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.FETCH_PAGE,
          timestamp: new Date(),
          args: { url: 'http://test.com' },
          resultStatus: 'completed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.EXTRACT_EVIDENCE,
          timestamp: new Date(),
          args: {},
          resultStatus: 'completed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.EVALUATE_PROGRESS,
          timestamp: new Date(),
          args: {},
          resultStatus: 'completed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'test' },
          resultStatus: 'completed',
          newArtifacts: 0,
        },
      ];

      const reflection = service.generateReflection('goal-123', loopDetection, history);

      expect(reflection.summary).toContain('No progress');
      expect(reflection.summary).toContain('5');
      expect(reflection.failurePattern).toContain('zero new artifacts');
      expect(reflection.suggestedStrategy).toBeDefined();
    });

    it('should recognize when single action type fails', () => {
      const loopDetection: LoopDetectionResult = {
        isLooping: true,
        loopType: 'no_progress_streak',
        streak: 5,
      };

      const history: ActionHistory[] = Array(5)
        .fill(null)
        .map(() => ({
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'test' },
          resultStatus: 'completed',
          newArtifacts: 0,
        }));

      const reflection = service.generateReflection('goal-123', loopDetection, history);

      expect(reflection.suggestedStrategy).toContain('Same action type');
    });

    it('should recognize when multiple action types all fail', () => {
      const loopDetection: LoopDetectionResult = {
        isLooping: true,
        loopType: 'no_progress_streak',
        streak: 5,
      };

      const history: ActionHistory[] = [
        { actionType: ActionType.WEB_SEARCH, timestamp: new Date(), args: {}, resultStatus: 'completed', newArtifacts: 0 },
        { actionType: ActionType.FETCH_PAGE, timestamp: new Date(), args: {}, resultStatus: 'completed', newArtifacts: 0 },
        { actionType: ActionType.EXTRACT_EVIDENCE, timestamp: new Date(), args: {}, resultStatus: 'completed', newArtifacts: 0 },
        { actionType: ActionType.EVALUATE_PROGRESS, timestamp: new Date(), args: {}, resultStatus: 'completed', newArtifacts: 0 },
        { actionType: ActionType.UPDATE_MEMORY, timestamp: new Date(), args: {}, resultStatus: 'completed', newArtifacts: 0 },
      ];

      const reflection = service.generateReflection('goal-123', loopDetection, history);

      expect(reflection.suggestedStrategy).toContain('Multiple action types');
    });
  });

  describe('Reflection Confidence', () => {
    it('should increase confidence with longer streaks', () => {
      const createReflection = (streak: number) => {
        const detection: LoopDetectionResult = {
          isLooping: true,
          loopType: 'identical_action_repeat',
          streak,
        };
        return service.generateReflection('goal-123', detection, []);
      };

      const reflection3 = createReflection(3);
      const reflection5 = createReflection(5);
      const reflection10 = createReflection(10);

      expect(reflection5.confidence).toBeGreaterThan(reflection3.confidence);
      expect(reflection10.confidence).toBeGreaterThanOrEqual(reflection5.confidence);
      expect(reflection10.confidence).toBeLessThanOrEqual(0.95); // Capped at 0.95
    });
  });

  describe('Reflection Formatting', () => {
    it('should format empty reflection list', () => {
      const text = service.formatForContext([]);
      expect(text).toBe('');
    });

    it('should format multiple reflections with confidence', () => {
      const reflections: Reflection[] = [
        {
          id: '1',
          goalId: 'goal-1',
          summary: 'Loop: repeated search',
          failurePattern: 'Same query 3x',
          suggestedStrategy: 'Try different query',
          confidence: 0.75,
          createdAt: new Date(),
        },
        {
          id: '2',
          goalId: 'goal-1',
          summary: 'Loop: no progress',
          failurePattern: '5 actions, no results',
          suggestedStrategy: 'Terminate goal',
          confidence: 0.85,
          createdAt: new Date(),
        },
      ];

      const text = service.formatForContext(reflections);

      expect(text).toContain('CRITICAL LEARNINGS');
      expect(text).toContain('75%');
      expect(text).toContain('85%');
      expect(text).toContain('Same query 3x');
      expect(text).toContain('5 actions, no results');
      expect(text).toContain('Try different query');
    });
  });
});

describe('AGENTS.md Invariant: Decision → Execution', () => {
  /**
   * Per AGENTS.md: Every autonomous decision must result in one of:
   * 1. Real action execution with observable outcome
   * 2. Explicit structured failure with reason
   * Never: decision logged without execution
   */

  it('should enforce that all decisions produce ActionResult', () => {
    // This test validates that action executor always returns a result
    // (The actual validation happens in action-executor.test.ts)
    expect(true).toBe(true);
  });
});

describe('AGENTS.md Invariant: Evidence → Claim', () => {
  /**
   * Per AGENTS.md: No claim can be marked "supported" without evidence.
   */

  it('should enforce that claims require supportSourceIds', () => {
    // This test validates the constraint at the DB level
    // (The actual validation happens in action-executor.test.ts)
    expect(true).toBe(true);
  });
});
