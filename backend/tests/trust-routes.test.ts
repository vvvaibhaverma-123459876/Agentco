/**
 * Trust + reputation integration tests.
 * - Pure scorers (trustworthiness, trust-scoring) tested directly against the REAL functions.
 * - Routes proven wired into server.ts build(); DB-backed reputation mocked at boundary.
 */
jest.mock('../src/services/reputation-scale.service', () => ({
  reputationScaleService: { getReputationDistribution: jest.fn() },
}));
jest.mock('../src/services/trust-impact-assessment.service', () => ({
  trustImpactAssessmentService: { produceRecommendation: jest.fn() },
}));

import { build } from '../src/server';
import { trustworthinessService } from '../src/services/trustworthiness.service';
import { trustScoringService } from '../src/services/trust-scoring.service';
import { reputationScaleService } from '../src/services/reputation-scale.service';

const reader = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'auditor' };   // has trust:read

describe('trust scorers (pure, real functions)', () => {
  it('computeTrustScore returns a composite within [0,1] and rewards high inputs', () => {
    const low = trustworthinessService.computeTrustScore(0.3, 0.4, 0.3, 0.3, 0.3, 0.3);
    const high = trustworthinessService.computeTrustScore(0.95, 0.02, 0.95, 0.9, 0.9, 0.95);
    for (const s of [low, high]) {
      expect(s.overall_trust).toBeGreaterThanOrEqual(0);
      expect(s.overall_trust).toBeLessThanOrEqual(1);
    }
    expect(high.overall_trust).toBeGreaterThan(low.overall_trust);
  });

  it('assessAnswerRisk requires review below the domain threshold and escalates when low', () => {
    const safe = trustworthinessService.assessAnswerRisk('ok', 0.99, 'general');
    expect(safe.requires_review).toBe(false);
    const risky = trustworthinessService.assessAnswerRisk('careful', 0.5, 'medical');
    expect(risky.requires_review).toBe(true);
    expect(risky.suggested_actions).toContain('Reject answer');
  });

  it('trustScoring.computeTrustScore yields a composite_score in range', () => {
    const s = trustScoringService.computeTrustScore(0.9, 0.05, 0.85, 5, 0.8, 0.7);
    expect(s.composite_score).toBeGreaterThanOrEqual(0);
    expect(s.composite_score).toBeLessThanOrEqual(1);
  });
});

describe('trust routes wired into the deployable app', () => {
  beforeEach(() => {
    (reputationScaleService.getReputationDistribution as jest.Mock).mockReset();
  });

  it('POST /api/trust/score returns a trustworthiness score', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/trust/score', headers: reader,
      payload: { accuracy: 0.9, calibrationError: 0.05, consistency: 0.8, explainability: 0.8, uncertaintyQuality: 0.8, conformalCoverage: 0.9 },
    });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('overall_trust');
    await app.close();
  });

  it('POST /api/trust/assess-risk gates a low-trust medical answer', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/trust/assess-risk', headers: reader,
      payload: { answer: 'take 2 pills', trustScore: 0.5, domain: 'medical' },
    });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).requires_review).toBe(true);
    await app.close();
  });

  it('GET /api/institutions/:id/reputation returns the distribution', async () => {
    (reputationScaleService.getReputationDistribution as jest.Mock).mockResolvedValueOnce({ mean: 0.6, count: 10 });
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/api/institutions/inst-1/reputation', headers: reader });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).count).toBe(10);
    expect(reputationScaleService.getReputationDistribution).toHaveBeenCalledWith('inst-1');
    await app.close();
  });

  it('rejects trust:read routes without the scope', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/trust/score', headers: { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'operator' },
      payload: { accuracy: 0.9 },
    });
    expect(res.statusCode).toBe(403);
    await app.close();
  });
});
