import { describe, expect, test } from '@jest/globals';
import { db } from '../src/db/client';
import { civilizationRuntimeService } from '../src/services/civilization-runtime.service';

describe('CivilizationRuntimeService reachability gate', () => {
  test('persists a coordinator reachability tick for the core L14 runtime graph', async () => {
    const tick = await civilizationRuntimeService.runReachabilityTick('jest_l14_runtime');

    expect(tick.status).toBe('passed');
    expect(tick.missingTables).toEqual([]);
    expect(tick.missingRoutes).toEqual([]);
    expect(tick.nodes.length).toBeGreaterThanOrEqual(10);
    expect(tick.nodes.every(node => node.status === 'reachable')).toBe(true);
    expect(tick.nodes.map(node => node.id)).toEqual(expect.arrayContaining([
      'runtime_substrate_and_idempotency',
      'identity_authority',
      'resource_budgeting',
      'event_audit_outbox',
      'constitution_and_policy',
    ]));

    const stored = await db.query<{ tick_type: string; status: string }>(
      `SELECT t.tick_type, r.status
         FROM civilization_coordinator_ticks t
         JOIN civilization_vertical_slice_runs r ON r.id = t.run_id
        WHERE t.id = $1`,
      [tick.tickId],
    );

    expect(stored.rowCount).toBe(1);
    expect(stored.rows[0].tick_type).toBe('reachability_gate');
    expect(stored.rows[0].status).toBe('passed');
  });
});
