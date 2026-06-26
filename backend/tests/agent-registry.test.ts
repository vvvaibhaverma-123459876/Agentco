import { assertAgentCanRunTask } from '../src/agent-registry';
import { build } from '../src/server';

describe('agent runtime registry', () => {
  test('allows registered runnable agent task type', () => {
    expect(() => assertAgentCanRunTask('reviewer-agent', 'health_check')).not.toThrow();
  });

  test('rejects unsupported task type for runnable agent', () => {
    expect(() => assertAgentCanRunTask('reviewer-agent', 'decision')).toThrow(/cannot run task_type/);
  });

  test('rejects unregistered runtime dispatch agents', () => {
    expect(() => assertAgentCanRunTask('ceo-agent', 'health_check')).toThrow(/not registered/);
  });

  test('dispatch route rejects unsupported task before enqueue', async () => {
    process.env.AGENTCO_API_KEY = 'test-api-key';
    const app = await build();
    const response = await app.inject({
      method: 'POST',
      url: '/api/agents/reviewer-agent/dispatch',
      headers: { 'x-agentco-api-key': 'test-api-key', 'x-api-key': 'test-api-key' },
      payload: { task_type: 'decision', payload: { options: ['approve'] } },
    });

    expect(response.statusCode).toBe(422);
    expect(response.json()).toEqual(expect.objectContaining({ status: 'unsupported' }));
    await app.close();
  });
});
