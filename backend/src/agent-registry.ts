export interface AgentRegistryEntry {
  agentId: string;
  department: string;
  runtimeStatus: 'runnable' | 'library_only' | 'unsupported';
  allowedTaskTypes: string[];
  modelTier: 'standard' | 'frontier' | 'code' | 'none';
  capabilityTags: string[];
}

const AGENT_REGISTRY: AgentRegistryEntry[] = [
  {
    agentId: 'reviewer-agent',
    department: 'engineering',
    runtimeStatus: 'runnable',
    allowedTaskTypes: ['health_check', 'record_observation', 'llm_call', 'calibration'],
    modelTier: 'code',
    capabilityTags: ['code_review', 'risk_review'],
  },
  {
    agentId: 'calibration-reasoner',
    department: 'calibration',
    runtimeStatus: 'runnable',
    allowedTaskTypes: ['health_check', 'record_observation', 'llm_call', 'calibration'],
    modelTier: 'standard',
    capabilityTags: ['calibration', 'scoring'],
  },
  {
    agentId: 'research-agent',
    department: 'product',
    runtimeStatus: 'runnable',
    allowedTaskTypes: ['health_check', 'record_observation', 'llm_call'],
    modelTier: 'standard',
    capabilityTags: ['research', 'evidence'],
  },
];

export function getAgentRegistryEntry(agentId: string): AgentRegistryEntry | null {
  return AGENT_REGISTRY.find(entry => entry.agentId === agentId) ?? null;
}

export function listAgentRegistry(): AgentRegistryEntry[] {
  return [...AGENT_REGISTRY];
}

export function assertAgentCanRunTask(agentId: string, taskType: string): void {
  const entry = getAgentRegistryEntry(agentId);
  if (!entry) {
    throw new Error(`agent ${agentId} is not registered for runtime dispatch`);
  }
  if (entry.runtimeStatus !== 'runnable') {
    throw new Error(`agent ${agentId} is ${entry.runtimeStatus}, not runnable`);
  }
  if (!entry.allowedTaskTypes.includes(taskType)) {
    throw new Error(`agent ${agentId} cannot run task_type ${taskType}`);
  }
}
