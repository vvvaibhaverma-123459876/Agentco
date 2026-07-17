import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { civilizationOs } from '../src/services/civilization-os.service';

// Completion condition 40: cross-civilization and cross-society access blocked.
// The uq_civilizations_single_active index is PARTIAL (WHERE status='active'), so
// multiple civilization rows coexist — only one is active. This makes cross-
// civilization isolation both constructible and meaningful: data scoped to one
// civilization must never be visible to a query scoped to another.

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

async function insertActiveSociety(civilizationId: string, name: string, actorId: string): Promise<string> {
  const r = await db.query<{ id: string }>(
    `INSERT INTO societies (civilization_id, name, status, created_by_actor_id)
     VALUES ($1,$2,'active',$3) RETURNING id`,
    [civilizationId, name, actorId]
  );
  return r.rows[0].id;
}

describe('cross-civilization / cross-society isolation (completion condition 40)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('a second civilization row coexists in forming state (partial singleton index)', async () => {
    const root = await civilizationKernel.getActiveCivilization();
    expect(root).not.toBeNull();
    const other = await civilizationKernel.createCivilization({ name: `civ-B-${Date.now()}` });
    expect(other.status).toBe('forming'); // not active — the active singleton is preserved
    expect(other.id).not.toBe(root!.id);
    // Exactly one active civilization still holds.
    const active = await db.query(`SELECT COUNT(*)::int c FROM civilizations WHERE status = 'active'`);
    expect(Number(active.rows[0].c)).toBe(1);
  });

  test('data scoped to civ B is invisible to a projection scoped to civ A, and vice versa', async () => {
    const op = await actor('iso');
    const root = await civilizationKernel.getActiveCivilization();
    const civA = root!.id;
    const civB = (await civilizationKernel.createCivilization({ name: `civ-B-iso-${Date.now()}` })).id;

    // Baseline society counts, per civilization.
    const projA0 = await civilizationOs.statusProjection(civA);
    const projB0 = await civilizationOs.statusProjection(civB);
    const societiesA0 = Number((projA0 as any).societies_active ?? (projA0 as any).societies ?? 0);
    const societiesB0 = Number((projB0 as any).societies_active ?? (projB0 as any).societies ?? 0);

    // Add an active society under EACH civilization.
    await insertActiveSociety(civA, `soc-A-${Date.now()}`, op);
    await insertActiveSociety(civB, `soc-B-${Date.now()}`, op);

    const projA1 = await civilizationOs.statusProjection(civA);
    const projB1 = await civilizationOs.statusProjection(civB);
    const societiesA1 = Number((projA1 as any).societies_active ?? (projA1 as any).societies ?? 0);
    const societiesB1 = Number((projB1 as any).societies_active ?? (projB1 as any).societies ?? 0);

    // Each civilization sees exactly its own +1 — no bleed across the boundary.
    expect(societiesA1).toBe(societiesA0 + 1);
    expect(societiesB1).toBe(societiesB0 + 1);

    // Direct scoped query confirms rows never leak across civilization_id.
    const aSeesB = await db.query(
      `SELECT COUNT(*)::int c FROM societies s
        WHERE s.civilization_id = $1 AND s.name LIKE 'soc-B-%'`,
      [civA]
    );
    expect(Number(aSeesB.rows[0].c)).toBe(0);
    const bSeesA = await db.query(
      `SELECT COUNT(*)::int c FROM societies s
        WHERE s.civilization_id = $1 AND s.name LIKE 'soc-A-%'`,
      [civB]
    );
    expect(Number(bSeesA.rows[0].c)).toBe(0);
  });

  test('a society jurisdiction cannot exceed its civilization jurisdiction (cross-society escalation blocked)', async () => {
    // The composite FK society_jurisdictions -> civilization_jurisdictions makes
    // granting a key the civilization never held a referential impossibility.
    const op = await actor('iso-jur');
    const root = await civilizationKernel.getActiveCivilization();
    const societyId = await insertActiveSociety(root!.id, `soc-jur-${Date.now()}`, op);
    // All columns valid EXCEPT the (civilization_id, jurisdiction_key) pair, which
    // the civilization never held — so the composite FK is the only thing that fails.
    await expect(
      db.query(
        `INSERT INTO society_jurisdictions (society_id, civilization_id, jurisdiction_key, granted_by_actor_id)
         VALUES ($1,$2,$3,$4)`,
        [societyId, root!.id, `never-granted-key-${Date.now()}`, op]
      )
    ).rejects.toThrow(/violates foreign key|society_jurisdictions/i);
  });
});
