import { assertAgentCanRunTask } from '../src/agent-registry';
import { build } from '../src/server';

describe('agent runtime registry', () => {
  test('allows registered runnable agent task type', () => {
    expect(() => assertAgentCanRunTask('reviewer-agent', 'health_check')).not.toThrow();
  });

  test('allows durable decision task type for registered runnable agents', () => {
    expect(() => assertAgentCanRunTask('reviewer-agent', 'decision')).not.toThrow();
  });

  test('rejects unsupported task type for runnable agent', () => {
    expect(() => assertAgentCanRunTask('reviewer-agent', 'unsupported_task')).toThrow(/cannot run task_type/);
  });

  test('dispatch route rejects unsupported task before enqueue', async () => {
    process.env.AGENTCO_API_KEY = 'test-api-key';
    const app = await build();
    const response = await app.inject({
      method: 'POST',
      url: '/api/agents/reviewer-agent/dispatch',
      headers: { 'x-agentco-api-key': 'test-api-key', 'x-api-key': 'test-api-key' },
      payload: { task_type: 'unsupported_task', payload: {} },
    });

    expect(response.statusCode).toBe(422);
    expect(response.json()).toEqual(expect.objectContaining({ status: 'unsupported' }));
    await app.close();
  });
});
