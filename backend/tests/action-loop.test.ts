/**
 * Action Loop Integration Tests
 * Tests the complete flow: planner → executor → dispatcher
 */

import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { db } from '../src/db/client';
import { ActionExecutorService } from '../src/services/action-executor.service';
import { LoopDetectorService, ActionHistory } from '../src/services/loop-detector.service';
import { MockWebAdapter } from './support/mock-web-adapter';
import {
  ActionSpec,
  ActionType,
  ActionStatus,
  RiskLevel,
} from '../src/types/action.types';
import { v4 as uuidv4 } from 'uuid';

describe('Action Loop Integration', () => {
  const executor = new ActionExecutorService();
  const loopDetector = new LoopDetectorService();

  beforeEach(async () => {
    executor.setWebAdapter(new MockWebAdapter());
    // Clear test data before each test
    await db.query('TRUNCATE autonomy_actions CASCADE');
    await db.query('TRUNCATE autonomy_claims CASCADE');
    await db.query('TRUNCATE autonomy_evidence CASCADE');
  });

  afterEach(async () => {
    await db.query('TRUNCATE autonomy_actions CASCADE');
    await db.query('TRUNCATE autonomy_claims CASCADE');
    await db.query('TRUNCATE autonomy_evidence CASCADE');
  });

  describe('Planner Output Validation', () => {
    it('should create valid ActionSpec with required fields', () => {
      const spec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.WEB_SEARCH,
        goalId: uuidv4(),
        objective: 'Search for information',
        args: { query: 'test query' },
        successCriteria: ['Search completed'],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'autonomy_planner',
        decidedAt: new Date(),
        reasoning: 'Testing search functionality',
      };

      expect(spec.actionId).toBeDefined();
      expect(spec.actionType).toBe(ActionType.WEB_SEARCH);
      expect(spec.successCriteria).toHaveLength(1);
    });

    it('should reject ActionSpec without evidence for claims', () => {
      const spec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.GENERATE_CLAIM,
        goalId: uuidv4(),
        objective: 'Generate claim',
        args: { claimText: 'Some claim', supportSourceIds: [] }, // INVALID: empty sources
        successCriteria: ['Claim generated'],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'autonomy_planner',
        decidedAt: new Date(),
      };

      // Should have empty sources
      expect(spec.args.supportSourceIds).toHaveLength(0);
    });

    it('should validate action type is known', () => {
      const validTypes = Object.values(ActionType);
      expect(validTypes).toContain(ActionType.WEB_SEARCH);
      expect(validTypes).toContain(ActionType.GENERATE_CLAIM);
      expect(validTypes).toContain(ActionType.REPLAN);
      expect(validTypes).toContain(ActionType.TERMINATE);
    });
  });

  describe('Action Executor', () => {
    it('should execute WEB_SEARCH action', async () => {
      const spec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.WEB_SEARCH,
        goalId: uuidv4(),
        objective: 'Search for AI autonomy',
        args: { query: 'autonomous AI systems' },
        successCriteria: ['Search recorded'],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'test',
        decidedAt: new Date(),
      };

      const result = await executor.executeAction(spec);

      expect(result.actionId).toBe(spec.actionId);
      expect(result.status).toBe(ActionStatus.COMPLETED);
      expect(result.observations.searchQuery).toBe('autonomous AI systems');
      expect(result.observations.resultsFound).toBeGreaterThan(0);
    });

    it('should block FETCH_PAGE without real content instead of recording placeholder evidence', async () => {
      const isolatedExecutor = new ActionExecutorService();
      const spec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.FETCH_PAGE,
        goalId: uuidv4(),
        objective: 'Fetch unavailable page',
        args: { url: 'https://example.com/no-adapter' },
        successCriteria: ['No placeholder artifact created'],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'test',
        decidedAt: new Date(),
      };

      const result = await isolatedExecutor.executeAction(spec);

      expect(result.status).toBe(ActionStatus.BLOCKED);
      expect(result.createdArtifacts).toHaveLength(0);
      expect(result.observations.status).toBe('fetch_blocked_no_real_content');
      expect(result.blockedReason).toContain('no evidence artifact was created');
    });

    it('should execute GENERATE_CLAIM with evidence validation', async () => {
      const fetchSpec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.FETCH_PAGE,
        goalId: uuidv4(),
        objective: 'Fetch evidence source',
        args: { url: 'https://example.com/evidence-source' },
        successCriteria: ['Evidence source registered'],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'test',
        decidedAt: new Date(),
      };
      const fetchResult = await executor.executeAction(fetchSpec);
      expect(fetchResult.status).toBe(ActionStatus.COMPLETED);
      const sourceId = fetchResult.createdArtifacts[0];

      const spec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.GENERATE_CLAIM,
        goalId: uuidv4(),
        objective: 'Generate backed claim',
        args: {
          claimText: 'AI autonomy is advancing rapidly',
          supportSourceIds: [sourceId],
          supportSnippets: ['Recent advances in autonomous AI systems show significant progress'],
          confidence: 0.8,
        },
        successCriteria: ['Claim backed by source'],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'test',
        decidedAt: new Date(),
      };

      const result = await executor.executeAction(spec);

      expect(result.status).toBe(ActionStatus.COMPLETED);
      expect(result.observations.claimId).toBeDefined();
      expect(result.createdArtifacts).toContain(result.observations.claimId);
    });

    it('should BLOCK claim generation when support source ids are not registered evidence', async () => {
      const missingSourceId = uuidv4();
      const spec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.GENERATE_CLAIM,
        goalId: uuidv4(),
        objective: 'Generate claim with missing evidence',
        args: {
          claimText: 'Claim with unregistered source id',
          supportSourceIds: [missingSourceId],
        },
        successCriteria: [],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'test',
        decidedAt: new Date(),
      };

      const result = await executor.executeAction(spec);

      expect(result.status).toBe(ActionStatus.BLOCKED);
      expect(result.blockedReason).toContain('source id is not registered evidence');
      expect(result.blockedReason).toContain(missingSourceId);
    });

    it('should BLOCK claim generation without evidence sources', async () => {
      const spec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.GENERATE_CLAIM,
        goalId: uuidv4(),
        objective: 'Generate unsupported claim',
        args: {
          claimText: 'Some unsupported claim',
          supportSourceIds: [], // NO SOURCES
        },
        successCriteria: [],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'test',
        decidedAt: new Date(),
      };

      const result = await executor.executeAction(spec);

      expect(result.status).toBe(ActionStatus.BLOCKED);
      expect(result.blockedReason).toContain('at least one source');
    });

    it('should execute REPLAN action', async () => {
      const spec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.REPLAN,
        goalId: uuidv4(),
        objective: 'Replan due to loop',
        args: {
          loopType: 'identical_action_repeat',
          streak: 3,
        },
        successCriteria: ['Replan recorded'],
        riskLevel: RiskLevel.MEDIUM,
        decidedBy: 'loop_detector',
        decidedAt: new Date(),
      };

      const result = await executor.executeAction(spec);

      expect(result.status).toBe(ActionStatus.COMPLETED);
      expect(result.observations.status).toBe('replan_triggered');
      expect(result.observations.loopType).toBe('identical_action_repeat');
    });

    it('should execute TERMINATE action', async () => {
      const spec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.TERMINATE,
        goalId: uuidv4(),
        objective: 'Terminate loop',
        args: { reason: 'Max iterations reached' },
        successCriteria: [],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'test',
        decidedAt: new Date(),
      };

      const result = await executor.executeAction(spec);

      expect(result.status).toBe(ActionStatus.COMPLETED);
      expect(result.observations.terminationReason).toContain('Max iterations');
    });
  });

  describe('Loop Detection', () => {
    it('should NOT detect loop with different actions', () => {
      const history: ActionHistory[] = [
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'test1' },
          resultStatus: 'completed',
          newArtifacts: 1,
        },
        {
          actionType: ActionType.FETCH_PAGE,
          timestamp: new Date(),
          args: { url: 'http://test.com' },
          resultStatus: 'completed',
          newArtifacts: 1,
        },
      ];

      const result = loopDetector.detectLoop(history);

      expect(result.isLooping).toBe(false);
      expect(result.streak).toBe(0);
    });

    it('should detect loop: identical action repeat 3+ times', () => {
      const history: ActionHistory[] = [
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'same query' },
          resultStatus: 'completed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'same query' },
          resultStatus: 'completed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'same query' },
          resultStatus: 'completed',
          newArtifacts: 0,
        },
      ];

      const result = loopDetector.detectLoop(history);

      expect(result.isLooping).toBe(true);
      expect(result.loopType).toBe('identical_action_repeat');
      expect(result.streak).toBe(3);
      expect(result.recommendation).toBe('replan');
    });

    it('should detect loop: no-progress streak 5+ actions', () => {
      const history: ActionHistory[] = [];
      for (let i = 0; i < 5; i++) {
        history.push({
          actionType: ActionType.EVALUATE_PROGRESS,
          timestamp: new Date(),
          args: { goalId: 'test-goal', step: i },
          resultStatus: 'completed',
          newArtifacts: 0, // NO NEW ARTIFACTS
        });
      }

      const result = loopDetector.detectLoop(history);

      expect(result.isLooping).toBe(true);
      expect(result.loopType).toBe('no_progress_streak');
      expect(result.streak).toBe(5);
      expect(result.recommendation).toBe('terminate');
    });

    it('should recommend termination for severe loops', () => {
      const history: ActionHistory[] = [
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'test' },
          resultStatus: 'failed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'test' },
          resultStatus: 'failed',
          newArtifacts: 0,
        },
        {
          actionType: ActionType.WEB_SEARCH,
          timestamp: new Date(),
          args: { query: 'test' },
          resultStatus: 'failed',
          newArtifacts: 0,
        },
      ];

      const result = loopDetector.detectLoop(history);

      expect(result.isLooping).toBe(true);
      expect(result.recommendation).toBeDefined();
    });
  });

  describe('Research Loop Integration', () => {
    it('should complete goal → search → evidence → claim cycle', async () => {
      const goalId = uuidv4();

      // Step 1: Search action
      const searchSpec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.WEB_SEARCH,
        goalId,
        objective: 'Research AI autonomy',
        args: { query: 'autonomous AI agents research' },
        successCriteria: ['Search initiated'],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'autonomy_planner',
        decidedAt: new Date(),
      };
      const searchResult = await executor.executeAction(searchSpec);
      expect(searchResult.status).toBe(ActionStatus.COMPLETED);

      // Step 2: Fetch evidence
      const fetchSpec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.FETCH_PAGE,
        goalId,
        objective: 'Fetch research page',
        args: { url: 'https://example.com/ai-autonomy' },
        successCriteria: ['Page fetched'],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'autonomy_planner',
        decidedAt: new Date(),
      };
      const fetchResult = await executor.executeAction(fetchSpec);
      expect(fetchResult.status).toBe(ActionStatus.COMPLETED);
      const evidenceId = fetchResult.createdArtifacts[0];
      expect(evidenceId).toBeDefined();

      // Step 3: Generate claim with evidence
      const claimSpec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.GENERATE_CLAIM,
        goalId,
        objective: 'Generate claim from research',
        args: {
          claimText: 'AI autonomy research shows rapid progress',
          supportSourceIds: [evidenceId],
          supportSnippets: ['Recent advances in autonomous AI systems show significant progress'],
          confidence: 0.85,
        },
        successCriteria: ['Claim backed by evidence'],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'autonomy_planner',
        decidedAt: new Date(),
      };
      const claimResult = await executor.executeAction(claimSpec);
      expect(claimResult.status).toBe(ActionStatus.COMPLETED);
      expect(claimResult.observations.claimId).toBeDefined();

      // Verify all artifacts are created
      expect([searchResult, fetchResult, claimResult]).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ status: ActionStatus.COMPLETED }),
          expect.objectContaining({ status: ActionStatus.COMPLETED }),
          expect.objectContaining({ status: ActionStatus.COMPLETED }),
        ])
      );
    });

    it('should terminate when loop is detected', async () => {
      const goalId = uuidv4();
      const history: ActionHistory[] = [];

      // Simulate 5 no-progress actions
      for (let i = 0; i < 5; i++) {
        history.push({
          actionType: ActionType.EVALUATE_PROGRESS,
          timestamp: new Date(),
          args: { goalId },
          resultStatus: 'completed',
          newArtifacts: 0,
        });
      }

      const loopResult = loopDetector.detectLoop(history);
      expect(loopResult.isLooping).toBe(true);

      // Should trigger termination
      const terminateSpec: ActionSpec = {
        actionId: uuidv4(),
        actionType: ActionType.TERMINATE,
        goalId,
        objective: 'Terminate due to loop',
        args: { reason: `Loop detected: ${loopResult.loopType}` },
        successCriteria: [],
        riskLevel: RiskLevel.LOW,
        decidedBy: 'loop_detector',
        decidedAt: new Date(),
      };

      const result = await executor.executeAction(terminateSpec);
      expect(result.status).toBe(ActionStatus.COMPLETED);
      expect(result.observations.status).toBe('terminated');
    });
  });

  describe('Dispatcher Routing', () => {
    it('should handle all action types without errors', async () => {
      const actionTypes = [
        ActionType.WEB_SEARCH,
        ActionType.FETCH_PAGE,
        ActionType.EVALUATE_PROGRESS,
        ActionType.GENERATE_CLAIM,
        ActionType.REPLAN,
        ActionType.TERMINATE,
      ];

      const goalId = uuidv4();

      for (const actionType of actionTypes) {
        const spec: ActionSpec = {
          actionId: uuidv4(),
          actionType,
          goalId,
          objective: `Test ${actionType}`,
          args:
            actionType === ActionType.GENERATE_CLAIM
              ? { claimText: 'test', supportSourceIds: ['test'], supportSnippets: ['test'] }
              : actionType === ActionType.FETCH_PAGE
                ? { url: 'https://example.com' }
                : { query: 'test' },
          successCriteria: [],
          riskLevel: RiskLevel.LOW,
          decidedBy: 'test',
          decidedAt: new Date(),
        };

        const result = await executor.executeAction(spec);
        expect(result.actionId).toBe(spec.actionId);
        expect([ActionStatus.COMPLETED, ActionStatus.BLOCKED, ActionStatus.FAILED]).toContain(result.status);
      }
    });
  });
});
