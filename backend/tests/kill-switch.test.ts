import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { killSwitchService } from '../src/services/kill-switch.service';

async function applyMigration() {
  const migration = fs.readFileSync(
    path.resolve(__dirname, '../src/db/migrations/098_governance_kill_switch.sql'),
    'utf8'
  );
  await migrationDb.query(migration);
}

describe('governance kill switch', () => {
  beforeAll(async () => {
    await applyMigration();
  });

  test('activates idempotently and blocks guarded scope until deactivated', async () => {
    const actor = await identityAuthorityService.registerActor({
      actor_type: 'human',
      name: `kill-switch-actor-${Date.now()}`,
    });
    const scope = `learning:${Date.now()}`;

    const first = await killSwitchService.activate(scope, actor.id, 'unsafe promotion detected', {
      candidate: 'candidate-123',
    });
    const second = await killSwitchService.activate(scope, actor.id, 'duplicate activation');

    expect(second.id).toBe(first.id);
    expect(first.activated_event_log_id).toBeTruthy();
    await expect(killSwitchService.assertNotKilled(scope)).rejects.toThrow(/Kill switch active/);

    const deactivated = await killSwitchService.deactivate(scope, actor.id, 'manual review complete');
    expect(deactivated.active).toBe(false);
    expect(deactivated.deactivated_event_log_id).toBeTruthy();
    await expect(killSwitchService.assertNotKilled(scope)).resolves.toBeUndefined();
  });

  test('rejects deactivation when no active switch exists', async () => {
    const actor = await identityAuthorityService.registerActor({
      actor_type: 'human',
      name: `kill-switch-missing-${Date.now()}`,
    });

    await expect(killSwitchService.deactivate(`missing:${Date.now()}`, actor.id, 'not active')).rejects.toThrow(/No active/);
  });
});
