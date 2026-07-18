import { describe, expect, test } from '@jest/globals';
import { build } from '../src/server';
import { provisionSignedActor, signHeaders } from './helpers/sign-request';

function writeHeaders(): Record<string, string> {
  return process.env.AGENTCO_API_KEY ? { 'x-api-key': process.env.AGENTCO_API_KEY } : {};
}

describe('Civilization runtime API routes', () => {
  test('exposes the L14 runtime graph and persists reachability ticks through Fastify', async () => {
    const app = await build();
    // AUD-004: these routes now require a signed, credential-bound principal.
    const operator = await provisionSignedActor({ name: `runtime-route-${Date.now()}`, roles: ['civilization_operator'] });
    const signedHeaders = (method: string, url: string, body?: unknown) =>
      ({ ...writeHeaders(), ...signHeaders({ actorId: operator.actorId, privateKey: operator.privateKey, method, url, body }) });
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

      const tickUrl = '/api/civilization/runtime/reachability-tick';
      const tickBodyPayload = { runtimeMode: 'fastify_route_l14_runtime' };
      const tick = await app.inject({
        method: 'POST',
        url: tickUrl,
        headers: signedHeaders('POST', tickUrl, tickBodyPayload),
        payload: tickBodyPayload,
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

      const schedulerUrl = '/api/civilization/runtime/scheduler/run-once';
      const schedulerBodyPayload = { runtimeMode: 'fastify_scheduler_l14_runtime' };
      const scheduledTick = await app.inject({
        method: 'POST',
        url: schedulerUrl,
        headers: signedHeaders('POST', schedulerUrl, schedulerBodyPayload),
        payload: schedulerBodyPayload,
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
