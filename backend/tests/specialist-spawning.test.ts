/**
 * Specialist Subprocess Spawning Tests
 * =====================================
 * Verifies that specialists can be spawned as subprocesses and communicate via HTTP.
 */

import { TeamActivationService, SpecialistActivationRequest } from '../src/services/team-activation.service';

describe('Specialist Subprocess Spawning', () => {
  let teamActivation: TeamActivationService;

  beforeAll(() => {
    teamActivation = new TeamActivationService();
  });

  afterEach(async () => {
    // Cleanup any active specialists
    // Note: In a real test, we'd terminate each specialist
  });

  test('should spawn a researcher specialist with HTTP endpoint', async () => {
    const request: SpecialistActivationRequest = {
      parentGoalId: 'test-goal-1',
      role: 'researcher',
      objective: 'Test research task',
    };

    const specialist = await teamActivation.activateSpecialist(request);

    expect(specialist).not.toBeNull();
    expect(specialist?.specialistId).toBeDefined();
    expect(specialist?.role).toBe('researcher');
    expect(specialist?.httpEndpoint).toBeDefined();
    expect(specialist?.portNumber).toBeDefined();
    expect(specialist?.processId).toBeGreaterThan(0);
    expect(specialist?.httpEndpoint).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
  }, 10000);

  test('should make HTTP request to specialist /status endpoint', async () => {
    const request: SpecialistActivationRequest = {
      parentGoalId: 'test-goal-2',
      role: 'researcher',
      objective: 'Test status check',
    };

    const specialist = await teamActivation.activateSpecialist(request);
    expect(specialist?.httpEndpoint).toBeDefined();

    // Request status from specialist
    const statusResponse = await fetch(`${specialist!.httpEndpoint}/status`);
    expect(statusResponse.ok).toBe(true);

    const status = (await statusResponse.json()) as any;
    expect(status.specialist_id).toBe(specialist?.specialistId);
    expect(status.role).toBe('researcher');
    expect(status.status).toBe('running');
    expect(status.budget).toBeDefined();
  }, 10000);

  test('should execute action via specialist /execute endpoint', async () => {
    const request: SpecialistActivationRequest = {
      parentGoalId: 'test-goal-3',
      role: 'researcher',
      objective: 'Test action execution',
    };

    const specialist = await teamActivation.activateSpecialist(request);
    expect(specialist?.httpEndpoint).toBeDefined();

    // Send action to specialist
    const actionSpec = {
      actionId: 'action-1',
      actionType: 'web_search',
      objective: 'Search for test',
      args: { query: 'test search' },
    };

    const response = await fetch(`${specialist!.httpEndpoint}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(actionSpec),
    });

    expect(response.ok).toBe(true);
    const result = (await response.json()) as any;
    expect(result.status).toBe('completed');
    expect(result.observations).toBeDefined();
    expect(result.artifacts).toBeDefined();
  }, 10000);

  test('should reject request with invalid role', async () => {
    const request: SpecialistActivationRequest = {
      parentGoalId: 'test-goal-4',
      role: 'invalid-role',
      objective: 'Should fail',
    };

    const specialist = await teamActivation.activateSpecialist(request);
    expect(specialist).toBeNull();
  });

  test('should enforce max concurrent specialists per goal', async () => {
    const parentGoalId = 'test-goal-5';

    // Spawn 3 specialists
    const spec1 = await teamActivation.activateSpecialist({
      parentGoalId,
      role: 'researcher',
      objective: 'First',
    });
    expect(spec1).not.toBeNull();

    const spec2 = await teamActivation.activateSpecialist({
      parentGoalId,
      role: 'fetcher',
      objective: 'Second',
    });
    expect(spec2).not.toBeNull();

    const spec3 = await teamActivation.activateSpecialist({
      parentGoalId,
      role: 'evidence_summarizer',
      objective: 'Third',
    });
    expect(spec3).not.toBeNull();

    // Fourth should be rejected (max 3)
    const spec4 = await teamActivation.activateSpecialist({
      parentGoalId,
      role: 'claim_validator',
      objective: 'Fourth - should fail',
    });
    expect(spec4).toBeNull();
  }, 15000);
});
