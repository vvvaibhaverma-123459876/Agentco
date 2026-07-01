import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { db } from '../src/db/client';
import { institutionsService } from '../src/services/institutions.service';
import { institutionClaimVettingService } from '../src/services/institution-claim-vetting.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '052b_institutions.sql',
    '062_runtime_schema_compatibility.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '050_autonomy_action_loop.sql',
    '053_work_assignment_schema.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function createInstitution(prefix: string) {
  const institution = await institutionsService.createCanonicalInstitution({
    name: `${prefix}_${Date.now()}`,
    domain: `${prefix}_domain`,
    purpose: 'Claim vetting test institution',
    authorityScope: ['claim_vetting'],
  });
  const departments = Object.fromEntries(institution.departments.map(dept => [dept.name, dept.id]));
  return { ...institution, departments };
}

async function createWorkRequest(institutionId: string, productionDepartmentId: string): Promise<string> {
  const id = crypto.randomUUID();
  await db.query(
    `INSERT INTO institution_work_requests
       (id, institution_id, department_id, objective, required_specialists,
        budget_tokens, budget_iterations, budget_seconds, verification_required, risk_level, status)
     VALUES ($1,$2,$3,'Vet claim through department flow','[]'::jsonb,1000,3,60,true,'medium','queued')`,
    [id, institutionId, productionDepartmentId]
  );
  return id;
}

async function createClaim(claimId: string, options: { snippets?: string[]; derivedFrom?: string[] } = {}) {
  await db.query(
    `INSERT INTO autonomy_claims
       (claim_id, text, status, confidence, support_source_ids, support_snippets, derived_from_action_ids, generated_by)
     VALUES ($1,$2,'draft',0.76,$3::jsonb,$4::jsonb,$5::jsonb,'institution-vetting-test')`,
    [
      claimId,
      `${claimId} is supported by the evidence packet.`,
      JSON.stringify([`evidence-${claimId}`]),
      JSON.stringify(options.snippets ?? []),
      JSON.stringify(options.derivedFrom ?? []),
    ]
  );
}

describe('institution claim vetting service', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('lite rigor promotes a grounded claim without adversarial stage execution', async () => {
    const institution = await createInstitution('lite_vetting');
    const workRequestId = await createWorkRequest(institution.institutionId, institution.departments.Production);
    const claimId = `lite-claim-${Date.now()}`;
    await createClaim(claimId, { snippets: ['supported by the evidence packet'] });

    const result = await institutionClaimVettingService.vetClaim({
      workRequestId,
      claimId,
      rigorTier: 'lite',
      findingType: 'EXTERNALLY_VERIFIED',
    });

    expect(result.status).toBe('finding');
    expect(result.stages.map(stage => [stage.stage, stage.status])).toEqual([
      ['Production', 'passed'],
      ['Verification', 'passed'],
      ['Adversarial', 'skipped'],
      ['Audit', 'passed'],
    ]);

    const request = await db.query(`SELECT status, result_summary FROM institution_work_requests WHERE id = $1`, [workRequestId]);
    expect(request.rows[0].status).toBe('completed');
    expect(request.rows[0].result_summary.vetting.status).toBe('finding');

    const events = await db.query(`SELECT cycle_phase FROM work_cycle_events WHERE work_request_id = $1`, [workRequestId]);
    expect(events.rowCount).toBe(4);
  });

  test('full rigor rejects claims without a substantive adversarial break attempt', async () => {
    const institution = await createInstitution('full_vetting');
    const workRequestId = await createWorkRequest(institution.institutionId, institution.departments.Production);
    const claimId = `full-claim-${Date.now()}`;
    await createClaim(claimId, { snippets: ['supported by the evidence packet'] });

    const result = await institutionClaimVettingService.vetClaim({
      workRequestId,
      claimId,
      rigorTier: 'full',
      findingType: 'EXTERNALLY_VERIFIED',
      adversarialReview: { attempted_break: true, counter_hypothesis: 'too short' },
    });

    expect(result.status).toBe('rejected');
    expect(result.stages.find(stage => stage.stage === 'Adversarial')?.status).toBe('failed');
    expect(result.reputation_adjustments_required).toEqual([
      expect.objectContaining({
        department_id: institution.departments.Adversarial,
        delta: -0.03,
      }),
    ]);

    const request = await db.query(`SELECT status FROM institution_work_requests WHERE id = $1`, [workRequestId]);
    expect(request.rows[0].status).toBe('failed');

    const claim = await db.query(`SELECT status FROM autonomy_claims WHERE claim_id = $1`, [claimId]);
    expect(claim.rows[0].status).toBe('contradicted');

    const summary = await db.query(`SELECT result_summary FROM institution_work_requests WHERE id = $1`, [workRequestId]);
    expect(summary.rows[0].result_summary.vetting.reputation_adjustments_required[0].department_id)
      .toBe(institution.departments.Adversarial);
  });

  test('external verification fails without support snippets', async () => {
    const institution = await createInstitution('verification_vetting');
    const workRequestId = await createWorkRequest(institution.institutionId, institution.departments.Production);
    const claimId = `missing-snippet-claim-${Date.now()}`;
    await createClaim(claimId);

    const result = await institutionClaimVettingService.vetClaim({
      workRequestId,
      claimId,
      rigorTier: 'lite',
      findingType: 'EXTERNALLY_VERIFIED',
    });

    expect(result.status).toBe('rejected');
    expect(result.stages.find(stage => stage.stage === 'Verification')?.status).toBe('failed');
    const claim = await db.query(`SELECT status FROM autonomy_claims WHERE claim_id = $1`, [claimId]);
    expect(claim.rows[0].status).toBe('unsupported');
  });
});
