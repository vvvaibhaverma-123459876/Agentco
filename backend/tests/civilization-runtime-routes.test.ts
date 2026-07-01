import { describe, expect, test } from '@jest/globals';
import { build } from '../src/server';

function writeHeaders(): Record<string, string> {
  return process.env.AGENTCO_API_KEY ? { 'x-api-key': process.env.AGENTCO_API_KEY } : {};
}

describe('Civilization runtime API routes', () => {
  test('exposes the L14 runtime graph and persists reachability ticks through Fastify', async () => {
    const app = await build();
    try {
      const graph = await app.inject({
        method: 'GET',
        url: '/api/civilization/runtime/graph',
      });
      expect(graph.statusCode).toBe(200);
      const graphBody = graph.json();
      expect(graphBody.scope).toBe('core_l14_runtime_graph');
      expect(graphBody.graph.length).toBeGreaterThanOrEqual(10);
      expect(graphBody.graph.map((node: { id: string }) => node.id)).toEqual(expect.arrayContaining([
        'runtime_substrate_and_idempotency',
        'identity_authority',
        'resource_budgeting',
        'event_audit_outbox',
      ]));
      const graphRoutes = graphBody.graph.flatMap((node: { requiredRoutes: string[] }) => node.requiredRoutes);
      expect(graphRoutes).toContain('/api/civilization/runtime/reachability-tick');
      expect(graphRoutes).toContain('/api/civilization/runtime/dispatch-tick');
      expect(graphRoutes).toContain('/api/civilization/runtime/scheduler/run-once');

      const tick = await app.inject({
        method: 'POST',
        url: '/api/civilization/runtime/reachability-tick',
        headers: writeHeaders(),
        payload: { runtimeMode: 'fastify_route_l14_runtime' },
      });
      expect(tick.statusCode).toBe(201);
      const tickBody = tick.json();
      expect(tickBody.status).toBe('passed');
      expect(tickBody.runtimeMode).toBe('fastify_route_l14_runtime');
      expect(tickBody.missingTables).toEqual([]);
      expect(tickBody.missingRoutes).toEqual([]);
      expect(tickBody.tickType).toBe('reachability_gate');

      const scheduler = await app.inject({
        method: 'GET',
        url: '/api/civilization/runtime/scheduler',
      });
      expect(scheduler.statusCode).toBe(200);
      expect(typeof scheduler.json().running).toBe('boolean');

      const scheduledTick = await app.inject({
        method: 'POST',
        url: '/api/civilization/runtime/scheduler/run-once',
        headers: writeHeaders(),
        payload: { runtimeMode: 'fastify_scheduler_l14_runtime' },
      });
      expect(scheduledTick.statusCode).toBe(201);
      const scheduledBody = scheduledTick.json();
      expect(scheduledBody.tick.status).toBe('passed');
      expect(scheduledBody.scheduler.lastStatus).toBe('passed');
    } finally {
      await app.close();
    }
  });
});
