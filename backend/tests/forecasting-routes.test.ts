/**
 * Forecasting & calibration-governance integration tests.
 * - dynamic-calibration tested against the REAL pure functions.
 * - Routes proven wired into server.ts build(); DB/network services mocked at boundary.
 */
jest.mock('../src/services/calibration-drift-monitor.service', () => ({
  calibrationDriftMonitorService: { listUnresolved: jest.fn() },
}));
jest.mock('../src/services/ensemble.service', () => ({
  ensembleService: { ensembleVote: jest.fn() },
}));

import { build } from '../src/server';
import { dynamicCalibrationService } from '../src/services/dynamic-calibration.service';
import { calibrationDriftMonitorService } from '../src/services/calibration-drift-monitor.service';
import { ensembleService } from '../src/services/ensemble.service';

const reader = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'auditor' }; // trust:read

describe('dynamic calibration (real pure functions)', () => {
  it('getCalibratedConfidence returns a bounded adjusted confidence with an interval', () => {
    const r = dynamicCalibrationService.getCalibratedConfidence(0.8, 'general', 'medium');
    expect(r.adjusted_confidence).toBeGreaterThanOrEqual(0);
    expect(r.adjusted_confidence).toBeLessThanOrEqual(1);
    expect(r.confidence_interval.lower).toBeLessThanOrEqual(r.confidence_interval.upper);
  });
});

describe('forecasting routes wired into the deployable app', () => {
  beforeEach(() => {
    (calibrationDriftMonitorService.listUnresolved as jest.Mock).mockReset();
    (ensembleService.ensembleVote as jest.Mock).mockReset();
  });

  it('POST /api/calibration/dynamic/confidence returns calibrated confidence', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/calibration/dynamic/confidence', headers: reader,
      payload: { baseConfidence: 0.8, domain: 'general', difficulty: 'medium' },
    });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('adjusted_confidence');
    await app.close();
  });

  it('POST /api/calibration/dynamic/confidence rejects non-numeric base', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/calibration/dynamic/confidence', headers: reader, payload: { domain: 'x' } });
    expect(res.statusCode).toBe(400);
    await app.close();
  });

  it('GET /api/calibration/drift lists unresolved drift events', async () => {
    (calibrationDriftMonitorService.listUnresolved as jest.Mock).mockResolvedValueOnce([{ id: 'd1' }]);
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/api/calibration/drift', headers: reader });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).count).toBe(1);
    await app.close();
  });

  it('POST /api/ensemble/vote delegates to the ensemble service', async () => {
    (ensembleService.ensembleVote as jest.Mock).mockResolvedValueOnce({ answer: 'yes', agreement: 0.8 });
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/ensemble/vote', headers: reader, payload: { question: 'is P=NP?' } });
    expect(res.statusCode).toBe(200);
    expect(ensembleService.ensembleVote).toHaveBeenCalledWith('is P=NP?');
    await app.close();
  });
});
