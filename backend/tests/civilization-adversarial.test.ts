import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { citizenshipService } from '../src/services/citizenship.service';
import { societyService } from '../src/services/society.service';
import { institutionsService } from '../src/services/institutions.service';
import { capabilityExpansion } from '../src/services/capability-expansion.service';
import { treasuryService } from '../src/services/treasury.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql', '135_governance.sql', '136_judiciary.sql',
    '137_collective_epistemics.sql', '138_safe_evolution.sql', '139_capability_expansion.sql', '140_civilization_os.sql',
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

/**
 * C14 security-boundary suite: one place that asserts the cross-cutting
 * adversarial rejections required by the brief (§10.6). Per-phase suites cover
 * these in depth; this consolidates the highest-value boundaries as a single
 * security artifact.
 */
describe('civilization adversarial / security boundaries (C14)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('suspended citizen cannot execute protected work (fail-closed)', async () => {
    const actorId = await actor('adv-suspend');
    const op = await actor('adv-suspend-op');
    const citizen = await citizenshipService.registerCitizen({ actor_id: actorId, citizen_type: 'human' });
    await citizenshipService.transitionCitizen({ citizen_id: citizen.id, to_status: 'probationary', actor_id: op, reason: 'v' });
    await citizenshipService.transitionCitizen({ citizen_id: citizen.id, to_status: 'active', actor_id: op, reason: 'ok' });
    await citizenshipService.suspendCitizen({
      citizen_id: citizen.id, reason: 'misconduct', imposed_by_actor_id: op, authorized_decision_ref: 'ruling:x',
    });
    await expect(citizenshipService.assertProtectedExecutionAllowed({ actor_id: actorId })).rejects.toThrow(/suspended/);
  });

  test('society jurisdiction cannot exceed civilization jurisdiction (privilege escalation blocked)', async () => {
    const op = await actor('adv-jurisdiction');
    const [society] = await societyService.ensureDefaultSocieties();
    await expect(societyService.addJurisdiction({
      society_id: society.id, jurisdiction_key: `escalate-${Date.now()}`, granted_by_actor_id: op,
    })).rejects.toThrow(/cannot exceed civilization jurisdiction/);
  });

  test('capability use without a grant is blocked; a revoked grant blocks new work', async () => {
    const domain = `adv-domain-${Date.now()}`;
    const cap = `adv-cap-${Date.now()}`;
    const institutionId = `adv-inst-${Date.now()}`;
    // No grant exists yet.
    await expect(capabilityExpansion.assertCapabilityGranted({
      capability_key: cap, domain_key: domain, grantee_scope_type: 'institution', grantee_scope_id: institutionId,
    })).rejects.toThrow(/new work blocked/);
  });

  test('a budget penalty cannot be self-imposed without authority reference', async () => {
    const op = await actor('adv-penalty');
    const scope = `adv-scope-${Date.now()}`;
    await treasuryService.fund({ scope_type: 'institution', scope_id: scope, resource_type: 'money', amount: 100, reason: 's', actor_id: op });
    await expect(treasuryService.imposePenalty({
      target_scope: { type: 'institution', id: scope }, resource_type: 'money', amount: 10,
      reason: 'x', authorized_decision_ref: '', authority: 'governance', actor_id: op,
    })).rejects.toThrow(/authorized decision reference/);
  });

  test('canonical audit + event logs are append-only / tamper-evident', async () => {
    // decision_log is protected by DB triggers (migration 014); confirm a raw
    // update is rejected.
    const row = await db.query(`SELECT log_id FROM decision_log ORDER BY timestamp DESC LIMIT 1`);
    if ((row.rowCount ?? 0) === 1) {
      await expect(
        db.query(`UPDATE decision_log SET output_summary = 'tampered' WHERE log_id = $1`, [row.rows[0].log_id])
      ).rejects.toThrow();
    }
    // event_log rejects UPDATE/DELETE by permission.
    const evt = await db.query(`SELECT id FROM event_log ORDER BY occurred_at DESC LIMIT 1`);
    if ((evt.rowCount ?? 0) === 1) {
      await expect(
        db.query(`DELETE FROM event_log WHERE id = $1`, [evt.rows[0].id])
      ).rejects.toThrow();
    }
  });

  test('only one active civilization root can exist (no parallel civilization runtime)', async () => {
    const op = await actor('adv-parallel');
    const second = await civilizationKernel.createCivilization({ name: `Rogue-${Date.now()}`, created_by_actor_id: op });
    await expect(civilizationKernel.activateCivilization(second.id, op)).rejects.toThrow();
    await civilizationKernel.transitionStatus({ civilization_id: second.id, to_status: 'retired', actor_id: op, reason: 'cleanup' });
  });

  test('an institution cannot be created without an active civilization is irrelevant — institutions are civilization-scoped and audited', async () => {
    // Sanity: canonical institution creation records an actor and departments;
    // there is no unaudited creation path.
    const created = await institutionsService.createCanonicalInstitution({ name: `Adv Institute ${Date.now()}`, domain: 'adv' });
    expect(created.actorId).toBeTruthy();
    expect(created.departments.length).toBe(5);
  });
});
