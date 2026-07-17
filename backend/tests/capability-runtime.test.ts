import { build } from '../src/server';
import { capabilityRuntime } from '../src/services/capability-runtime.service';
import { rateLimiterService } from '../src/services/rate-limiter.service';

const API_KEY = 'capability-runtime-test-key';

function request(task_type = 'planning') {
  return {
    protocol_version: 'agentco-capability-v1',
    request_id: `req-${task_type}`,
    attempt_id: `attempt-${task_type}`,
    actor: { id: 'tester', type: 'test' },
    tenant: 'test-tenant',
    task_type,
    prompt: `Execute ${task_type}`,
    structured_input: {},
    context: {},
    memory_policy: {},
    tool_allowlist: ['json_transformer'],
    provider_policy: { provider: 'deterministic_local_reference' },
    budget: { max_wall_ms: 5000, max_provider_calls: 1 },
    deadline: null,
    idempotency_key: `idem-${task_type}`,
    authorization_context: { permissions: ['capability:execute'] },
    trace_context: { trace_id: `trace-${task_type}` },
  };
}

describe('governed capability runtime routes', () => {
  const savedKey = process.env.AGENTCO_API_KEY;
  let app: Awaited<ReturnType<typeof build>>;

  beforeAll(async () => {
    process.env.AGENTCO_API_KEY = API_KEY;
    app = await build();
  });

  afterEach(() => {
    capabilityRuntime.resetForTests();
    rateLimiterService.resetAll();
  });

  afterAll(async () => {
    await app.close();
    if (savedKey === undefined) delete process.env.AGENTCO_API_KEY;
    else process.env.AGENTCO_API_KEY = savedKey;
  });

  test('requires API key', async () => {
    const res = await app.inject({ method: 'POST', url: '/v1/capabilities/execute', payload: request() });

    expect(res.statusCode).toBe(401);
  });

  test('executes deterministic capability request and retrieves attempt', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/v1/capabilities/execute',
      headers: { 'x-api-key': API_KEY },
      payload: request('evidence_evaluation'),
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.status).toBe('completed');
    expect(body.provider).toBe('deterministic_local_reference');

    const fetched = await app.inject({
      method: 'GET',
      url: '/v1/capabilities/attempts/attempt-evidence_evaluation',
      headers: { 'x-api-key': API_KEY },
    });
    expect(fetched.statusCode).toBe(200);
    expect(fetched.json().attempt_id).toBe('attempt-evidence_evaluation');
  });

  test('denies runtime authorization without capability permission', async () => {
    const payload = request('reasoning');
    payload.authorization_context = { permissions: [] };
    const res = await app.inject({
      method: 'POST',
      url: '/v1/capabilities/execute',
      headers: { 'x-api-key': API_KEY },
      payload,
    });

    expect(res.statusCode).toBe(403);
    expect(res.json().status).toBe('denied');
  });

  test('idempotent retry returns same attempt', async () => {
    const payload = request('planning');
    const first = await app.inject({
      method: 'POST',
      url: '/v1/capabilities/execute',
      headers: { 'x-api-key': API_KEY },
      payload,
    });
    const second = await app.inject({
      method: 'POST',
      url: '/v1/capabilities/execute',
      headers: { 'x-api-key': API_KEY },
      payload,
    });

    expect(first.statusCode).toBe(200);
    expect(second.statusCode).toBe(200);
    expect(second.json().idempotent_replay).toBe(true);
  });
});
