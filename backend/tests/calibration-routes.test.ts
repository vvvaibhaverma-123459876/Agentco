/**
 * Calibration governance integration tests.
 * - Pure calibration math (bayesian ECE/Brier, confidence gap) tested against the REAL functions.
 * - Routes proven wired into server.ts build(); DB-backed claim-accuracy mocked at boundary.
 */
jest.mock('../src/services/claim-accuracy-tracker.service', () => ({
  claimAccuracyTracker: { generateCalibrationReport: jest.fn() },
}));

import { build } from '../src/server';
import { bayesianService } from '../src/services/bayesian.service';
import { confidenceService } from '../src/services/confidence.service';
import { claimAccuracyTracker } from '../src/services/claim-accuracy-tracker.service';

const reader = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'auditor' }; // trust:read

describe('calibration math (pure, real functions)', () => {
  it('bayesian.computeCalibrationMetrics: perfectly-calibrated batch has low Brier', () => {
    const m = bayesianService.computeCalibrationMetrics([
      { confidence: 1.0, correct: true },
      { confidence: 1.0, correct: true },
      { confidence: 0.0, correct: false },
    ]);
    expect(m.brier_score).toBeGreaterThanOrEqual(0);
    expect(m.brier_score).toBeLessThan(0.1);
  });

  it('bayesian.computeCalibrationMetrics: confidently-wrong batch has high Brier', () => {
    const good = bayesianService.computeCalibrationMetrics([
      { confidence: 0.9, correct: true }, { confidence: 0.9, correct: true },
    ]);
    const bad = bayesianService.computeCalibrationMetrics([
      { confidence: 0.9, correct: false }, { confidence: 0.9, correct: false },
    ]);
    expect(bad.brier_score).toBeGreaterThan(good.brier_score);
  });

  it('confidence.computeCalibrationMetric flags overconfidence', () => {
    const m = confidenceService.computeCalibrationMetric(0.95, 0.5);
    expect(m.calibration_quality).toBe('overconfident');
    expect(m.calibration_gap).toBeCloseTo(0.45, 5);
  });
});

describe('calibration routes wired into the deployable app', () => {
  beforeEach(() => {
    (claimAccuracyTracker.generateCalibrationReport as jest.Mock).mockReset();
  });

  it('POST /api/calibration/metrics returns calibration metrics', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/calibration/metrics', headers: reader,
      payload: { predictions: [{ confidence: 0.8, correct: true }, { confidence: 0.4, correct: false }] },
    });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('brier_score');
    await app.close();
  });

  it('POST /api/calibration/metrics rejects an empty batch', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/calibration/metrics', headers: reader, payload: { predictions: [] } });
    expect(res.statusCode).toBe(400);
    await app.close();
  });

  it('POST /api/calibration/metric classifies a single prediction', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/calibration/metric', headers: reader,
      payload: { statedConfidence: 0.9, actualAccuracy: 0.5 },
    });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).calibration_quality).toBe('overconfident');
    await app.close();
  });

  it('GET /api/calibration/claim-accuracy returns the report', async () => {
    (claimAccuracyTracker.generateCalibrationReport as jest.Mock).mockResolvedValueOnce({ overall_accuracy: 0.8 });
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/api/calibration/claim-accuracy', headers: reader });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).overall_accuracy).toBe(0.8);
    await app.close();
  });
});
