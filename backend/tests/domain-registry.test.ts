import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { domainRegistry } from '../src/services/domain-registry.service';
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
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function insertTrust(subjectId: string, domain: string, trustFactor: number, forceDowngrade = false): Promise<string> {
  const result = await db.query<{ trust_id: string }>(
    `INSERT INTO trust_scores
       (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
        n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade, downgrade_reason)
     VALUES ($1,'agent',$2,'general','short',NOW() - INTERVAL '7 days',NOW(),10,10,0.1,0.2,0.03,$3,$4,$5)
     RETURNING trust_id`,
    [subjectId, domain, trustFactor, forceDowngrade, forceDowngrade ? 'test_force_downgrade' : null]
  );
  return result.rows[0].trust_id;
}

describe('domain registry', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('activates a domain only with core institution and sufficient trust proof', async () => {
    const domainKey = `pet_dental_health_${Date.now()}`;
    const proofSubject = `domain-proof-agent-${Date.now()}`;
    const institution = await institutionsService.createCanonicalInstitution({
      name: `domain_registry_${Date.now()}`,
      domain: domainKey,
      purpose: 'Domain registry verification institution',
      authorityScope: ['domain_onboarding'],
    });
    const trustId = await insertTrust(proofSubject, domainKey, 0.84);

    const record = await domainRegistry.registerDomain({
      domain_key: domainKey,
      display_name: 'Pet Dental Health',
      institution_id: institution.institutionId,
      proof_subject_id: proofSubject,
      required_trust_threshold: 0.7,
      proof: { benchmark: 'focused-domain-regression' },
    });

    expect(record.status).toBe('active');
    expect(record.latest_trust_id).toBe(trustId);
    expect(Number(record.latest_trust_factor)).toBeCloseTo(0.84);
    expect(record.institution_actor_id).toBe(institution.actorId);
    expect(record.event_log_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));

    const outbox = await db.query('SELECT id FROM event_outbox WHERE event_log_id = $1', [record.event_log_id]);
    expect(outbox.rowCount).toBe(1);

    const duplicate = await domainRegistry.registerDomain({
      domain_key: domainKey,
      institution_id: institution.institutionId,
      proof_subject_id: proofSubject,
    });
    expect(duplicate.id).toBe(record.id);
  });

  test('rejects domain activation when latest trust is below threshold or downgraded', async () => {
    const lowTrustDomain = `low_trust_domain_${Date.now()}`;
    const downgradedDomain = `downgraded_domain_${Date.now()}`;
    const institution = await institutionsService.createCanonicalInstitution({
      name: `domain_registry_reject_${Date.now()}`,
      domain: lowTrustDomain,
      purpose: 'Domain registry rejection institution',
      authorityScope: ['domain_onboarding'],
    });

    await insertTrust('low-trust-agent', lowTrustDomain, 0.52);
    await expect(
      domainRegistry.registerDomain({
        domain_key: lowTrustDomain,
        institution_id: institution.institutionId,
        proof_subject_id: 'low-trust-agent',
        required_trust_threshold: 0.7,
      })
    ).rejects.toThrow(/below threshold/);

    await insertTrust('downgraded-agent', downgradedDomain, 0.91, true);
    await expect(
      domainRegistry.registerDomain({
        domain_key: downgradedDomain,
        institution_id: institution.institutionId,
        proof_subject_id: 'downgraded-agent',
        required_trust_threshold: 0.7,
      })
    ).rejects.toThrow(/force-downgraded/);
  });
});
