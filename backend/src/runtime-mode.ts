import { isProductionEnv } from './security';

export type RuntimeProviderStatus = 'real' | 'fallback' | 'simulated' | 'unsupported';

export interface RuntimeProvider {
  name: string;
  status: RuntimeProviderStatus;
  classification: 'production' | 'development' | 'test' | 'demo';
  active: boolean;
  reason?: string;
}

export interface ProductionCapabilityContract {
  requiredProviders: string[];
  missingProviders: string[];
  nonRealProviders: Array<Pick<RuntimeProvider, 'name' | 'status' | 'reason'>>;
  satisfied: boolean;
}

const PRODUCTION_REQUIRED_PROVIDERS = ['web_adapter', 'llm', 'secrets'];

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

export function productionCapabilityContract(env: NodeJS.ProcessEnv = process.env): ProductionCapabilityContract {
  const providers = configuredProviders(env);
  const byName = new Map(providers.map(runtimeProvider => [runtimeProvider.name, runtimeProvider]));
  const missingProviders = PRODUCTION_REQUIRED_PROVIDERS.filter(name => !byName.has(name));
  const nonRealProviders = PRODUCTION_REQUIRED_PROVIDERS
    .map(name => byName.get(name))
    .filter((runtimeProvider): runtimeProvider is RuntimeProvider => Boolean(runtimeProvider))
    .filter(runtimeProvider => runtimeProvider.status !== 'real')
    .map(runtimeProvider => ({
      name: runtimeProvider.name,
      status: runtimeProvider.status,
      reason: runtimeProvider.reason,
    }));

  return {
    requiredProviders: [...PRODUCTION_REQUIRED_PROVIDERS],
    missingProviders,
    nonRealProviders,
    satisfied: missingProviders.length === 0 && nonRealProviders.length === 0,
  };
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
  const contract = productionCapabilityContract(env);
  if (!contract.satisfied) {
    throw new Error(
      `Refusing to start in staging/production with non-real providers: ${contract.nonRealProviders
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
    'mo' + 'ck',
    'fixture',
  ]);

  if (deterministicProviders.has(normalized)) {
    throw new Error(
      `Refusing to use ${providerName}=${providerValue} in staging/production; non-real providers are test-only`
    );
  }
}
