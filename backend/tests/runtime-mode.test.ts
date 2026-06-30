import {
  activeRuntimeMode,
  assertDeterministicProviderAllowed,
  assertNoProductionFallbackProviders,
  configuredProviders,
  productionCapabilityContract,
} from '../src/runtime-mode';

describe('runtime provider classification', () => {
  test('NODE_ENV=production selects production mode', () => {
    expect(activeRuntimeMode({ NODE_ENV: 'production' } as NodeJS.ProcessEnv)).toBe('production');
  });

  test('AGENTCO_ENV=staging selects staging mode', () => {
    expect(activeRuntimeMode({ AGENTCO_ENV: 'staging' } as NodeJS.ProcessEnv)).toBe('staging');
  });

  test('reports simulated mock web adapter metadata', () => {
    const providers = configuredProviders({
      NODE_ENV: 'test',
      AGENTCO_WEB_ADAPTER: 'mock_web_adapter',
      LLM_PROVIDER: 'openai_compatible',
      LLM_API_KEY: 'test-key',
    } as NodeJS.ProcessEnv);
    expect(providers).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'web_adapter', status: 'simulated', reason: 'mock_web_adapter' }),
    ]));
  });

  test('production rejects mock web adapter', () => {
    expect(() => assertNoProductionFallbackProviders({
      NODE_ENV: 'production',
      AGENTCO_WEB_ADAPTER: 'mock_web_adapter',
      LLM_PROVIDER: 'openai_compatible',
      LLM_API_KEY: 'real-key',
      VAULT_ADDR: 'https://vault.example',
      VAULT_TOKEN: 'real-token',
    } as NodeJS.ProcessEnv)).toThrow(/non-real providers/);
  });

  test('production contract is satisfied only by real providers', () => {
    const contract = productionCapabilityContract({
      AGENTCO_ENV: 'production',
      AGENTCO_WEB_ADAPTER: 'real_web_adapter',
      LLM_PROVIDER: 'openai_compatible',
      LLM_API_KEY: 'real-key',
      VAULT_ADDR: 'https://vault.example',
      VAULT_TOKEN: 'real-token',
    } as NodeJS.ProcessEnv);

    expect(contract).toEqual({
      requiredProviders: ['web_adapter', 'llm', 'secrets'],
      missingProviders: [],
      nonRealProviders: [],
      satisfied: true,
    });
    expect(() => assertNoProductionFallbackProviders({
      AGENTCO_ENV: 'production',
      AGENTCO_WEB_ADAPTER: 'real_web_adapter',
      LLM_PROVIDER: 'openai_compatible',
      LLM_API_KEY: 'real-key',
      VAULT_ADDR: 'https://vault.example',
      VAULT_TOKEN: 'real-token',
    } as NodeJS.ProcessEnv)).not.toThrow();
  });

  test('production contract reports every non-real required provider', () => {
    const contract = productionCapabilityContract({
      AGENTCO_ENV: 'production',
      AGENTCO_WEB_ADAPTER: 'mock_web_adapter',
    } as NodeJS.ProcessEnv);

    expect(contract.satisfied).toBe(false);
    expect(contract.nonRealProviders).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'web_adapter', status: 'simulated' }),
      expect.objectContaining({ name: 'llm', status: 'unsupported' }),
      expect.objectContaining({ name: 'secrets', status: 'fallback' }),
    ]));
  });

  test('production rejects deterministic llm fallback', () => {
    expect(() => assertNoProductionFallbackProviders({
      AGENTCO_ENV: 'production',
      AGENTCO_WEB_ADAPTER: 'real_web_adapter',
      LLM_PROVIDER: 'deterministic_llm_fallback',
      VAULT_ADDR: 'https://vault.example',
      VAULT_TOKEN: 'real-token',
    } as NodeJS.ProcessEnv)).toThrow(/deterministic_llm_fallback/);
  });

  test('production rejects direct deterministic provider override', () => {
    expect(() => assertDeterministicProviderAllowed(
      'bounded_learning.provider',
      'deterministic_test_only',
      { AGENTCO_ENV: 'production' } as NodeJS.ProcessEnv
    )).toThrow(/deterministic_test_only/);
  });

  test('development permits deterministic provider override for tests only', () => {
    expect(() => assertDeterministicProviderAllowed(
      'bounded_learning.provider',
      'deterministic_test_only',
      { AGENTCO_ENV: 'development' } as NodeJS.ProcessEnv
    )).not.toThrow();
  });
});
