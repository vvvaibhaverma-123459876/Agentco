import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { institutionGovernance } from '../src/services/institution-governance.service';
import { missionService } from '../src/services/mission.service';
import { civilizationOs } from '../src/services/civilization-os.service';
import { killSwitchService } from '../src/services/kill-switch.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql', '135_governance.sql', '136_judiciary.sql',
    '137_collective_epistemics.sql', '138_safe_evolution.sql', '139_capability_expansion.sql',
    '140_civilization_os.sql',
  ]) {
    await migrationDb.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${file}`), 'utf8'));
  }
}

async function actor(prefix: string): Promise<string> {
  const a = await identityAuthorityService.registerActor({
    actor_type: 'human', name: `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`,
  });
  return a.id;
}

async function plannedMission(op: string): Promise<string> {
  const m = await missionService.createMission({ title: `OS mission ${Date.now()}-${Math.random()}`, actor_id: op });
  for (const [to, reason] of [['triaged', 't'], ['approved', 'a'], ['funded', 'f'], ['planned', 'p']] as Array<[string, string]>) {
    await missionService.transitionMission({ mission_id: m.id, to_status: to as any, actor_id: op, reason });
  }
  return m.id;
}

describe('civilization operating system (C12)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
    await institutionGovernance.ensureMandatoryInstitutions();
    // Clean slate for OS mode so prior suites don't leave it paused.
    await civilizationOs.setMode('running');
  });

  test('a tick sources and routes pending missions, and re-ticking does not duplicate routing (restart-safe)', async () => {
    const op = await actor('os-route');
    const missionId = await plannedMission(op);

    const before = await db.query(`SELECT lead_institution_id FROM missions WHERE id = $1`, [missionId]);
    expect(before.rows[0].lead_institution_id).toBeNull();

    const tick1 = await civilizationOs.tick();
    expect(tick1.was_leader).toBe(true);
    expect(tick1.work_routed).toBeGreaterThanOrEqual(1);

    const assigned = await db.query(`SELECT lead_institution_id FROM missions WHERE id = $1`, [missionId]);
    expect(assigned.rows[0].lead_institution_id).not.toBeNull();
    const firstInstitution = assigned.rows[0].lead_institution_id;

    // Re-tick: the already-routed mission is not re-sourced (idempotent / no duplicate work).
    const tick2 = await civilizationOs.tick();
    const stillAssigned = await db.query(`SELECT lead_institution_id FROM missions WHERE id = $1`, [missionId]);
    expect(stillAssigned.rows[0].lead_institution_id).toBe(firstInstitution);
    // No duplicate routing events for this mission.
    const routeEvents = await db.query(
      `SELECT COUNT(*)::int c FROM event_log WHERE event_type = 'civilization_os.mission_routed' AND object_id = $1`,
      [missionId]
    );
    expect(Number(routeEvents.rows[0].c)).toBe(1);
    expect(tick2.tick_number).toBeGreaterThan(tick1.tick_number);
  });

  test('tick numbers are monotonic and heartbeat advances', async () => {
    const a = await civilizationOs.tick();
    const b = await civilizationOs.tick();
    expect(b.tick_number).toBe(a.tick_number + 1);
    const state = await db.query(`SELECT tick_count, heartbeat_at FROM civ_os_state WHERE id = 1`);
    expect(Number(state.rows[0].tick_count)).toBe(b.tick_number);
    expect(state.rows[0].heartbeat_at).not.toBeNull();
  });

  test('the kill switch stops protected ticks; releasing it resumes them', async () => {
    const op = await actor('os-kill');
    await killSwitchService.activate('civilization.os', op, 'incident containment');
    const killed = await civilizationOs.tick();
    expect(killed.was_leader).toBe(false);
    expect(killed.skipped_reason).toMatch(/kill switch/);

    await killSwitchService.deactivate('civilization.os', op, 'incident resolved');
    const resumed = await civilizationOs.tick();
    expect(resumed.was_leader).toBe(true);
    expect(resumed.skipped_reason).toBeUndefined();
  });

  test('paused mode ticks but sources no new work; drained mode still sweeps', async () => {
    const op = await actor('os-pause');
    const missionId = await plannedMission(op);
    await civilizationOs.pause(op);
    const paused = await civilizationOs.tick();
    expect(paused.mode).toBe('paused');
    expect(paused.skipped_reason).toMatch(/mode paused/);
    const stillUnrouted = await db.query(`SELECT lead_institution_id FROM missions WHERE id = $1`, [missionId]);
    expect(stillUnrouted.rows[0].lead_institution_id).toBeNull();

    await civilizationOs.drain(op);
    const drained = await civilizationOs.tick();
    expect(drained.mode).toBe('drained');
    // Drained sweeps run (leader), but no new work sourced.
    expect(drained.was_leader).toBe(true);
    const stillUnrouted2 = await db.query(`SELECT lead_institution_id FROM missions WHERE id = $1`, [missionId]);
    expect(stillUnrouted2.rows[0].lead_institution_id).toBeNull();

    await civilizationOs.resume(op);
    const resumed = await civilizationOs.tick();
    expect(resumed.mode).toBe('running');
    const routed = await db.query(`SELECT lead_institution_id FROM missions WHERE id = $1`, [missionId]);
    expect(routed.rows[0].lead_institution_id).not.toBeNull();
  });

  test('the status projection reports civilization-wide counts, and recovery reports without creating work', async () => {
    await civilizationOs.setMode('running');
    const status = await civilizationOs.statusProjection();
    expect(status.civilization_id).toBeTruthy();
    expect(Number(status.societies_active)).toBeGreaterThanOrEqual(0);
    expect(Number(status.institutions_active)).toBeGreaterThanOrEqual(10); // mandatory institutions seeded

    const recovery = await civilizationOs.recoverAndReport();
    expect(recovery.mode).toBe('running');
    expect(recovery.last_tick).toBeGreaterThan(0);
    expect(recovery.status.civilization_id).toBe(status.civilization_id);

    // Tick log is append-only.
    const tick = await db.query(`SELECT id FROM civ_os_ticks ORDER BY tick_number DESC LIMIT 1`);
    await expect(
      db.query(`UPDATE civ_os_ticks SET work_routed = 999 WHERE id = $1`, [tick.rows[0].id])
    ).rejects.toThrow(/append-only/);
  });
});
