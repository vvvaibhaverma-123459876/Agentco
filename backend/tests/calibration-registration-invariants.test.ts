import crypto from 'crypto';
import { afterEach, describe, expect, jest, test } from '@jest/globals';
import { db } from '../src/db/client';
import { ledgerResolutionService } from '../src/services/resolution-service.service';

function validRegistration(overrides: Record<string, unknown> = {}) {
  return {
    claim: 'registration invariant claim',
    probability: 0.7,
    confidence_basis: {},
    producing_agent_id: `reg-invariant-${crypto.randomUUID()}`,
    producing_prompt_version: 'reg-invariant-v1',
    resolution_criterion: 'independent external evidence resolves this claim',
    resolution_date: new Date(Date.now() + 60_000),
    ground_truth_source: 'external_resolution_feed',
    horizon_class: 'short' as const,
    domain: 'registration_invariants',
    claim_type: 'test',
    correlation_id: crypto.randomUUID(),
    ...overrides,
  };
}

describe('prediction registration invariants', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('live registration rejects backdated resolution_date before DB insert', async () => {
    await expect(
      ledgerResolutionService.registerPrediction(validRegistration({
        resolution_date: new Date(Date.now() - 1000),
      }))
    ).rejects.toThrow(/resolution_date must be in the future/);
  });

  test('registration rejects disqualified internal source tokens without blocking user-agent text', async () => {
    await expect(
      ledgerResolutionService.registerPrediction(validRegistration({
        ground_truth_source: 'internal simulation export',
      }))
    ).rejects.toThrow(/ground_truth_source/);

    const query = jest.spyOn(db, 'query').mockResolvedValue({ rows: [], rowCount: 1 } as any);
    await expect(ledgerResolutionService.registerPrediction(validRegistration({
      ground_truth_source: 'Google Analytics user agent logs export',
    }))).resolves.toEqual(expect.any(String));
    expect(query).toHaveBeenCalledTimes(1);
  });
});
