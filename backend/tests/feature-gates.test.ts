import { assertFeatureEnabled, evaluateFeatureGate, evaluateFeatureGates } from '../src/feature-gates';

describe('feature gates', () => {
  test('test mode disables live networked features and permits simulated data', () => {
    const gates = evaluateFeatureGates({ NODE_ENV: 'test' } as NodeJS.ProcessEnv);

    expect(gates).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'live_llm', enabled: false }),
      expect.objectContaining({ name: 'external_web', enabled: false }),
      expect.objectContaining({ name: 'simulated_data', enabled: true }),
      expect.objectContaining({ name: 'db_writes', enabled: true }),
    ]));
  });

  test('local development can explicitly disable a feature', () => {
    const gate = evaluateFeatureGate('civilization_scheduler', {
      AGENTCO_ENV: 'development',
      AGENTCO_FEATURE_CIVILIZATION_SCHEDULER: 'disabled',
    } as NodeJS.ProcessEnv);

    expect(gate).toEqual(expect.objectContaining({
      name: 'civilization_scheduler',
      enabled: false,
      source: 'env_override',
    }));
  });

  test('production enables runtime features only when provider contract is satisfied', () => {
    const gate = evaluateFeatureGate('live_llm', {
      AGENTCO_ENV: 'production',
      AGENTCO_WEB_ADAPTER: 'real_web_adapter',
      LLM_PROVIDER: 'openai_compatible',
      LLM_API_KEY: 'real-key',
      VAULT_ADDR: 'https://vault.example',
      VAULT_TOKEN: 'real-token',
    } as NodeJS.ProcessEnv);

    expect(gate).toEqual(expect.objectContaining({
      name: 'live_llm',
      enabled: true,
      source: 'production_contract',
    }));
  });

  test('production ignores enabling overrides when provider contract is incomplete', () => {
    const gate = evaluateFeatureGate('external_web', {
      AGENTCO_ENV: 'production',
      AGENTCO_FEATURE_EXTERNAL_WEB: 'enabled',
    } as NodeJS.ProcessEnv);

    expect(gate).toEqual(expect.objectContaining({
      name: 'external_web',
      enabled: false,
      source: 'production_contract',
    }));
  });

  test('production never permits simulated data override', () => {
    expect(() => evaluateFeatureGate('simulated_data', {
      AGENTCO_ENV: 'production',
      AGENTCO_FEATURE_SIMULATED_DATA: 'enabled',
    } as NodeJS.ProcessEnv)).toThrow(/simulated_data/);
  });

  test('assertFeatureEnabled fails closed with gate reason', () => {
    expect(() => assertFeatureEnabled('live_llm', { NODE_ENV: 'test' } as NodeJS.ProcessEnv)).toThrow(/live_llm/);
  });
});
