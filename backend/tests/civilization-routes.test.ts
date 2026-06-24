/**
 * Civilization integration tests.
 * - Pure unit test of the bridge scoring (real function, no mocks).
 * - Route-level tests proving the civilization layer is wired into the deployable app
 *   (server.ts build()), with the heavy services mocked at their boundary.
 */
jest.mock('../src/services/civilization.service', () => ({
  civilizationService: { solveWithCivilization: jest.fn() },
}));
jest.mock('../src/services/autonomy-civilization-bridge.service', () => {
  // Keep the REAL computePerformanceScore (pure), mock the I/O methods.
  const actual = jest.requireActual('../src/services/autonomy-civilization-bridge.service');
  return {
    autonomyCivilizationBridgeService: {
      computePerformanceScore: actual.autonomyCivilizationBridgeService.computePerformanceScore.bind(
        actual.autonomyCivilizationBridgeService,
      ),
      routeWorkToAutonomy: jest.fn(),
      reportWorkCompletion: jest.fn(),
    },
  };
});

import { build } from '../src/server';
import { civilizationService } from '../src/services/civilization.service';
import { autonomyCivilizationBridgeService } from '../src/services/autonomy-civilization-bridge.service';

const headers = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'operator' };

describe('bridge performance scoring (pure, real function)', () => {
  it('produces a bounded weighted score from a work result', () => {
    const score = autonomyCivilizationBridgeService.computePerformanceScore({
      work_request_id: 'w1',
      specialist_role: 'researcher',
      evidence_count: 5,
      claim_count: 2,
      confidence_avg: 0.8,
      tokens_used: 1000,
      iterations_used: 10,
      time_elapsed_seconds: 600,
    });
    for (const v of [score.evidence_quality, score.claim_accuracy, score.efficiency, score.overall]) {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
    }
    expect(score.evidence_quality).toBeCloseTo(0.5, 5); // 5/10
    expect(score.claim_accuracy).toBeCloseTo(0.8, 5);
  });

  it('is monotonic in evidence_count (more evidence ⇒ ≥ quality)', () => {
    const base = { work_request_id: 'w', specialist_role: 'r', claim_count: 0, confidence_avg: 0.5,
      tokens_used: 100, iterations_used: 1, time_elapsed_seconds: 60 };
    const low = autonomyCivilizationBridgeService.computePerformanceScore({ ...base, evidence_count: 1 });
    const high = autonomyCivilizationBridgeService.computePerformanceScore({ ...base, evidence_count: 8 });
    expect(high.evidence_quality).toBeGreaterThanOrEqual(low.evidence_quality);
  });
});

describe('civilization routes wired into the deployable app', () => {
  beforeEach(() => {
    (civilizationService.solveWithCivilization as jest.Mock).mockReset();
    (autonomyCivilizationBridgeService.routeWorkToAutonomy as jest.Mock).mockReset();
    (autonomyCivilizationBridgeService.reportWorkCompletion as jest.Mock).mockReset();
  });

  it('POST /api/civilization/solve delegates to the civilization service', async () => {
    (civilizationService.solveWithCivilization as jest.Mock).mockResolvedValueOnce({ answer: '42', confidence: 0.9 });
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/civilization/solve', payload: { question: 'meaning?' } });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).answer).toBe('42');
    expect(civilizationService.solveWithCivilization).toHaveBeenCalledWith('meaning?');
    await app.close();
  });

  it('POST /api/civilization/solve rejects empty question', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/civilization/solve', payload: { question: '' } });
    expect(res.statusCode).toBe(400);
    await app.close();
  });

  it('POST /api/civilization/work drives the bridge into the autonomy loop', async () => {
    (autonomyCivilizationBridgeService.routeWorkToAutonomy as jest.Mock).mockResolvedValueOnce('autonomy_run_123');
    const app = await build();
    const res = await app.inject({
      method: 'POST',
      url: '/api/civilization/work',
      headers,
      payload: { work_request_id: 'wr-1', objective: 'research primes', specialists: ['researcher'] },
    });
    expect(res.statusCode).toBe(202);
    expect(JSON.parse(res.payload).autonomy_goal_id).toBe('autonomy_run_123');
    expect(autonomyCivilizationBridgeService.routeWorkToAutonomy).toHaveBeenCalledWith('wr-1', 'research primes', ['researcher']);
    await app.close();
  });
});
