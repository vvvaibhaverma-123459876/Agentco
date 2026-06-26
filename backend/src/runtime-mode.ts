import { isProductionEnv } from './security';

export type RuntimeProviderStatus = 'real' | 'fallback' | 'simulated' | 'unsupported';

export interface RuntimeProvider {
  name: string;
  status: RuntimeProviderStatus;
  classification: 'production' | 'development' | 'test' | 'demo';
  active: boolean;
  reason?: string;
}

export function activeRuntimeMode(env: NodeJS.ProcessEnv = process.env): 'test' | 'development' | 'staging' | 'production' {
  const agentcoEnv = (env.AGENTCO_ENV || '').toLowerCase();
  const nodeEnv = (env.NODE_ENV || '').toLowerCase();
  if (agentcoEnv === 'production' || nodeEnv === 'production') return 'production';
  if (agentcoEnv === 'staging') return 'staging';
  if (nodeEnv === 'test' || agentcoEnv === 'test') return 'test';
  return 'development';
}

export function configuredProviders(env: NodeJS.ProcessEnv = process.env): RuntimeProvider[] {
  const mode = activeRuntimeMode(env);
  const webAdapter = env.AGENTCO_WEB_ADAPTER || (mode === 'test' ? 'mock_web_adapter' : 'real_web_adapter');
  const llmProvider = env.LLM_PROVIDER || (env.LLM_API_KEY || env.OPENAI_API_KEY ? 'openai_compatible' : 'unsupported');
  const secretProvider = env.VAULT_ADDR && env.VAULT_TOKEN ? 'vault' : 'env_secret_provider';

  const providers: RuntimeProvider[] = [
    provider('web_adapter', webAdapter, webAdapter === 'mock_web_adapter' ? 'simulated' : 'real'),
    provider('llm', llmProvider, llmProvider === 'deterministic_llm_fallback' ? 'simulated' : llmProvider === 'unsupported' ? 'unsupported' : 'real'),
    provider('secrets', secretProvider, secretProvider === 'env_secret_provider' ? 'fallback' : 'real'),
  ];
  return providers;
}

function provider(name: string, implementation: string, status: RuntimeProviderStatus): RuntimeProvider {
  const classification = status === 'real' ? 'production' : status === 'simulated' ? 'test' : 'development';
  return {
    name,
    status,
    classification,
    active: status !== 'unsupported',
    reason: implementation,
  };
}

export function assertNoProductionFallbackProviders(env: NodeJS.ProcessEnv = process.env): void {
  if (!isProductionEnv(env)) return;
  const unsafe = configuredProviders(env).filter(provider =>
    provider.status === 'fallback' || provider.status === 'simulated' || provider.status === 'unsupported'
  );
  if (unsafe.length > 0) {
    throw new Error(
      `Refusing to start in staging/production with non-real providers: ${unsafe
        .map(provider => `${provider.name}=${provider.reason}`)
        .join(', ')}`
    );
  }
}

export function assertDeterministicProviderAllowed(
  providerName: string,
  providerValue: string | undefined,
  env: NodeJS.ProcessEnv = process.env
): void {
  if (!isProductionEnv(env)) return;
  if (!providerValue) return;

  const normalized = providerValue.toLowerCase();
  const deterministicProviders = new Set([
    'deterministic_test_only',
    'deterministic_llm_fallback',
    'fake',
    'mock',
    'fixture',
  ]);

  if (deterministicProviders.has(normalized)) {
    throw new Error(
      `Refusing to use ${providerName}=${providerValue} in staging/production; deterministic, fake, mock, and fixture providers are test-only`
    );
  }
}
