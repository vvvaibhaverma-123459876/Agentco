import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel, KERNEL_PROTECTED_INVARIANTS } from '../src/services/civilization-kernel.service';

async function applyMigration() {
  const migration = fs.readFileSync(
    path.resolve(__dirname, '../src/db/migrations/129_civilization_kernel.sql'),
    'utf8'
  );
  await migrationDb.query(migration);
}

async function registerActor(prefix: string): Promise<string> {
  const actor = await identityAuthorityService.registerActor({
    actor_type: 'human',
    name: `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`,
  });
  return actor.id;
}

describe('civilization kernel (C1)', () => {
  beforeAll(async () => {
    await applyMigration();
  });

  test('bootstrap is idempotent and seeds charter, invariants, and jurisdiction', async () => {
    const first = await civilizationKernel.ensureCivilizationRoot();
    expect(first.status).toBe('active');
    expect(first.name).toBe('AgentCo');

    const second = await civilizationKernel.ensureCivilizationRoot();
    expect(second.id).toBe(first.id);

    const charter = await civilizationKernel.getActiveCharter(first.id);
    expect(charter).not.toBeNull();
    expect(charter!.version_number).toBeGreaterThanOrEqual(1);

    const invariants = await civilizationKernel.listProtectedInvariants(first.id);
    const keys = invariants.map(i => i.invariant_key);
    for (const invariant of KERNEL_PROTECTED_INVARIANTS) {
      expect(keys).toContain(invariant.key);
    }
    expect(invariants.every(i => i.tier === 0)).toBe(true);

    const jurisdiction = await db.query(
      `SELECT jurisdiction_key FROM civilization_jurisdictions WHERE civilization_id = $1`,
      [first.id]
    );
    expect(jurisdiction.rows.map((r: any) => r.jurisdiction_key)).toContain('global');

    const events = await db.query(
      `SELECT event_type FROM event_log WHERE object_type = 'civilization' AND object_id = $1`,
      [first.id]
    );
    expect(events.rows.map((r: any) => r.event_type)).toContain('civilization.created');
  });

  test('only one active civilization root can exist', async () => {
    const actorId = await registerActor('kernel-second-civ');
    const second = await civilizationKernel.createCivilization({
      name: `Parallel-Civ-${Date.now()}`,
      created_by_actor_id: actorId,
    });
    expect(second.status).toBe('forming');
    await expect(civilizationKernel.activateCivilization(second.id, actorId)).rejects.toThrow();
    // Clean terminal state for the leftover forming civilization.
    await civilizationKernel.transitionStatus({
      civilization_id: second.id,
      to_status: 'retired',
      actor_id: actorId,
      reason: 'test cleanup',
    });
  });

  test('illegal lifecycle transitions are rejected and status cannot change outside the service', async () => {
    const root = await civilizationKernel.ensureCivilizationRoot();
    const actorId = await registerActor('kernel-illegal');

    await expect(civilizationKernel.transitionStatus({
      civilization_id: root.id,
      to_status: 'recovering',
      actor_id: actorId,
      reason: 'invalid direct move',
    })).rejects.toThrow(/illegal civilization transition/);

    await expect(civilizationKernel.transitionStatus({
      civilization_id: root.id,
      to_status: 'emergency',
      actor_id: actorId,
      reason: 'must use enterEmergency',
    })).rejects.toThrow(/enterEmergency/);

    await expect(
      db.query(`UPDATE civilizations SET status = 'suspended' WHERE id = $1`, [root.id])
    ).rejects.toThrow(/KERNEL GUARD/);
  });

  test('retired civilizations are immutable', async () => {
    const actorId = await registerActor('kernel-retire');
    const civ = await civilizationKernel.createCivilization({
      name: `Retire-Test-${Date.now()}`,
      created_by_actor_id: actorId,
    });
    await civilizationKernel.transitionStatus({
      civilization_id: civ.id,
      to_status: 'retired',
      actor_id: actorId,
      reason: 'test retirement',
    });
    await expect(
      db.query(`UPDATE civilizations SET description = 'mutated' WHERE id = $1`, [civ.id])
    ).rejects.toThrow(/retired civilization .* is immutable/);
    await expect(civilizationKernel.transitionStatus({
      civilization_id: civ.id,
      to_status: 'active',
      actor_id: actorId,
      reason: 'resurrect attempt',
    })).rejects.toThrow(/illegal civilization transition/);
    await expect(
      db.query(`DELETE FROM civilizations WHERE id = $1`, [civ.id])
    ).rejects.toThrow(/may not be deleted/);
  });

  test('emergency powers require authorization and expiry, then auto-expire into recovery', async () => {
    const root = await civilizationKernel.ensureCivilizationRoot();
    const actorId = await registerActor('kernel-emergency');
    const scope = `containment-${Date.now()}`;

    await expect(civilizationKernel.enterEmergency({
      civilization_id: root.id,
      scope,
      reason: 'missing decision ref',
      actor_id: actorId,
      authorized_decision_ref: '',
      ttl_seconds: 3600,
    })).rejects.toThrow(/authorized_decision_ref/);

    await expect(civilizationKernel.enterEmergency({
      civilization_id: root.id,
      scope,
      reason: 'bad ttl',
      actor_id: actorId,
      authorized_decision_ref: 'decision:test',
      ttl_seconds: 0,
    })).rejects.toThrow(/ttl_seconds/);

    const entered = await civilizationKernel.enterEmergency({
      civilization_id: root.id,
      scope,
      reason: 'containment drill',
      actor_id: actorId,
      authorized_decision_ref: 'decision:test-drill',
      ttl_seconds: 3600,
    });
    expect(entered.civilization.status).toBe('emergency');
    expect(entered.emergency.status).toBe('active');

    // A second active emergency with the same scope is blocked.
    await expect(civilizationKernel.enterEmergency({
      civilization_id: root.id,
      scope,
      reason: 'duplicate scope',
      actor_id: actorId,
      authorized_decision_ref: 'decision:dup',
      ttl_seconds: 3600,
    })).rejects.toThrow();

    // Activation fields are frozen; extending expiry is impossible.
    await expect(
      db.query(
        `UPDATE civilization_emergency_states SET expires_at = expires_at + interval '1 day' WHERE id = $1`,
        [entered.emergency.id]
      )
    ).rejects.toThrow(/immutable/);

    const revoked = await civilizationKernel.revokeEmergency({
      emergency_id: entered.emergency.id,
      actor_id: actorId,
      reason: 'drill complete',
    });
    expect(revoked.status).toBe('revoked');
    expect(revoked.ended_at).not.toBeNull();

    // Seed an already-due emergency directly (test setup), then sweep.
    await db.query(
      `INSERT INTO civilization_emergency_states
         (civilization_id, scope, reason, activated_by_actor_id, authorized_decision_ref, activated_at, expires_at)
       VALUES ($1,$2,'due drill',$3,'decision:due', now() - interval '10 seconds', now() - interval '5 seconds')`,
      [root.id, `${scope}-due`, actorId]
    );
    const sweep = await civilizationKernel.expireDueEmergencies();
    expect(sweep.expired).toBeGreaterThanOrEqual(1);
    expect(sweep.civilizations_recovering).toContain(root.id);

    const recoveringRoot = await civilizationKernel.getCivilization(root.id);
    expect(recoveringRoot!.status).toBe('recovering');

    // Restore the root to active for subsequent suites.
    const restored = await civilizationKernel.transitionStatus({
      civilization_id: root.id,
      to_status: 'active',
      actor_id: actorId,
      reason: 'recovery complete',
    });
    expect(restored.status).toBe('active');

    const transitions = await db.query(
      `SELECT from_status, to_status FROM civilization_state_transitions
        WHERE civilization_id = $1 ORDER BY created_at`,
      [root.id]
    );
    const pairs = transitions.rows.map((r: any) => `${r.from_status}->${r.to_status}`);
    expect(pairs).toContain('active->emergency');
    expect(pairs).toContain('emergency->recovering');
    expect(pairs).toContain('recovering->active');
  });

  test('charters are append-only and versioned; activation supersedes the prior charter', async () => {
    const root = await civilizationKernel.ensureCivilizationRoot();
    const actorId = await registerActor('kernel-charter');
    const before = await civilizationKernel.getActiveCharter(root.id);
    expect(before).not.toBeNull();

    const draft = await civilizationKernel.proposeCharter({
      civilization_id: root.id,
      charter: { name: 'Amended charter', principles: ['Evidence before memory'], amendment: Date.now() },
      actor_id: actorId,
    });
    expect(draft.status).toBe('draft');
    expect(draft.version_number).toBeGreaterThan(before!.version_number);

    await civilizationKernel.activateCharter(draft.id, actorId);
    const after = await civilizationKernel.getActiveCharter(root.id);
    expect(after!.id).toBe(draft.id);

    const supersededOld = await db.query(
      `SELECT status FROM civilization_charters WHERE id = $1`,
      [before!.id]
    );
    expect(supersededOld.rows[0].status).toBe('superseded');

    await expect(
      db.query(`UPDATE civilization_charters SET charter_json = '{}'::jsonb WHERE id = $1`, [draft.id])
    ).rejects.toThrow(/charter content is immutable/);

    await expect(civilizationKernel.activateCharter(draft.id, actorId)).rejects.toThrow(/not draft/);
  });

  test('objective lifecycle enforces transitions and records provenance', async () => {
    const root = await civilizationKernel.ensureCivilizationRoot();
    const actorId = await registerActor('kernel-objective');
    const objective = await civilizationKernel.createObjective({
      civilization_id: root.id,
      title: `Increase verified generality ${Date.now()}`,
      description: 'Grow the count of domains with verified competence',
      priority: 10,
      actor_id: actorId,
    });
    expect(objective.status).toBe('proposed');

    await expect(civilizationKernel.setObjectiveStatus({
      objective_id: objective.id,
      to_status: 'achieved',
      actor_id: actorId,
    })).rejects.toThrow(/illegal objective transition/);

    const activated = await civilizationKernel.setObjectiveStatus({
      objective_id: objective.id,
      to_status: 'active',
      actor_id: actorId,
    });
    expect(activated.status).toBe('active');

    const achieved = await civilizationKernel.setObjectiveStatus({
      objective_id: objective.id,
      to_status: 'achieved',
      actor_id: actorId,
      reason: 'demonstrated',
    });
    expect(achieved.status).toBe('achieved');

    const events = await db.query(
      `SELECT event_type FROM event_log WHERE object_type = 'civilization_objective' AND object_id = $1 ORDER BY occurred_at`,
      [objective.id]
    );
    expect(events.rows.map((r: any) => r.event_type)).toEqual(
      expect.arrayContaining(['civilization.objective_created', 'civilization.objective_status_changed'])
    );
  });

  test('version history is append-only', async () => {
    const root = await civilizationKernel.ensureCivilizationRoot();
    const version = await db.query(
      `SELECT id FROM civilization_versions WHERE civilization_id = $1 ORDER BY version_number LIMIT 1`,
      [root.id]
    );
    expect(version.rowCount).toBe(1);
    await expect(
      db.query(`UPDATE civilization_versions SET content_json = '{}'::jsonb WHERE id = $1`, [version.rows[0].id])
    ).rejects.toThrow(/append-only/);
  });
});
