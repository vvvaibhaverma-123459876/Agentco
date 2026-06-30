import { activeRuntimeMode, productionCapabilityContract } from './runtime-mode';
import { isProductionEnv } from './security';

export type FeatureGateName =
  | 'live_llm'
  | 'db_writes'
  | 'external_web'
  | 'simulated_data'
  | 'self_modification'
  | 'civilization_scheduler';

export interface FeatureGateDecision {
  name: FeatureGateName;
  enabled: boolean;
  source: 'runtime_mode' | 'env_override' | 'production_contract';
  reason: string;
}

const FEATURE_NAMES: FeatureGateName[] = [
  'live_llm',
  'db_writes',
  'external_web',
  'simulated_data',
  'self_modification',
  'civilization_scheduler',
];

function envKey(name: FeatureGateName): string {
  return `AGENTCO_FEATURE_${name.toUpperCase()}`;
}

function parseOverride(value: string | undefined): boolean | undefined {
  if (!value) return undefined;
  const normalized = value.toLowerCase();
  if (['1', 'true', 'enabled', 'on', 'yes'].includes(normalized)) return true;
  if (['0', 'false', 'disabled', 'off', 'no'].includes(normalized)) return false;
  throw new Error(`Invalid feature gate override value: ${value}`);
}

function runtimeDefault(name: FeatureGateName, env: NodeJS.ProcessEnv): FeatureGateDecision {
  const mode = activeRuntimeMode(env);
  const contract = productionCapabilityContract(env);
  const productionContractReady = contract.satisfied;

  if (name === 'simulated_data') {
    return {
      name,
      enabled: mode === 'test',
      source: 'runtime_mode',
      reason: mode === 'test' ? 'test mode permits simulated data' : 'simulated data disabled outside test mode',
    };
  }

  if (name === 'self_modification') {
    return {
      name,
      enabled: false,
      source: 'runtime_mode',
      reason: 'self modification requires an explicit audited workflow',
    };
  }

  if (mode === 'production') {
    return {
      name,
      enabled: productionContractReady,
      source: 'production_contract',
      reason: productionContractReady ? 'production provider contract satisfied' : 'production provider contract incomplete',
    };
  }

  if (mode === 'test') {
    return {
      name,
      enabled: name !== 'live_llm' && name !== 'external_web',
      source: 'runtime_mode',
      reason: 'test mode disables live networked capabilities by default',
    };
  }

  return {
    name,
    enabled: true,
    source: 'runtime_mode',
    reason: `${mode} mode enables local runtime capabilities`,
  };
}

export function evaluateFeatureGate(
  name: FeatureGateName,
  env: NodeJS.ProcessEnv = process.env
): FeatureGateDecision {
  const override = parseOverride(env[envKey(name)]);
  const defaultDecision = runtimeDefault(name, env);

  if (override === undefined) return defaultDecision;

  if (isProductionEnv(env) && name === 'simulated_data' && override) {
    throw new Error('Refusing to enable simulated_data in staging/production');
  }

  if (isProductionEnv(env) && override && !productionCapabilityContract(env).satisfied) {
    return {
      name,
      enabled: false,
      source: 'production_contract',
      reason: 'production override ignored because provider contract is incomplete',
    };
  }

  return {
    name,
    enabled: override,
    source: 'env_override',
    reason: `${envKey(name)}=${env[envKey(name)]}`,
  };
}

export function evaluateFeatureGates(env: NodeJS.ProcessEnv = process.env): FeatureGateDecision[] {
  return FEATURE_NAMES.map(name => evaluateFeatureGate(name, env));
}

export function assertFeatureEnabled(name: FeatureGateName, env: NodeJS.ProcessEnv = process.env): void {
  const decision = evaluateFeatureGate(name, env);
  if (!decision.enabled) {
    throw new Error(`Feature gate ${name} is disabled: ${decision.reason}`);
  }
}
