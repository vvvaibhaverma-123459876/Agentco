import { build } from '../src/server';

const API_KEY = { 'x-agentco-api-key': 'dev-api-key' };

describe('governed API boundaries', () => {
  test('route auth required for mutation', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/institutions', payload: { name: 'NoAuth' } });
    expect(res.statusCode).toBe(401);
    await app.close();
  });

  test('idempotency prevents duplicate institution mutation', async () => {
    const app = await build();
    const first = await app.inject({
      method: 'POST',
      url: '/institutions',
      headers: { ...API_KEY, 'idempotency-key': 'same-inst' },
      payload: { name: 'Idempotent Institution' },
    });
    const second = await app.inject({
      method: 'POST',
      url: '/institutions',
      headers: { ...API_KEY, 'idempotency-key': 'same-inst' },
      payload: { name: 'Idempotent Institution' },
    });
    expect(first.statusCode).toBe(201);
    expect(JSON.parse(second.payload).id).toBe(JSON.parse(first.payload).id);
    await app.close();
  });

  test('audit log written for mutation', async () => {
    const app = await build();
    const created = await app.inject({
      method: 'POST',
      url: '/institutions',
      headers: API_KEY,
      payload: { name: 'Audited Institution' },
    });
    const id = JSON.parse(created.payload).id;
    const audit = await app.inject({ method: 'GET', url: '/audit/mutations' });
    expect(audit.statusCode).toBe(200);
    expect(JSON.parse(audit.payload).events.some((e: { entityId: string }) => e.entityId === id)).toBe(true);
    await app.close();
  });

  test('invalid role rejected and valid role accepted', async () => {
    const app = await build();
    const created = await app.inject({
      method: 'POST',
      url: '/institutions',
      headers: API_KEY,
      payload: { name: 'Role Institution' },
    });
    const id = JSON.parse(created.payload).id;
    const invalid = await app.inject({
      method: 'POST',
      url: `/institutions/${id}/agents`,
      headers: API_KEY,
      payload: { agent_id: 'a1', role: 'self_certifier' },
    });
    expect(invalid.statusCode).toBe(400);
    const valid = await app.inject({
      method: 'POST',
      url: `/institutions/${id}/agents`,
      headers: API_KEY,
      payload: { agent_id: 'a1', role: 'engineer' },
    });
    expect(valid.statusCode).toBe(201);
    await app.close();
  });
});
