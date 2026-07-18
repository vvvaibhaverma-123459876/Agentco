import {
  assertAgentCanRunTask,
  ensureAgentRegistryActors,
  listAgentRegistryWithIdentities,
} from '../src/agent-registry';
import { db } from '../src/db/client';
import { build } from '../src/server';
import { provisionSignedActor, signHeaders } from './helpers/sign-request';

describe('agent runtime registry', () => {
  test('allows registered runnable agent task type', () => {
    expect(() => assertAgentCanRunTask('reviewer-agent', 'health_check')).not.toThrow();
  });

  test('allows durable decision task type for registered runnable agents', () => {
    expect(() => assertAgentCanRunTask('reviewer-agent', 'decision')).not.toThrow();
  });

  test('materializes registered agents as canonical active actor identities', async () => {
    await ensureAgentRegistryActors();
    const identities = await listAgentRegistryWithIdentities();
    const reviewer = identities.find((entry) => entry.agentId === 'reviewer-agent');
    expect(reviewer).toEqual(expect.objectContaining({
      actorStatus: 'active',
      identityStatus: 'active',
      modelName: 'qwen2.5-coder:7b',
      version: 'agent-registry-v1',
    }));

    const actor = await db.query(
      `SELECT a.actor_type, a.name, a.status, ai.agent_key, ai.model_name, ai.status AS identity_status
         FROM actors a
         JOIN agent_identities ai ON ai.actor_id = a.id
        WHERE a.id = $1`,
      [reviewer?.actorId]
    );
    expect(actor.rows).toEqual([
      expect.objectContaining({
        actor_type: 'agent',
        name: 'reviewer-agent',
        status: 'active',
        agent_key: 'reviewer-agent',
        model_name: 'qwen2.5-coder:7b',
        identity_status: 'active',
      }),
    ]);
  });

  test('rejects unsupported task type for runnable agent', () => {
    expect(() => assertAgentCanRunTask('reviewer-agent', 'unsupported_task')).toThrow(/cannot run task_type/);
  });

  test('agents route returns canonical actor identity fields', async () => {
    const app = await build();
    const response = await app.inject({
      method: 'GET',
      url: '/api/agents/reviewer-agent',
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual(expect.objectContaining({
      id: 'reviewer-agent',
      actor_id: expect.stringMatching(/^[0-9a-f-]{36}$/),
      actor_status: 'active',
      identity_status: 'active',
      model: 'qwen2.5-coder:7b',
      version: 'agent-registry-v1',
    }));
    await app.close();
  });

  test('dispatch route rejects unsupported task before enqueue', async () => {
    process.env.AGENTCO_API_KEY = 'test-api-key';
    const app = await build();
    // AUD-004: this route now requires a signed, credential-bound principal.
    const operator = await provisionSignedActor({ name: `dispatch-reject-${Date.now()}`, roles: ['civilization_operator'] });
    const url = '/api/agents/reviewer-agent/dispatch';
    const payload = { task_type: 'unsupported_task', payload: {} };
    const response = await app.inject({
      method: 'POST',
      url,
      headers: {
        'x-agentco-api-key': 'test-api-key', 'x-api-key': 'test-api-key',
        ...signHeaders({ actorId: operator.actorId, privateKey: operator.privateKey, method: 'POST', url, body: payload }),
      },
      payload,
    });

    expect(response.statusCode).toBe(422);
    expect(response.json()).toEqual(expect.objectContaining({ status: 'unsupported' }));
    await app.close();
  });
});
