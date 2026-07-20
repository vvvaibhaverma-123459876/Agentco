/**
 * AUD-013 -- judiciary case idempotency.
 *
 * judiciary_cases.source_dispute_id had no uniqueness constraint, and openCase() had no
 * idempotency check at all; its one caller with a check-then-act guard
 * (routeEscalationsToJudiciary) splits that check and the INSERT across two separate database
 * connections/transactions, which is not a real guarantee against a genuine race -- only against
 * the one specific crash-recovery sequencing it was written for.
 *
 * Migration 145 adds a partial unique index (source_dispute_id IS NOT NULL); openCase() catches
 * the resulting unique-violation and resolves to the existing case instead of surfacing a raw
 * constraint error. These tests prove: (a) the DB constraint itself is real and independent of the
 * service layer (a direct-SQL bypass is rejected), (b) the service-level idempotency resolves
 * concurrent racing callers to the SAME case rather than creating duplicates, (c) callers with no
 * source_dispute_id are unaffected (multiple such cases may coexist), and (d) callers with distinct
 * source_dispute_id values are unaffected (no over-broad blocking).
 */
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { judiciaryCaseService } from '../src/services/judiciary-case.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql', '135_governance.sql', '136_judiciary.sql',
    '145_aud013_judiciary_case_idempotency.sql',
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

function openInput(complainant: string, respondent: string, sourceDisputeId?: string) {
  return {
    dispute_type: 'jurisdiction_conflict' as const,
    title: `AUD-013 ${crypto.randomUUID()}`,
    complainant_actor_id: complainant,
    respondent_scope_type: 'actor' as const,
    respondent_scope_id: respondent,
    source_dispute_id: sourceDisputeId,
  };
}

describe('AUD-013: judiciary case idempotency', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('DB backstop: a direct-SQL INSERT reusing a source_dispute_id is rejected, independent of the service layer', async () => {
    const complainant = await actor('aud013-direct-sql');
    const civ = await civilizationKernel.ensureCivilizationRoot();
    const sourceDisputeId = crypto.randomUUID();

    const first = await judiciaryCaseService.openCase(openInput(complainant, crypto.randomUUID(), sourceDisputeId));
    expect(first.id).toBeTruthy();

    await expect(
      db.query(
        `INSERT INTO judiciary_cases
           (id, civilization_id, dispute_type, title, complainant_actor_id, respondent_scope_type, respondent_scope_id, source_dispute_id)
         VALUES ($1,$2,'jurisdiction_conflict','direct sql bypass attempt',$3,'actor',$4,$5)`,
        [crypto.randomUUID(), civ.id, complainant, crypto.randomUUID(), sourceDisputeId]
      )
    ).rejects.toThrow(/duplicate key|uq_judiciary_cases_source_dispute_id/i);
  });

  test('service-level idempotency: sequential openCase calls with the same source_dispute_id return the SAME case, not a duplicate', async () => {
    const complainant = await actor('aud013-sequential');
    const sourceDisputeId = crypto.randomUUID();

    const first = await judiciaryCaseService.openCase(openInput(complainant, crypto.randomUUID(), sourceDisputeId));
    const second = await judiciaryCaseService.openCase(openInput(complainant, crypto.randomUUID(), sourceDisputeId));

    expect(second.id).toBe(first.id);

    const rows = await db.query(`SELECT id FROM judiciary_cases WHERE source_dispute_id = $1`, [sourceDisputeId]);
    expect(rows.rowCount).toBe(1);
  });

  test('service-level idempotency: CONCURRENT racing openCase calls with the same source_dispute_id resolve to one case, not two', async () => {
    const complainant = await actor('aud013-concurrent');
    const sourceDisputeId = crypto.randomUUID();

    // This is the actual race the DB constraint exists to close -- routeEscalationsToJudiciary's
    // check-then-act guard is split across two separate connections and cannot prevent this by
    // itself. Fire both concurrently rather than sequentially.
    const [a, b] = await Promise.all([
      judiciaryCaseService.openCase(openInput(complainant, crypto.randomUUID(), sourceDisputeId)),
      judiciaryCaseService.openCase(openInput(complainant, crypto.randomUUID(), sourceDisputeId)),
    ]);

    expect(a.id).toBe(b.id);

    const rows = await db.query(`SELECT id FROM judiciary_cases WHERE source_dispute_id = $1`, [sourceDisputeId]);
    expect(rows.rowCount).toBe(1);
  });

  test('cases with NO source_dispute_id are unaffected -- multiple may coexist', async () => {
    const complainant = await actor('aud013-no-source');

    const a = await judiciaryCaseService.openCase(openInput(complainant, crypto.randomUUID(), undefined));
    const b = await judiciaryCaseService.openCase(openInput(complainant, crypto.randomUUID(), undefined));

    expect(a.id).not.toBe(b.id);
  });

  test('cases with DISTINCT source_dispute_id values are unaffected -- no over-broad blocking', async () => {
    const complainant = await actor('aud013-distinct');

    const a = await judiciaryCaseService.openCase(openInput(complainant, crypto.randomUUID(), crypto.randomUUID()));
    const b = await judiciaryCaseService.openCase(openInput(complainant, crypto.randomUUID(), crypto.randomUUID()));

    expect(a.id).not.toBe(b.id);
  });
});
