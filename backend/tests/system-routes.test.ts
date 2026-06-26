import { build } from '../src/server';

describe('system routes', () => {
  test('reports runtime mode and capabilities', async () => {
    const app = await build();

    const runtime = await app.inject({ method: 'GET', url: '/system/runtime-mode' });
    const capabilities = await app.inject({ method: 'GET', url: '/system/capabilities' });

    expect(runtime.statusCode).toBe(200);
    expect(runtime.json()).toHaveProperty('runtime_mode');
    expect(capabilities.statusCode).toBe(200);
    expect(capabilities.json()).toHaveProperty('providers');
    await app.close();
  });

  test('reports build ledger rollups without marking complete', async () => {
    const app = await build();

    const response = await app.inject({ method: 'GET', url: '/system/build-status' });
    const body = response.json();

    expect(response.statusCode).toBe(200);
    expect(body.rollups.total_items).toBeGreaterThan(0);
    expect(body.rollups.percent_verified).toBeLessThan(100);
    expect(body.meta.termination_predicate_met).toBe(false);
    await app.close();
  });
});
