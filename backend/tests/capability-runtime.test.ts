import crypto from 'crypto';
import { build } from '../src/server';
import { capabilityRuntime } from '../src/services/capability-runtime.service';
import { rateLimiterService } from '../src/services/rate-limiter.service';
import { provisionSignedActor, signedInject, SignedActor } from './helpers/sign-request';

const API_KEY = 'capability-runtime-test-key';

function request(task_type = 'planning', overrides: Record<string, unknown> = {}) {
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
    ...overrides,
  };
}

describe('governed capability runtime routes', () => {
  const savedKey = process.env.AGENTCO_API_KEY;
  let app: Awaited<ReturnType<typeof build>>;
  let executor: SignedActor;
  let unprivileged: SignedActor;

  beforeAll(async () => {
    process.env.AGENTCO_API_KEY = API_KEY;
    app = await build();
    executor = await provisionSignedActor({ name: `capability-executor-${crypto.randomUUID()}`, roles: ['task_executor'] });
    unprivileged = await provisionSignedActor({ name: `capability-unprivileged-${crypto.randomUUID()}`, roles: [] });
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

  test('requires a signed principal even with a valid API key', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/v1/capabilities/execute',
      headers: { 'x-api-key': API_KEY },
      payload: request(),
    });

    expect(res.statusCode).toBe(401);
    expect(res.json().error).toBe('authenticated principal required');
  });

  test('AUD-004: rejects a credentialed principal that lacks capability.execute -- REGARDLESS of what the body claims', async () => {
    // The body still claims the full permission set; this must not matter -- the body's
    // authorization_context is never trusted, only the actor's REAL granted permissions.
    const res = await app.inject(
      signedInject({
        actorId: unprivileged.actorId,
        privateKey: unprivileged.privateKey,
        method: 'POST',
        url: '/v1/capabilities/execute',
        body: request('reasoning'),
        headers: { 'x-api-key': API_KEY },
      })
    );

    expect(res.statusCode).toBe(403);
    expect(res.json().permission).toBe('capability.execute');
  });

  test('executes deterministic capability request and retrieves attempt', async () => {
    const res = await app.inject(
      signedInject({
        actorId: executor.actorId,
        privateKey: executor.privateKey,
        method: 'POST',
        url: '/v1/capabilities/execute',
        body: request('evidence_evaluation'),
        headers: { 'x-api-key': API_KEY },
      })
    );

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

  test('AUD-004: a caller cannot impersonate another actor or self-grant permissions via the request body', async () => {
    // executor is genuinely authorized, but claims to BE a different actor in the body, and
    // claims a broader permission set than it was ever granted. Both must be silently overridden
    // by the verified principal -- the response's audit trail must reflect the REAL signer.
    const res = await app.inject(
      signedInject({
        actorId: executor.actorId,
        privateKey: executor.privateKey,
        method: 'POST',
        url: '/v1/capabilities/execute',
        body: request('planning', {
          actor: { id: 'someone-else-entirely', type: 'human' },
          authorization_context: { permissions: ['capability:execute', 'admin:all', 'treasury:drain'] },
        }),
        headers: { 'x-api-key': API_KEY },
      })
    );

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.authorization_events[0].actor_id).toBe(executor.actorId);
    expect(body.authorization_events[0].actor_id).not.toBe('someone-else-entirely');
  });

  test('AUD-004: the body-supplied authorization_context is irrelevant once a real permission is verified', async () => {
    // The body's empty permissions array would have caused a 'denied' response under the OLD
    // (pre-AUD-004) self-declared-authorization design. It must have no effect now -- the ONLY
    // authorization that matters is the credential-bound one already verified by requirePrincipal.
    const res = await app.inject(
      signedInject({
        actorId: executor.actorId,
        privateKey: executor.privateKey,
        method: 'POST',
        url: '/v1/capabilities/execute',
        body: request('reasoning', { authorization_context: { permissions: [] } }),
        headers: { 'x-api-key': API_KEY },
      })
    );

    expect(res.statusCode).toBe(200);
    expect(res.json().status).toBe('completed');
  });

  test('idempotent retry returns same attempt', async () => {
    const payload = request('planning');
    const first = await app.inject(
      signedInject({
        actorId: executor.actorId,
        privateKey: executor.privateKey,
        method: 'POST',
        url: '/v1/capabilities/execute',
        body: payload,
        headers: { 'x-api-key': API_KEY },
      })
    );
    const second = await app.inject(
      signedInject({
        actorId: executor.actorId,
        privateKey: executor.privateKey,
        method: 'POST',
        url: '/v1/capabilities/execute',
        body: payload,
        headers: { 'x-api-key': API_KEY },
      })
    );

    expect(first.statusCode).toBe(200);
    expect(second.statusCode).toBe(200);
    expect(second.json().idempotent_replay).toBe(true);
  });

  test('AUD-004: cancel requires capability.cancel, not just any signed principal', async () => {
    await app.inject(
      signedInject({
        actorId: executor.actorId,
        privateKey: executor.privateKey,
        method: 'POST',
        url: '/v1/capabilities/execute',
        body: request('planning'),
        headers: { 'x-api-key': API_KEY },
      })
    );

    const deniedCancel = await app.inject(
      signedInject({
        actorId: unprivileged.actorId,
        privateKey: unprivileged.privateKey,
        method: 'POST',
        url: '/v1/capabilities/attempts/attempt-planning/cancel',
        headers: { 'x-api-key': API_KEY },
      })
    );
    expect(deniedCancel.statusCode).toBe(403);

    const allowedCancel = await app.inject(
      signedInject({
        actorId: executor.actorId,
        privateKey: executor.privateKey,
        method: 'POST',
        url: '/v1/capabilities/attempts/attempt-planning/cancel',
        headers: { 'x-api-key': API_KEY },
      })
    );
    // The deterministic provider completes synchronously, so by the time cancel runs there's
    // nothing left in flight -- the service correctly no-ops on an already-completed attempt.
    // What this proves is the permission gate itself: 403 for the unprivileged actor above,
    // 200 (request admitted) for the privileged one.
    expect(allowedCancel.statusCode).toBe(200);
    expect(allowedCancel.json().status).toBe('completed');
  });
});
