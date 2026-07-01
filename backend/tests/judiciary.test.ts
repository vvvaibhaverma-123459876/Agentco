import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { disputeRegistry, precedentStore, rulingService } from '../src/services/judiciary.service';

async function applyMigrations() {
  for (const name of [
    '009_trust_scores.sql',
    '050_autonomy_action_loop.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '109_judiciary.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function createClaim(claimId: string, text: string, generatedBy = 'judiciary-test'): Promise<void> {
  await db.query(
     `INSERT INTO autonomy_claims
       (claim_id, text, status, confidence, support_source_ids, support_snippets, generated_by)
     VALUES ($1,$2,'supported',0.8,$3::jsonb,$4::jsonb,$5)
     ON CONFLICT (claim_id) DO NOTHING`,
    [
      claimId,
      text,
      JSON.stringify([`source-${claimId}`]),
      JSON.stringify([{ source_id: `source-${claimId}`, snippet: text }]),
      generatedBy,
    ]
  );
}

async function insertTrust(subjectId: string, domain: string, trustFactor: number): Promise<void> {
  await db.query(
    `INSERT INTO trust_scores
       (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
        n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade)
     VALUES ($1,'agent',$2,'general','short',now() - interval '7 days',now(),20,20,0.1,0.2,0.03,$3,false)`,
    [subjectId, domain, trustFactor]
  );
}

describe('judiciary services', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('opens contradiction disputes, issues rulings, and stores precedents', async () => {
    const suffix = Date.now().toString().slice(-8);
    const leftClaim = `claim-left-${suffix}`;
    const rightClaim = `claim-right-${suffix}`;
    await createClaim(leftClaim, 'The vendor has SOC2 coverage.');
    await createClaim(rightClaim, 'The vendor does not have SOC2 coverage.');

    const dispute = await disputeRegistry.openContradictionDispute({
      subject_claim_id: leftClaim,
      counter_claim_id: rightClaim,
      reason: 'Claims assert mutually exclusive SOC2 status.',
      evidence: { source_pair: ['audit-report', 'vendor-email'] },
    });

    expect(dispute.status).toBe('opened');
    expect(dispute.dispute_type).toBe('claim_contradiction');
    expect(dispute.event_log_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));

    const linkedClaims = await db.query(
      `SELECT claim_id, status, contradicts, contradicted_by
         FROM autonomy_claims
        WHERE claim_id = ANY($1::varchar[])
        ORDER BY claim_id`,
      [[leftClaim, rightClaim].sort()]
    );
    expect(linkedClaims.rows).toHaveLength(2);
    expect(linkedClaims.rows.every((row) => row.status === 'contradicted')).toBe(true);
    expect(JSON.stringify(linkedClaims.rows)).toContain(leftClaim);
    expect(JSON.stringify(linkedClaims.rows)).toContain(rightClaim);

    const duplicate = await disputeRegistry.openContradictionDispute({
      subject_claim_id: rightClaim,
      counter_claim_id: leftClaim,
      reason: 'same contradiction in reverse order',
    });
    expect(duplicate.id).toBe(dispute.id);

    const { ruling, precedent } = await rulingService.issueRuling({
      dispute_id: dispute.id,
      outcome: 'counter_upheld',
      rationale: 'Latest independent evidence supports the counter-claim.',
      precedent_flag: true,
      principle: 'Prefer newer independent audit evidence over stale vendor attestations.',
    });

    expect(ruling.outcome).toBe('counter_upheld');
    expect(ruling.precedent_flag).toBe(true);
    expect(precedent?.principle).toMatch(/newer independent audit evidence/);

    const storedDispute = await db.query('SELECT status FROM disputes WHERE id = $1', [dispute.id]);
    expect(storedDispute.rows[0].status).toBe('ruled');

    const precedents = await precedentStore.findPrecedents({
      dispute_type: 'claim_contradiction',
      outcome: 'counter_upheld',
    });
    expect(precedents.map((row) => row.id)).toContain(precedent?.id);

    const outbox = await db.query(
      `SELECT COUNT(*)::int AS count
         FROM event_outbox
        WHERE event_log_id = ANY($1::uuid[])`,
      [[dispute.event_log_id, ruling.event_log_id, precedent?.event_log_id]]
    );
    expect(outbox.rows[0].count).toBe(3);
  });

  test('rejects disputes for missing claims and second rulings for ruled disputes', async () => {
    await expect(
      disputeRegistry.openContradictionDispute({
        subject_claim_id: `missing-a-${Date.now()}`,
        counter_claim_id: `missing-b-${Date.now()}`,
        reason: 'missing fixture claims',
      })
    ).rejects.toThrow(/claim not found/);

    const suffix = Date.now().toString().slice(-8);
    const leftClaim = `claim-once-${suffix}`;
    const rightClaim = `claim-twice-${suffix}`;
    await createClaim(leftClaim, 'The policy allows escalation.');
    await createClaim(rightClaim, 'The policy blocks escalation.');
    const dispute = await disputeRegistry.openContradictionDispute({
      subject_claim_id: leftClaim,
      counter_claim_id: rightClaim,
      reason: 'policy interpretation conflict',
    });
    await rulingService.issueRuling({
      dispute_id: dispute.id,
      outcome: 'insufficient_evidence',
      rationale: 'The cited policy version is ambiguous.',
    });

    await expect(
      rulingService.issueRuling({
        dispute_id: dispute.id,
        outcome: 'settled',
        rationale: 'Second ruling should fail.',
      })
    ).rejects.toThrow(/already ruled/);
  });

  test('issues calibration-weighted ruling for the clearly better calibrated side', async () => {
    const suffix = Date.now().toString().slice(-8);
    const domain = `judiciary_domain_${suffix}`;
    const subjectProducer = `subject-producer-${suffix}`;
    const counterProducer = `counter-producer-${suffix}`;
    const subjectClaim = `a-subj-${suffix}`;
    const counterClaim = `z-cnt-${suffix}`;
    await createClaim(subjectClaim, 'The trial endpoint was met.', subjectProducer);
    await createClaim(counterClaim, 'The trial endpoint was not met.', counterProducer);
    await insertTrust(subjectProducer, domain, 0.9);
    await insertTrust(counterProducer, domain, 0.55);

    const dispute = await disputeRegistry.openContradictionDispute({
      subject_claim_id: subjectClaim,
      counter_claim_id: counterClaim,
      reason: 'trial endpoint claims conflict',
    });

    const result = await rulingService.issueCalibrationWeightedRuling({
      dispute_id: dispute.id,
      domain,
      subject_evidence_independence: 0.95,
      counter_evidence_independence: 0.8,
    });

    expect(result.status).toBe('ruled');
    expect(result.outcome).toBe('subject_upheld');
    expect(result.subject_weight).toBeCloseTo(0.855);
    expect(result.counter_weight).toBeCloseTo(0.44);
    expect(result.ruling?.precedent_flag).toBe(true);
    expect(result.precedent?.principle).toContain('stated confidence is not used');

    const storedDispute = await db.query('SELECT status FROM disputes WHERE id = $1', [dispute.id]);
    expect(storedDispute.rows[0].status).toBe('ruled');
  });

  test('fails closed without ruling when calibration weights are near tied', async () => {
    const suffix = Date.now().toString().slice(-8);
    const domain = `judiciary_tie_${suffix}`;
    const subjectProducer = `tie-subject-${suffix}`;
    const counterProducer = `tie-counter-${suffix}`;
    const subjectClaim = `a-ties-${suffix}`;
    const counterClaim = `z-tiec-${suffix}`;
    await createClaim(subjectClaim, 'The evidence supports option A.', subjectProducer);
    await createClaim(counterClaim, 'The evidence supports option B.', counterProducer);
    await insertTrust(subjectProducer, domain, 0.72);
    await insertTrust(counterProducer, domain, 0.7);

    const dispute = await disputeRegistry.openContradictionDispute({
      subject_claim_id: subjectClaim,
      counter_claim_id: counterClaim,
      reason: 'near-tie calibrated claims conflict',
    });

    const result = await rulingService.issueCalibrationWeightedRuling({
      dispute_id: dispute.id,
      domain,
      minimum_margin: 0.1,
    });

    expect(result.status).toBe('escalated');
    expect(result.outcome).toBe('escalate');
    expect(result.ruling).toBeNull();
    expect(result.rationale).toMatch(/too close|weak/);

    const storedDispute = await db.query('SELECT status FROM disputes WHERE id = $1', [dispute.id]);
    expect(storedDispute.rows[0].status).toBe('opened');
  });
});
