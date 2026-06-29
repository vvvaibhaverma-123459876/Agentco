import { describe, expect, test } from '@jest/globals';
import { ActionExecutorService } from '../src/services/action-executor.service';
import { claimGrounding } from '../src/services/claim-grounding.service';
import { ActionSpec, ActionStatus, ActionType, RiskLevel } from '../src/types/action.types';
import { MockWebAdapter } from './support/mock-web-adapter';
import { v4 as uuidv4 } from 'uuid';

describe('claim grounding validator', () => {
  test('accepts support snippets that are token-subsequences of registered evidence', async () => {
    const executor = new ActionExecutorService();
    executor.setWebAdapter(new MockWebAdapter());
    const fetchSpec: ActionSpec = {
      actionId: uuidv4(),
      actionType: ActionType.FETCH_PAGE,
      goalId: uuidv4(),
      objective: 'Fetch evidence',
      args: { url: 'https://example.com/autonomy-research' },
      successCriteria: [],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'test',
      decidedAt: new Date(),
    };
    const fetchResult = await executor.executeAction(fetchSpec);
    expect(fetchResult.status).toBe(ActionStatus.COMPLETED);

    const result = await claimGrounding.validate({
      claimText: 'Autonomous AI systems show progress in reasoning and planning.',
      supportSourceIds: [fetchResult.createdArtifacts[0]],
      supportSnippets: ['autonomous AI systems show significant progress in reasoning planning and self correction'],
    });

    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  test('rejects snippets that are not present in registered evidence', async () => {
    const executor = new ActionExecutorService();
    executor.setWebAdapter(new MockWebAdapter());
    const fetchResult = await executor.executeAction({
      actionId: uuidv4(),
      actionType: ActionType.FETCH_PAGE,
      goalId: uuidv4(),
      objective: 'Fetch evidence',
      args: { url: 'https://example.com/autonomy-research' },
      successCriteria: [],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'test',
      decidedAt: new Date(),
    });

    const result = await claimGrounding.validate({
      claimText: 'Unsupported claim',
      supportSourceIds: [fetchResult.createdArtifacts[0]],
      supportSnippets: ['this exact unsupported phrase is absent'],
    });

    expect(result.valid).toBe(false);
    expect(result.errors.join(' ')).toContain('token-subsequence');
  });
});
