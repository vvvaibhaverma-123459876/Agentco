import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { domainRegistry } from '../src/services/domain-registry.service';
import { generalityMetricTracker } from '../src/services/generality-metric-tracker.service';
import { institutionsService } from '../src/services/institutions.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '009_trust_scores.sql',
    '052b_institutions.sql',
    '062_runtime_schema_compatibility.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '102_domain_registry.sql',
    '103_generality_metric_tracker.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await migrationDb.query(migration);
  }
}

async function insertTrust(subjectId: string, domain: string): Promise<void> {
  await db.query(
    `INSERT INTO trust_scores
       (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
        n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade)
     VALUES ($1,'agent',$2,'general','short',NOW() - INTERVAL '7 days',NOW(),12,12,0.08,0.18,0.02,0.88,false)`,
    [subjectId, domain]
  );
}

async function activateDomain(domainKey: string): Promise<void> {
  const proofSubject = `generality-proof-${domainKey}-${Date.now()}`;
  const institution = await institutionsService.createCanonicalInstitution({
    name: `generality_${domainKey}_${Date.now()}`,
    domain: domainKey,
    purpose: 'Generality tracker institution',
    authorityScope: ['domain_onboarding', 'generality_metric'],
  });
  await insertTrust(proofSubject, domainKey);
  await domainRegistry.registerDomain({
    domain_key: domainKey,
    institution_id: institution.institutionId,
    proof_subject_id: proofSubject,
    required_trust_threshold: 0.7,
  });
}

describe('generality metric tracker', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('records cross-domain scores only for active registered domains', async () => {
    const vendorDomain = `vendor_risk_${Date.now()}`;
    const codeDomain = `code_review_${Date.now()}`;
    await activateDomain(vendorDomain);
    await activateDomain(codeDomain);

    const run = await generalityMetricTracker.recordRun({
      benchmark_name: 'north_star_cross_domain_smoke',
      mode: 'deterministic_fake',
      baseline_score: 0.6,
      domains: [
        { domain_key: vendorDomain, score: 0.82, evidence: { case_id: 'vendor' } },
        { domain_key: codeDomain, score: 0.55, evidence: { case_id: 'code' } },
      ],
      metadata: { not_proof_of_general_intelligence: true },
    });

    expect(Number(run.aggregate_score)).toBeCloseTo(0.685);
    expect(run.domains_evaluated).toBe(2);
    expect(run.domains_above_baseline).toBe(1);
    expect(Number(run.generality_score)).toBeCloseTo(0.5);
    expect(run.event_log_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));

    const scores = await db.query(
      `SELECT domain_key, score, beats_baseline
         FROM generality_domain_scores
        WHERE run_id = $1
        ORDER BY domain_key`,
      [run.id]
    );
    expect(scores.rows).toHaveLength(2);
    expect(scores.rows.map((row) => row.beats_baseline).sort()).toEqual([false, true]);

    const outbox = await db.query('SELECT id FROM event_outbox WHERE event_log_id = $1', [run.event_log_id]);
    expect(outbox.rowCount).toBe(1);
  });

  test('rejects unregistered domains', async () => {
    await expect(
      generalityMetricTracker.recordRun({
        benchmark_name: 'north_star_cross_domain_smoke',
        mode: 'deterministic_fake',
        baseline_score: 0.6,
        domains: [{ domain_key: `missing_domain_${Date.now()}`, score: 0.9 }],
      })
    ).rejects.toThrow(/active registered domains required/);
  });
});
