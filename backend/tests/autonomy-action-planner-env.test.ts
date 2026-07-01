import { AutonomyActionPlannerService } from '../src/services/autonomy-action-planner.service';

describe('AutonomyActionPlannerService environment handling', () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    process.env = { ...originalEnv };
    jest.restoreAllMocks();
  });

  test('does not require an LLM key at construction time', () => {
    delete process.env.LLM_API_KEY;
    delete process.env.OPENAI_API_KEY;

    expect(() => new AutonomyActionPlannerService()).not.toThrow();
  });

  test('requires an LLM key only when planning needs an LLM call', async () => {
    delete process.env.LLM_API_KEY;
    delete process.env.OPENAI_API_KEY;
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => undefined);

    const planner = new AutonomyActionPlannerService();

    await expect(planner.planNextAction('goal-1', {
      goalText: 'Collect evidence for a vendor risk decision',
      claimsGenerated: 0,
      evidenceCount: 0,
      loopDetection: {
        isLooping: false,
        streak: 0,
        recommendation: 'proceed',
      },
      previousActions: [],
    })).rejects.toThrow(/LLM_API_KEY or OPENAI_API_KEY/);
  });
});
