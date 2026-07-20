import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { citizenshipService } from '../src/services/citizenship.service';
import { treasuryService } from '../src/services/treasury.service';
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

describe('civilization judiciary (C8)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('SCENARIO D: dispute -> jurisdiction -> evidence -> hearing -> ruling -> enforcement (real state) -> appeal (independent) -> final', async () => {
    const complainant = await actor('jud-complainant');
    const judge = await actor('jud-judge');
    const appellate = await actor('jud-appellate');

    // Respondent is a citizen with a funded treasury account.
    const respondentActor = await actor('jud-respondent');
    const respondent = await citizenshipService.registerCitizen({ actor_id: respondentActor, citizen_type: 'human' });
    const scopeId = respondent.id;
    await treasuryService.fund({
      scope_type: 'citizen', scope_id: scopeId, resource_type: 'llm_tokens', amount: 1000, reason: 'seed', actor_id: complainant,
    });

    const c = await judiciaryCaseService.openCase({
      dispute_type: 'citizen_misconduct', title: `Misconduct ${Date.now()}`,
      complainant_actor_id: complainant, respondent_scope_type: 'citizen', respondent_scope_id: scopeId,
    });
    expect(c.status).toBe('opened');

    await judiciaryCaseService.checkJurisdiction({ case_id: c.id, actor_id: judge, accept: true });
    await judiciaryCaseService.openEvidenceCollection(c.id, judge);
    await judiciaryCaseService.submitEvidence({ case_id: c.id, submitted_by_actor_id: complainant, statement: 'observed breach' });
    await judiciaryCaseService.holdHearing({ case_id: c.id, presiding_actor_id: judge, summary: 'both heard' });

    const ruling = await judiciaryCaseService.issueRuling({
      case_id: c.id, ruling_actor_id: judge, outcome: 'upheld', rationale: 'breach substantiated',
      is_precedent: true, principle: 'misconduct incurs a resource penalty',
    });
    expect(ruling.ruling_id).toBeTruthy();
    expect(ruling.precedent_id).not.toBeNull();

    // Enforcement mutates REAL state: a treasury penalty debits the respondent.
    const enforcement = await judiciaryCaseService.issueEnforcement({
      case_id: c.id, issued_by_actor_id: judge, order_type: 'resource_penalty',
      target_scope_type: 'citizen', target_scope_id: scopeId,
      detail: { resource_type: 'llm_tokens', amount: 300, reason: 'penalty' },
    });
    expect(enforcement.applied_ref).toMatch(/^penalty:/);
    const balance = await treasuryService.balance('citizen', scopeId, 'llm_tokens');
    expect(balance!.balance).toBe(700); // ruling altered real runtime state

    // Appeal routes to an INDEPENDENT panel (not the trial judge).
    await judiciaryCaseService.fileAppeal({ case_id: c.id, appellant_actor_id: respondentActor, grounds: 'penalty excessive' });
    await expect(judiciaryCaseService.ruleOnAppeal({
      case_id: c.id, appellate_actor_id: judge, outcome: 'partial', rationale: 'same judge',
    })).rejects.toThrow(/independent of the trial judge/);

    const appeal = await judiciaryCaseService.ruleOnAppeal({
      case_id: c.id, appellate_actor_id: appellate, outcome: 'dismissed', rationale: 'penalty upheld',
    });
    expect(appeal.ruling_id).toBeTruthy();

    const finalized = await judiciaryCaseService.finalizeCase({ case_id: c.id, actor_id: appellate });
    expect(finalized.status).toBe('closed');

    // Precedent is searchable.
    const precedents = await judiciaryCaseService.findPrecedents({ dispute_type: 'citizen_misconduct', outcome: 'upheld' });
    expect(precedents.some(p => p.ruling_id === ruling.ruling_id)).toBe(true);

    // Terminal case is immutable.
    await expect(
      db.query(`UPDATE judiciary_cases SET status = 'opened' WHERE id = $1`, [c.id])
    ).rejects.toThrow(/JUDICIARY GUARD/);
  });

  test('judiciary independence: the complainant cannot preside or rule', async () => {
    const complainant = await actor('jud-indep');
    const c = await judiciaryCaseService.openCase({
      dispute_type: 'resource_dispute', title: `Indep ${Date.now()}`,
      complainant_actor_id: complainant, respondent_scope_type: 'actor', respondent_scope_id: await actor('jud-indep-resp'),
    });
    const judge = await actor('jud-indep-judge');
    await judiciaryCaseService.checkJurisdiction({ case_id: c.id, actor_id: judge, accept: true });
    await judiciaryCaseService.openEvidenceCollection(c.id, judge);
    await expect(judiciaryCaseService.holdHearing({ case_id: c.id, presiding_actor_id: complainant, summary: 'self hearing' }))
      .rejects.toThrow(/cannot be the complainant/);
  });

  test('duplicate trial rulings are blocked', async () => {
    const complainant = await actor('jud-dup');
    const judge = await actor('jud-dup-judge');
    const c = await judiciaryCaseService.openCase({
      dispute_type: 'contract_breach', title: `Dup ${Date.now()}`,
      complainant_actor_id: complainant, respondent_scope_type: 'actor', respondent_scope_id: await actor('jud-dup-resp'),
    });
    await judiciaryCaseService.checkJurisdiction({ case_id: c.id, actor_id: judge, accept: true });
    await judiciaryCaseService.openEvidenceCollection(c.id, judge);
    await judiciaryCaseService.holdHearing({ case_id: c.id, presiding_actor_id: judge, summary: 'heard' });
    await judiciaryCaseService.issueRuling({ case_id: c.id, ruling_actor_id: judge, outcome: 'partial', rationale: 'first' });
    // Case is now in 'ruling'; a second issueRuling is rejected by status guard.
    await expect(judiciaryCaseService.issueRuling({ case_id: c.id, ruling_actor_id: judge, outcome: 'upheld', rationale: 'second' }))
      .rejects.toThrow(/requires a heard case/);
    // And a direct duplicate insert violates the unique trial-ruling index.
    await expect(
      db.query(
        `INSERT INTO judiciary_rulings (case_id, ruling_actor_id, outcome, rationale, signature, is_appellate)
         VALUES ($1,$2,'upheld','dup','sig',false)`,
        [c.id, judge]
      )
    ).rejects.toThrow(/uq_judiciary_trial_ruling|duplicate key/);
  });

  test('a case can be dismissed at jurisdiction check', async () => {
    const complainant = await actor('jud-dismiss');
    const judge = await actor('jud-dismiss-judge');
    const c = await judiciaryCaseService.openCase({
      dispute_type: 'jurisdiction_conflict', title: `Dismiss ${Date.now()}`,
      complainant_actor_id: complainant, respondent_scope_type: 'actor', respondent_scope_id: await actor('jud-dismiss-resp'),
    });
    await judiciaryCaseService.checkJurisdiction({ case_id: c.id, actor_id: judge, accept: false });
    const dismissed = await judiciaryCaseService.getCase(c.id);
    expect(dismissed!.status).toBe('dismissed');
    await expect(judiciaryCaseService.openEvidenceCollection(c.id, judge)).rejects.toThrow(/terminal|must be jurisdiction_check/);
  });
});
