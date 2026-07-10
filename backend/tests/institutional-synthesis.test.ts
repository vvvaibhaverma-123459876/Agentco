import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { institutionsService } from '../src/services/institutions.service';
import { FindingType } from '../src/services/institution-claim-vetting.service';
import { institutionalSynthesisService } from '../src/services/institutional-synthesis.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '050_autonomy_action_loop.sql',
    '052b_institutions.sql',
    '053_work_assignment_schema.sql',
    '062_runtime_schema_compatibility.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await migrationDb.query(migration);
  }
}

async function sourceFinding(input: {
  institutionId: string;
  departmentId: string;
  claimId: string;
  workRequestId: string;
  text: string;
  confidence: number;
  sourceIds: string[];
  findingType: FindingType;
  status?: 'completed' | 'failed' | 'queued';
}): Promise<void> {
  await db.query(
    `INSERT INTO autonomy_claims
       (claim_id, text, status, confidence, support_source_ids, support_snippets, generated_by)
     VALUES ($1,$2,'supported',$3,$4::jsonb,$5::jsonb,'synthesis-test')`,
    [
      input.claimId,
      input.text,
      input.confidence,
      JSON.stringify(input.sourceIds),
      JSON.stringify(input.sourceIds.map(sourceId => ({ source_id: sourceId, snippet: input.text }))),
    ]
  );
  await db.query(
    `INSERT INTO institution_work_requests
       (id, institution_id, department_id, objective, required_specialists,
        budget_tokens, budget_iterations, budget_seconds, verification_required,
        reputation_metric, risk_level, status, result_summary, completed_at)
     VALUES ($1,$2,$3,$4,'[]'::jsonb,1000,1,300,true,'evidence_quality','medium',$5::varchar,$6::jsonb,
             CASE WHEN $5::varchar = 'completed' THEN now() ELSE NULL END)`,
    [
      input.workRequestId,
      input.institutionId,
      input.departmentId,
      input.text,
      input.status ?? 'completed',
      JSON.stringify({
        vetting: {
          work_request_id: input.workRequestId,
          claim_id: input.claimId,
          rigor_tier: 'full',
          finding_type: input.findingType,
          status: input.status === 'failed' ? 'rejected' : 'finding',
          stages: [],
          reputation_adjustments_required: [],
        },
      }),
    ]
  );
}

describe('institutional synthesis', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('composes completed findings into a checked derived synthesis with full provenance', async () => {
    const suffix = Date.now().toString().slice(-8);
    const institution = await institutionsService.createCanonicalInstitution({
      name: `synthesis_${suffix}`,
      domain: `synthesis_domain_${suffix}`,
      purpose: 'Institutional synthesis test society',
      authorityScope: ['institutional_synthesis'],
    });
    const production = institution.departments.find(department => department.name === 'Production');
    expect(production).toBeDefined();

    const firstWork = `wr-a-${suffix}`;
    const secondWork = `wr-b-${suffix}`;
    const firstClaim = `cl-a-${suffix}`;
    const secondClaim = `cl-b-${suffix}`;
    await sourceFinding({
      institutionId: institution.institutionId,
      departmentId: production!.id,
      claimId: firstClaim,
      workRequestId: firstWork,
      text: 'Finding A is supported by two independent sources.',
      confidence: 0.8,
      sourceIds: [`ev-a-${suffix}`, `ev-b-${suffix}`],
      findingType: 'EXTERNALLY_VERIFIED',
    });
    await sourceFinding({
      institutionId: institution.institutionId,
      departmentId: production!.id,
      claimId: secondClaim,
      workRequestId: secondWork,
      text: 'Finding B depends on Finding A and another source.',
      confidence: 0.9,
      sourceIds: [`ev-c-${suffix}`],
      findingType: 'EXTERNALLY_VERIFIED',
    });

    const result = await institutionalSynthesisService.synthesize({
      sourceWorkRequestIds: [firstWork, secondWork],
      synthesisText: 'Findings A and B jointly support a derived institutional answer.',
    });

    expect(result.finding_type).toBe('DERIVED');
    expect(result.weakest_necessary_link).toBeCloseTo(0.8);
    expect(result.independent_corroboration_lift).toBeCloseTo(0.02);
    expect(result.confidence).toBeCloseTo(0.82);
    expect(result.contributing_claim_ids.sort()).toEqual([firstClaim, secondClaim].sort());
    expect(result.evidence_ids.sort()).toEqual([`ev-a-${suffix}`, `ev-b-${suffix}`, `ev-c-${suffix}`].sort());
    expect(result.verification.status).toBe('passed');
    expect(result.audit.status).toBe('passed');

    const claim = await db.query(
      `SELECT status, confidence, support_source_ids, derived_from_action_ids, generated_by
         FROM autonomy_claims
        WHERE claim_id = $1`,
      [result.synthesis_claim_id]
    );
    expect(claim.rows[0].status).toBe('supported');
    expect(Number(claim.rows[0].confidence)).toBeCloseTo(0.82);
    expect(claim.rows[0].support_source_ids.sort()).toEqual(result.evidence_ids.sort());
    expect(claim.rows[0].derived_from_action_ids.sort()).toEqual([firstClaim, secondClaim].sort());
    expect(claim.rows[0].generated_by).toBe('institutional-synthesis');

    const events = await db.query(
      `SELECT cycle_phase, event_type
         FROM work_cycle_events
        WHERE work_request_id = $1
        ORDER BY timestamp ASC`,
      [result.synthesis_work_request_id]
    );
    expect(events.rows.map(row => row.cycle_phase).sort()).toEqual([
      'synthesis',
      'synthesis_audit',
      'synthesis_verification',
    ].sort());
  });

  test('rejects synthesis from a source work request that is not a completed finding', async () => {
    const suffix = Date.now().toString().slice(-8);
    const institution = await institutionsService.createCanonicalInstitution({
      name: `synthesis_reject_${suffix}`,
      domain: `synthesis_reject_${suffix}`,
    });
    const production = institution.departments.find(department => department.name === 'Production');
    expect(production).toBeDefined();
    const workRequestId = `wr-q-${suffix}`;
    await sourceFinding({
      institutionId: institution.institutionId,
      departmentId: production!.id,
      claimId: `cl-q-${suffix}`,
      workRequestId,
      text: 'Queued finding is not yet vetted.',
      confidence: 0.7,
      sourceIds: [`ev-q-${suffix}`],
      findingType: 'EXTERNALLY_VERIFIED',
      status: 'queued',
    });

    await expect(
      institutionalSynthesisService.synthesize({
        sourceWorkRequestIds: [workRequestId],
        synthesisText: 'This should not synthesize.',
      })
    ).rejects.toThrow(/not completed findings/);
  });
});
