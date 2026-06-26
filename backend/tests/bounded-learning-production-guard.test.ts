import { BoundedCivilizationLearningRun } from '../src/services/bounded-learning-run.service';

describe('bounded learning production provider guard', () => {
  const originalEnv = process.env.AGENTCO_ENV;

  afterEach(() => {
    if (originalEnv === undefined) {
      delete process.env.AGENTCO_ENV;
    } else {
      process.env.AGENTCO_ENV = originalEnv;
    }
  });

  test('rejects deterministic test provider before starting a production run', async () => {
    process.env.AGENTCO_ENV = 'production';
    const run = new BoundedCivilizationLearningRun();

    await expect(run.execute({
      goal: 'prove deterministic provider cannot run in production',
      sourcePack: 'ai_tech',
      provider: 'deterministic_test_only',
      realWebEnabled: false,
    })).rejects.toThrow(/deterministic_test_only/);
  });
});
