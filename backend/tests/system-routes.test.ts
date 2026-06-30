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
    expect(capabilities.json()).toHaveProperty('production_contract');
    expect(capabilities.json()).toHaveProperty('feature_gates');
    await app.close();
  });

  test('reports feature gate decisions', async () => {
    const app = await build();

    const response = await app.inject({ method: 'GET', url: '/system/feature-gates' });
    const body = response.json();

    expect(response.statusCode).toBe(200);
    expect(body.runtime_mode).toBeDefined();
    expect(body.production_contract).toBeDefined();
    expect(body.feature_gates).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'live_llm' }),
      expect.objectContaining({ name: 'civilization_scheduler' }),
    ]));
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
    expect(body).toHaveProperty('gate_findings');
    expect(body.gate_findings).toHaveProperty('no_stub');
    await app.close();
  });

  test('reports readiness without overclaiming production status', async () => {
    const app = await build();

    const response = await app.inject({ method: 'GET', url: '/system/readiness' });
    const body = response.json();

    expect(response.statusCode).toBe(200);
    expect(body.verdict).toMatch(/partial|not_production_ready|fallbacks/);
    expect(body.production_ready).toBe(false);
    expect(body.termination_predicate_met).toBe(false);
    expect(body.honesty.status).toBe('not_fully_verified');
    expect(body.build_ledger.total_items).toBeGreaterThan(0);
    expect(body.production_contract.satisfied).toBe(false);
    expect(body.feature_gates).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'simulated_data' }),
    ]));
    await app.close();
  });
});
