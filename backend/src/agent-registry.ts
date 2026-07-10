import { db } from './db/client';

export interface AgentRegistryEntry {
  agentId: string;
  department: string;
  runtimeStatus: 'runnable' | 'library_only' | 'unsupported';
  allowedTaskTypes: string[];
  modelTier: 'standard' | 'frontier' | 'code' | 'none';
  capabilityTags: string[];
}

export interface AgentRegistryIdentityEntry extends AgentRegistryEntry {
  actorId: string;
  actorStatus: 'active' | 'suspended' | 'revoked';
  identityStatus: 'active' | 'suspended' | 'revoked';
  modelName: string;
  version: string;
}

const AGENT_REGISTRY: AgentRegistryEntry[] = [
  entry('ceo-agent', 'executive', 'frontier', ['strategy', 'governance']),
  entry('cfo-agent', 'executive', 'standard', ['finance', 'budget']),
  entry('coo-agent', 'executive', 'standard', ['operations', 'coordination']),
  entry('pm-agent', 'product', 'standard', ['product', 'roadmap']),
  entry('research-agent', 'product', 'standard', ['research', 'evidence'], 'runnable', ['record_observation']),
  entry('prioritizer-agent', 'product', 'standard', ['prioritization'], 'unsupported'),
  entry('architect-agent', 'engineering', 'code', ['architecture', 'code_review'], 'unsupported'),
  entry('coder-agent', 'engineering', 'code', ['code_generation']),
  entry('reviewer-agent', 'engineering', 'code', ['code_review', 'risk_review']),
  entry('devops-agent', 'engineering', 'code', ['deployment', 'operations']),
  entry('ux-agent', 'design', 'standard', ['ux'], 'unsupported'),
  entry('brand-agent', 'design', 'standard', ['brand'], 'unsupported'),
  entry('ab-agent', 'design', 'standard', ['experimentation'], 'unsupported'),
  entry('sdr-agent', 'sales', 'standard', ['sales_development'], 'unsupported'),
  entry('ae-agent', 'sales', 'standard', ['sales'], 'unsupported'),
  entry('revops-agent', 'sales', 'standard', ['revenue_operations'], 'unsupported'),
  entry('content-agent', 'marketing', 'standard', ['content'], 'unsupported'),
  entry('seo-agent', 'marketing', 'standard', ['seo'], 'unsupported'),
  entry('ads-agent', 'marketing', 'standard', ['advertising'], 'unsupported'),
  entry('analytics-agent', 'marketing', 'standard', ['analytics'], 'unsupported'),
  entry('support-agent', 'customer_experience', 'standard', ['support'], 'unsupported'),
  entry('success-agent', 'customer_experience', 'standard', ['customer_success'], 'unsupported'),
  entry('voice-agent', 'customer_experience', 'standard', ['voice_of_customer'], 'unsupported'),
  entry('performance-agent', 'people_ops', 'standard', ['performance'], 'unsupported'),
  entry('recruiter-agent', 'people_ops', 'standard', ['recruiting'], 'unsupported'),
  entry('config-agent', 'people_ops', 'standard', ['configuration']),
  entry('contract-agent', 'legal', 'standard', ['contract_review'], 'unsupported'),
  entry('risk-agent', 'legal', 'standard', ['risk'], 'unsupported'),
  entry('privacy-agent', 'legal', 'standard', ['privacy']),
  entry('calibration-reasoner', 'calibration', 'standard', ['calibration', 'scoring'], 'runnable', ['record_observation']),
];

function entry(
  agentId: string,
  department: string,
  modelTier: AgentRegistryEntry['modelTier'],
  capabilityTags: string[],
  runtimeStatus: AgentRegistryEntry['runtimeStatus'] = 'runnable',
  allowedTaskTypes: string[] = ['health_check', 'record_observation', 'llm_call', 'calibration', 'review', 'decision'],
): AgentRegistryEntry {
  return {
    agentId,
    department,
    runtimeStatus,
    allowedTaskTypes,
    modelTier,
    capabilityTags,
  };
}

const AGENT_MODEL: Record<string, string> = {
  'ceo-agent': 'phi4',
  'cfo-agent': 'phi4',
  'coo-agent': 'phi4',
  'synthesis-agent': 'phi4',
  'calibration-reasoner': 'phi4',
  'coder-agent': 'qwen2.5-coder:7b',
  'reviewer-agent': 'qwen2.5-coder:7b',
};

export function modelForAgent(agentId: string): string {
  return AGENT_MODEL[agentId] ?? 'qwen2.5:7b';
}

export function getAgentRegistryEntry(agentId: string): AgentRegistryEntry | null {
  return AGENT_REGISTRY.find(entry => entry.agentId === agentId) ?? null;
}

export function listAgentRegistry(): AgentRegistryEntry[] {
  return [...AGENT_REGISTRY];
}

export async function ensureAgentRegistryActors(): Promise<void> {
  for (const agent of AGENT_REGISTRY) {
    const actor = await db.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('agent', $1, $2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET metadata_json = EXCLUDED.metadata_json,
                     updated_at = now()
       RETURNING id`,
      [
        agent.agentId,
        JSON.stringify({
          department: agent.department,
          runtime_status: agent.runtimeStatus,
          allowed_task_types: agent.allowedTaskTypes,
          model_tier: agent.modelTier,
          capability_tags: agent.capabilityTags,
        }),
      ]
    );
    await db.query(
      `INSERT INTO agent_identities
         (actor_id, agent_key, model_name, version, status)
       VALUES ($1,$2,$3,$4,'active')
       ON CONFLICT (agent_key)
       DO UPDATE SET model_name = EXCLUDED.model_name,
                     version = EXCLUDED.version,
                     status = 'active'`,
      [actor.rows[0].id, agent.agentId, modelForAgent(agent.agentId), 'agent-registry-v1']
    );
  }
}

export async function listAgentRegistryWithIdentities(): Promise<AgentRegistryIdentityEntry[]> {
  await ensureAgentRegistryActors();
  const identities = await db.query<{
    actor_id: string;
    agent_key: string;
    model_name: string;
    version: string;
    identity_status: 'active' | 'suspended' | 'revoked';
    actor_status: 'active' | 'suspended' | 'revoked';
  }>(
    `SELECT ai.actor_id,
            ai.agent_key,
            ai.model_name,
            ai.version,
            ai.status AS identity_status,
            a.status AS actor_status
       FROM agent_identities ai
       JOIN actors a ON a.id = ai.actor_id
      WHERE ai.agent_key = ANY($1)
      ORDER BY ai.agent_key ASC`,
    [AGENT_REGISTRY.map(agent => agent.agentId)]
  );
  const byKey = new Map(identities.rows.map(identity => [identity.agent_key, identity]));
  return AGENT_REGISTRY.map(agent => {
    const identity = byKey.get(agent.agentId);
    if (!identity) {
      throw new Error(`agent identity was not materialized: ${agent.agentId}`);
    }
    return {
      ...agent,
      actorId: identity.actor_id,
      actorStatus: identity.actor_status,
      identityStatus: identity.identity_status,
      modelName: identity.model_name,
      version: identity.version,
    };
  });
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
