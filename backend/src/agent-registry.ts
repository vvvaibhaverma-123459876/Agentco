export interface AgentRegistryEntry {
  agentId: string;
  department: string;
  runtimeStatus: 'runnable' | 'library_only' | 'unsupported';
  allowedTaskTypes: string[];
  modelTier: 'standard' | 'frontier' | 'code' | 'none';
  capabilityTags: string[];
}

const AGENT_REGISTRY: AgentRegistryEntry[] = [
  entry('ceo-agent', 'executive', 'frontier', ['strategy', 'governance']),
  entry('cfo-agent', 'executive', 'standard', ['finance', 'budget']),
  entry('coo-agent', 'executive', 'standard', ['operations', 'coordination']),
  entry('pm-agent', 'product', 'standard', ['product', 'roadmap']),
  entry('research-agent', 'product', 'standard', ['research', 'evidence']),
  entry('prioritizer-agent', 'product', 'standard', ['prioritization']),
  entry('architect-agent', 'engineering', 'code', ['architecture', 'code_review']),
  entry('coder-agent', 'engineering', 'code', ['code_generation']),
  entry('reviewer-agent', 'engineering', 'code', ['code_review', 'risk_review']),
  entry('devops-agent', 'engineering', 'code', ['deployment', 'operations']),
  entry('ux-agent', 'design', 'standard', ['ux']),
  entry('brand-agent', 'design', 'standard', ['brand']),
  entry('ab-agent', 'design', 'standard', ['experimentation']),
  entry('sdr-agent', 'sales', 'standard', ['sales_development']),
  entry('ae-agent', 'sales', 'standard', ['sales']),
  entry('revops-agent', 'sales', 'standard', ['revenue_operations']),
  entry('content-agent', 'marketing', 'standard', ['content']),
  entry('seo-agent', 'marketing', 'standard', ['seo']),
  entry('ads-agent', 'marketing', 'standard', ['advertising']),
  entry('analytics-agent', 'marketing', 'standard', ['analytics']),
  entry('support-agent', 'customer_experience', 'standard', ['support']),
  entry('success-agent', 'customer_experience', 'standard', ['customer_success']),
  entry('voice-agent', 'customer_experience', 'standard', ['voice_of_customer']),
  entry('performance-agent', 'people_ops', 'standard', ['performance']),
  entry('recruiter-agent', 'people_ops', 'standard', ['recruiting']),
  entry('config-agent', 'people_ops', 'standard', ['configuration']),
  entry('contract-agent', 'legal', 'standard', ['contract_review']),
  entry('risk-agent', 'legal', 'standard', ['risk']),
  entry('privacy-agent', 'legal', 'standard', ['privacy']),
  entry('calibration-reasoner', 'calibration', 'standard', ['calibration', 'scoring']),
];

function entry(
  agentId: string,
  department: string,
  modelTier: AgentRegistryEntry['modelTier'],
  capabilityTags: string[],
): AgentRegistryEntry {
  return {
    agentId,
    department,
    runtimeStatus: 'runnable',
    allowedTaskTypes: ['health_check', 'record_observation', 'llm_call', 'calibration', 'review', 'decision'],
    modelTier,
    capabilityTags,
  };
}

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
