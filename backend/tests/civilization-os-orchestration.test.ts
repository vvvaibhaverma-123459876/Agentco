import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { institutionGovernance } from '../src/services/institution-governance.service';
import { institutionsService } from '../src/services/institutions.service';
import { coalitionService } from '../src/services/coalition.service';
import { domainRegistry } from '../src/services/domain-registry.service';
import { collectiveKnowledge } from '../src/services/collective-knowledge.service';
import { civilizationOs } from '../src/services/civilization-os.service';

// C12 coordinator-driven reachability (brief A.6/B.8): the OS tick must
// orchestrate the judiciary, learning, expansion, and knowledge layers as real
// work, not merely observe them — and every step must be idempotent under
// re-ticks and restart recovery.

async function applyMigrations() {
  for (const file of [
    '009_trust_scores.sql',
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

async function insertClaim(claimId: string, sourceIds: string[], producer: string): Promise<void> {
  await db.query(
    `INSERT INTO autonomy_claims (claim_id, text, status, confidence, support_source_ids, generated_by)
     VALUES ($1,$2,'supported',0.8,$3::jsonb,$4)`,
    [claimId, `claim ${claimId}`, JSON.stringify(sourceIds), producer]
  );
}

describe('civilization OS layer orchestration (C12 coordinator reachability)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
    await institutionGovernance.ensureMandatoryInstitutions();
    await civilizationOs.setMode('running');
  });

  test('routes an open coalition→judiciary escalation into a real case, idempotently', async () => {
    const op = await actor('orch-judis');
    // Two member institutions for a coalition, then force a judiciary escalation.
    const instA = await institutionsService.createCanonicalInstitution({
      name: `orch_a_${Date.now()}`, domain: `d_a_${Date.now()}`, purpose: 'p', authorityScope: ['x'],
    });
    const instB = await institutionsService.createCanonicalInstitution({
      name: `orch_b_${Date.now()}`, domain: `d_b_${Date.now()}`, purpose: 'p', authorityScope: ['x'],
    });
    const coalition = await coalitionService.proposeCoalition({
      name: `orch coalition ${Date.now()}`, member_institution_ids: [instA.institutionId, instB.institutionId],
      created_by_actor_id: op,
    });
    // Insert the escalation directly (targets judiciary, open) — the coordinator routes it.
    const escId = crypto.randomUUID();
    await db.query(
      `INSERT INTO coalition_escalations (id, coalition_id, escalation_type, target, reason, status, created_by_actor_id)
       VALUES ($1,$2,'commitment_breach','judiciary','member breached commitment','open',$3)`,
      [escId, coalition.id, op]
    );

    await civilizationOs.tick();

    const routed = await db.query(`SELECT status, routed_at FROM coalition_escalations WHERE id = $1`, [escId]);
    expect(routed.rows[0].status).toBe('routed');
    expect(routed.rows[0].routed_at).not.toBeNull();
    const cases = await db.query(`SELECT id, dispute_type FROM judiciary_cases WHERE source_dispute_id = $1`, [escId]);
    expect(cases.rowCount).toBe(1);
    expect(cases.rows[0].dispute_type).toBe('contract_breach');

    // Re-tick: no duplicate case, escalation stays routed.
    await civilizationOs.tick();
    const casesAfter = await db.query(`SELECT COUNT(*)::int c FROM judiciary_cases WHERE source_dispute_id = $1`, [escId]);
    expect(Number(casesAfter.rows[0].c)).toBe(1);
  });

  test('suspends an active domain that has fallen below its trust threshold, idempotently', async () => {
    const domainKey = `orch_domain_${Date.now()}`;
    const proofSubject = `orch-proof-${Date.now()}`;
    const inst = await institutionsService.createCanonicalInstitution({
      name: `orch_dom_${Date.now()}`, domain: domainKey, purpose: 'p', authorityScope: ['domain_onboarding'],
    });
    // Register active with sufficient trust (0.84 >= 0.7).
    const trust = await db.query<{ trust_id: string }>(
      `INSERT INTO trust_scores
         (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
          n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade, downgrade_reason)
       VALUES ($1,'agent',$2,'general','short',NOW() - INTERVAL '7 days',NOW(),10,10,0.1,0.2,0.03,0.84,false,null)
       RETURNING trust_id`,
      [proofSubject, domainKey]
    );
    const record = await domainRegistry.registerDomain({
      domain_key: domainKey, display_name: 'Orchestration Domain', institution_id: inst.institutionId,
      proof_subject_id: proofSubject, required_trust_threshold: 0.7, proof: { benchmark: 'x' },
    });
    expect(record.status).toBe('active');

    // Trust decays below threshold on the registry row (simulating a later low score).
    await db.query(`UPDATE domain_registry SET latest_trust_factor = 0.4 WHERE id = $1`, [record.id]);

    await civilizationOs.tick();

    const after = await db.query(`SELECT status FROM domain_registry WHERE id = $1`, [record.id]);
    expect(after.rows[0].status).toBe('suspended');
    // Idempotent: a suspended domain is not re-processed and stays suspended.
    await civilizationOs.tick();
    const stable = await db.query(`SELECT status FROM domain_registry WHERE id = $1`, [record.id]);
    expect(stable.rows[0].status).toBe('suspended');
    const events = await db.query(
      `SELECT COUNT(*)::int c FROM event_log WHERE event_type = 'domain.suspended_below_threshold' AND object_id = $1`,
      [record.id]
    );
    expect(Number(events.rows[0].c)).toBe(1);
  });

  test('reconciles a dangling provenance edge whose source claim is already retracted', async () => {
    const op = await actor('orch-know');
    const producer = `agent-${Date.now()}`;
    const evidenceId = `ev-${crypto.randomUUID()}`;
    const otherEvidence = `ev-${crypto.randomUUID()}`;
    const claimA = crypto.randomUUID();
    const claimB = crypto.randomUUID();
    await insertClaim(claimA, [evidenceId], producer);
    // claimB is supported by UNRELATED evidence, so retracting claimA does not
    // auto-discover it via support_source_ids — the dependency is only the edge
    // we add after the retraction, making it genuinely dangling.
    await insertClaim(claimB, [otherEvidence], producer);
    // Retract claimA — but link B←A AFTER the retraction so propagation never reached B.
    await collectiveKnowledge.retract({ subject_type: 'claim', subject_id: claimA, reason: 'discredited', actor_id: op });
    await collectiveKnowledge.linkProvenance({
      from_type: 'claim', from_id: claimA, to_type: 'claim', to_id: claimB, actor_id: op,
    });
    // B is still standing on retracted ground.
    const before = await db.query(`SELECT status FROM autonomy_claims WHERE claim_id = $1`, [claimB]);
    expect(before.rows[0].status).toBe('supported');

    await civilizationOs.tick();

    const after = await db.query(`SELECT status FROM autonomy_claims WHERE claim_id = $1`, [claimB]);
    expect(after.rows[0].status).toBe('retracted');
    // Idempotent: re-tick does not re-process the now-retracted claim.
    const propBefore = await db.query(`SELECT COUNT(*)::int c FROM retraction_propagations WHERE affected_id = $1`, [claimB]);
    await civilizationOs.tick();
    const propAfter = await db.query(`SELECT COUNT(*)::int c FROM retraction_propagations WHERE affected_id = $1`, [claimB]);
    expect(Number(propAfter.rows[0].c)).toBe(Number(propBefore.rows[0].c));
  });

  test('the tick status projection reports the orchestrated layer counts', async () => {
    const tick = await civilizationOs.tick();
    expect(tick.status).toHaveProperty('orchestrated');
    const orch = (tick.status as any).orchestrated;
    expect(orch).toHaveProperty('escalations_routed');
    expect(orch).toHaveProperty('candidates_retained');
    expect(orch).toHaveProperty('domains_suspended');
    expect(orch).toHaveProperty('provenance_reconciled');
  });
});
