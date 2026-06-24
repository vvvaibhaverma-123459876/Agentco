/**
 * Institutions / goals / coalitions integration tests.
 * Proves the civilization org-layer is wired into the deployable app (server.ts build()).
 * DB-backed services are mocked at their boundary; institutionsService.createInstitution is
 * in-memory and exercised for real.
 */
jest.mock('../src/services/goal-manager.service', () => ({
  goalManager: { proposeGoal: jest.fn(), activateGoal: jest.fn() },
}));
jest.mock('../src/services/goal-hierarchy.service', () => ({
  goalHierarchyService: { getGoalHierarchy: jest.fn() },
}));
jest.mock('../src/services/coalition-formation.service', () => ({
  coalitionFormationService: { recommendTeamComposition: jest.fn() },
}));

import { build } from '../src/server';
import { goalManager } from '../src/services/goal-manager.service';
import { goalHierarchyService } from '../src/services/goal-hierarchy.service';
import { coalitionFormationService } from '../src/services/coalition-formation.service';

const headers = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'operator' };
const readers = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'operator' };

describe('institutions/goals/coalitions wired into the deployable app', () => {
  beforeEach(() => {
    (goalManager.proposeGoal as jest.Mock).mockReset();
    (goalManager.activateGoal as jest.Mock).mockReset();
    (goalHierarchyService.getGoalHierarchy as jest.Mock).mockReset();
    (coalitionFormationService.recommendTeamComposition as jest.Mock).mockReset();
  });

  it('POST /api/institutions creates a real institution (in-memory service)', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/institutions', headers, payload: { domain: 'mathematics' } });
    expect(res.statusCode).toBe(201);
    const inst = JSON.parse(res.payload);
    expect(inst).toHaveProperty('id');
    await app.close();
  });

  it('POST /api/institutions rejects a missing domain', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/institutions', headers, payload: {} });
    expect(res.statusCode).toBe(400);
    await app.close();
  });

  it('POST /api/goals proposes a governed goal via goalManager', async () => {
    (goalManager.proposeGoal as jest.Mock).mockResolvedValueOnce({ goalId: 'goal-1' });
    const app = await build();
    const res = await app.inject({
      method: 'POST',
      url: '/api/goals',
      headers,
      payload: { title: 'Investigate primes', domain: 'math.NT', proposedBy: 'agent-1',
        source: 'agent_proposed', riskLevel: 'low', successCriteria: { x: 1 }, stopConditions: { y: 1 } },
    });
    expect(res.statusCode).toBe(201);
    expect(JSON.parse(res.payload).goal_id).toBe('goal-1');
    expect(goalManager.proposeGoal).toHaveBeenCalled();
    await app.close();
  });

  it('POST /api/goals rejects missing required fields', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/goals', headers, payload: { title: 'x' } });
    expect(res.statusCode).toBe(400);
    expect(goalManager.proposeGoal).not.toHaveBeenCalled();
    await app.close();
  });

  it('POST /api/goals/:id/activate activates via goalManager', async () => {
    (goalManager.activateGoal as jest.Mock).mockResolvedValueOnce(undefined);
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/goals/goal-1/activate', headers });
    expect(res.statusCode).toBe(200);
    expect(goalManager.activateGoal).toHaveBeenCalledWith('goal-1');
    await app.close();
  });

  it('GET /api/institutions/:id/goals returns the goal hierarchy', async () => {
    (goalHierarchyService.getGoalHierarchy as jest.Mock).mockResolvedValueOnce({ institutionId: 'inst-1', goals: [] });
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/api/institutions/inst-1/goals', headers: readers });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).institutionId).toBe('inst-1');
    await app.close();
  });

  it('POST /api/coalitions/recommend returns a team recommendation', async () => {
    (coalitionFormationService.recommendTeamComposition as jest.Mock).mockResolvedValueOnce({
      recommended_lead: null, recommended_team_size: 4, predicted_success_rate: 0.7, reasoning: 'baseline',
    });
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/coalitions/recommend', headers,
      payload: { objective: 'prove a bound', required_specializations: ['researcher', 'reviewer'] },
    });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).recommended_team_size).toBe(4);
    expect(coalitionFormationService.recommendTeamComposition).toHaveBeenCalledWith('prove a bound', ['researcher', 'reviewer']);
    await app.close();
  });
});
