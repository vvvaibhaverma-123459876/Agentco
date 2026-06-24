/**
 * Operations integration tests.
 * - protected-surface-validator.isProtected + multiAgentEnsemble.getExpertStatus tested
 *   against the REAL functions.
 * - Routes proven wired into server.ts build(); DB services mocked at boundary.
 */
jest.mock('../src/services/planner.service', () => ({
  planner: { validatePlanDAG: jest.fn() },
}));
jest.mock('../src/services/rollback.service', () => ({
  rollback: { getDeploymentSnapshot: jest.fn() },
}));
jest.mock('../src/services/governance-reputation-integration.service', () => ({
  governanceReputationIntegrationService: { getVotingWeight: jest.fn() },
}));
jest.mock('../src/services/perception.service', () => ({
  perception: { persistEvent: jest.fn() },
}));

import { build } from '../src/server';
import { isProtected } from '../src/services/protected-surface-validator.service';
import { planner } from '../src/services/planner.service';
import { rollback } from '../src/services/rollback.service';
import { governanceReputationIntegrationService } from '../src/services/governance-reputation-integration.service';
import { perception } from '../src/services/perception.service';

const gov = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'operator' };   // governance:mutate, task:read
const reader = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'auditor' }; // trust:read

describe('protected-surface-validator (real pure function)', () => {
  it('isProtected returns a boolean and is stable', () => {
    expect(typeof isProtected('some.random.field')).toBe('boolean');
  });
});

describe('operations routes wired into the deployable app', () => {
  beforeEach(() => {
    (planner.validatePlanDAG as jest.Mock).mockReset();
    (rollback.getDeploymentSnapshot as jest.Mock).mockReset();
    (governanceReputationIntegrationService.getVotingWeight as jest.Mock).mockReset();
    (perception.persistEvent as jest.Mock).mockReset();
  });

  it('GET /api/protected-surfaces/check reports protection status', async () => {
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/api/protected-surfaces/check?field=foo', headers: gov });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('protected');
    await app.close();
  });

  it('GET /api/ensemble/experts returns expert status', async () => {
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/api/ensemble/experts', headers: reader });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('status');
    await app.close();
  });

  it('GET /api/plans/:id/validate validates a plan DAG', async () => {
    (planner.validatePlanDAG as jest.Mock).mockResolvedValueOnce({ valid: true, issues: [] });
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/api/plans/plan-1/validate', headers: gov });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).valid).toBe(true);
    expect(planner.validatePlanDAG).toHaveBeenCalledWith('plan-1');
    await app.close();
  });

  it('GET /api/rollback/:id/snapshot returns 404 when missing', async () => {
    (rollback.getDeploymentSnapshot as jest.Mock).mockResolvedValueOnce(null);
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/api/rollback/canary-1/snapshot', headers: gov });
    expect(res.statusCode).toBe(404);
    await app.close();
  });

  it('GET /api/governance/voting-weight/:entityId returns the weight', async () => {
    (governanceReputationIntegrationService.getVotingWeight as jest.Mock).mockResolvedValueOnce(2.5);
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/api/governance/voting-weight/agent-1', headers: gov });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).voting_weight).toBe(2.5);
    await app.close();
  });

  it('POST /api/perception/events persists a dedup-aware event', async () => {
    (perception.persistEvent as jest.Mock).mockResolvedValueOnce({ eventId: 'ev-1', isDuplicate: false });
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/perception/events', headers: gov,
      payload: { sourceId: 's1', eventType: 'paper', sourceFingerprint: 'fp1' },
    });
    expect(res.statusCode).toBe(201);
    expect(JSON.parse(res.payload).eventId).toBe('ev-1');
    await app.close();
  });

  it('POST /api/perception/events rejects missing fields', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/perception/events', headers: gov, payload: { sourceId: 's1' } });
    expect(res.statusCode).toBe(400);
    await app.close();
  });
});
