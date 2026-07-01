import { describe, expect, test } from '@jest/globals';
import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { civilizationRuntimeService } from '../src/services/civilization-runtime.service';
import { domainRegistry } from '../src/services/domain-registry.service';
import { institutionsService } from '../src/services/institutions.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '009_trust_scores.sql',
    '052b_institutions.sql',
    '053_work_assignment_schema.sql',
    '062_runtime_schema_compatibility.sql',
    '077_civilization_vertical_slice.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '102_domain_registry.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function insertTrust(subjectId: string, domain: string, trustFactor = 0.9): Promise<void> {
  await db.query(
    `INSERT INTO trust_scores
       (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
        n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade)
     VALUES ($1,'agent',$2,'general','short',now() - interval '7 days',now(),20,20,0.1,0.2,0.03,$3,false)`,
    [subjectId, domain, trustFactor]
  );
}

async function registerInstitutionDomain(domain: string): Promise<{ institutionId: string; proofSubject: string }> {
  const institution = await institutionsService.createCanonicalInstitution({
    name: `dispatch_${domain}_${Date.now()}`,
    domain,
    purpose: `${domain} dispatch institution`,
    authorityScope: ['civilization_dispatch'],
  });
  const proofSubject = `dispatch-proof-${domain}-${Date.now()}`;
  await insertTrust(proofSubject, domain, 0.91);
  await domainRegistry.registerDomain({
    domain_key: domain,
    institution_id: institution.institutionId,
    proof_subject_id: proofSubject,
  });
  return { institutionId: institution.institutionId, proofSubject };
}

describe('CivilizationRuntimeService reachability gate', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('persists a coordinator reachability tick for the core L14 runtime graph', async () => {
    const tick = await civilizationRuntimeService.runReachabilityTick('jest_l14_runtime');

    expect(tick.status).toBe('passed');
    expect(tick.missingTables).toEqual([]);
    expect(tick.missingRoutes).toEqual([]);
    expect(tick.nodes.length).toBeGreaterThanOrEqual(10);
    expect(tick.nodes.every(node => node.status === 'reachable')).toBe(true);
    expect(tick.nodes.map(node => node.id)).toEqual(expect.arrayContaining([
      'runtime_substrate_and_idempotency',
      'identity_authority',
      'resource_budgeting',
      'event_audit_outbox',
      'constitution_and_policy',
    ]));

    const stored = await db.query<{ tick_type: string; status: string }>(
      `SELECT t.tick_type, r.status
         FROM civilization_coordinator_ticks t
         JOIN civilization_vertical_slice_runs r ON r.id = t.run_id
        WHERE t.id = $1`,
      [tick.tickId],
    );

    expect(stored.rowCount).toBe(1);
    expect(stored.rows[0].tick_type).toBe('reachability_gate');
    expect(stored.rows[0].status).toBe('passed');
  });

  test('dispatches a single-domain goal to the qualifying institution production department', async () => {
    const suffix = Date.now();
    const domain = `dispatch_single_${suffix}`;
    const { institutionId } = await registerInstitutionDomain(domain);

    const tick = await civilizationRuntimeService.runDispatchTick({
      objective: 'Draft a grounded finding for a focused domain question.',
      domains: [domain],
      rigorTier: 'lite',
      runtimeMode: 'jest_l14_dispatch_single',
    });

    expect(tick.status).toBe('dispatched');
    expect(tick.dispatchType).toBe('institution');
    expect(tick.assignments).toHaveLength(1);
    expect(tick.assignments[0].institutionId).toBe(institutionId);
    expect(tick.assignments[0].domains).toEqual([domain]);
    expect(tick.coalitionId).toBeNull();

    const work = await db.query(
      `SELECT institution_id, department_id, status, result_summary
         FROM institution_work_requests
        WHERE id = $1`,
      [tick.assignments[0].workRequestId]
    );
    expect(work.rows[0].institution_id).toBe(institutionId);
    expect(work.rows[0].status).toBe('queued');
    expect(work.rows[0].result_summary.dispatch_type).toBe('institution');

    const stored = await db.query<{ tick_type: string; trace_json: Record<string, unknown> }>(
      `SELECT tick_type, trace_json
         FROM civilization_coordinator_ticks
        WHERE id = $1`,
      [tick.tickId]
    );
    expect(stored.rows[0].tick_type).toBe('dispatch_tick');
    expect(stored.rows[0].trace_json).toMatchObject({ status: 'dispatched', dispatch_type: 'institution' });
  });

  test('dispatches a cross-domain goal as a coalition over multiple institutions', async () => {
    const suffix = Date.now();
    const firstDomain = `dispatch_cross_a_${suffix}`;
    const secondDomain = `dispatch_cross_b_${suffix}`;
    const first = await registerInstitutionDomain(firstDomain);
    const second = await registerInstitutionDomain(secondDomain);

    const tick = await civilizationRuntimeService.runDispatchTick({
      objective: 'Coordinate a cross-domain answer from two registered societies.',
      domains: [firstDomain, secondDomain],
      rigorTier: 'full',
      riskLevel: 'high',
      runtimeMode: 'jest_l14_dispatch_coalition',
    });

    expect(tick.status).toBe('dispatched');
    expect(tick.dispatchType).toBe('coalition');
    expect(tick.coalitionId).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));
    expect(tick.assignments).toHaveLength(2);
    expect(tick.assignments.map(assignment => assignment.institutionId).sort()).toEqual(
      [first.institutionId, second.institutionId].sort()
    );

    const work = await db.query<{ count: string; verification_required: boolean; risk_level: string }>(
      `SELECT COUNT(*)::int AS count,
              bool_and(verification_required) AS verification_required,
              min(risk_level) AS risk_level
         FROM institution_work_requests
        WHERE id = ANY($1::varchar[])`,
      [tick.assignments.map(assignment => assignment.workRequestId)]
    );
    expect(Number(work.rows[0].count)).toBe(2);
    expect(work.rows[0].verification_required).toBe(true);
    expect(work.rows[0].risk_level).toBe('high');
  });
});
