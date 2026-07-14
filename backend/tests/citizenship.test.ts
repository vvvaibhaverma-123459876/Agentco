import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { citizenshipService } from '../src/services/citizenship.service';
import { durableExecution } from '../src/services/durable-execution.service';

async function applyMigrations() {
  for (const file of ['129_civilization_kernel.sql', '130_citizenship.sql']) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${file}`), 'utf8');
    await migrationDb.query(migration);
  }
}

async function registerActor(prefix: string): Promise<string> {
  const actor = await identityAuthorityService.registerActor({
    actor_type: 'human',
    name: `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`,
  });
  return actor.id;
}

async function registerCitizenActor(prefix: string): Promise<{ actorId: string; citizenId: string }> {
  const actorId = await registerActor(prefix);
  const citizen = await citizenshipService.registerCitizen({
    actor_id: actorId,
    citizen_type: 'human',
  });
  return { actorId, citizenId: citizen.id };
}

describe('citizenry (C2)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('registration is idempotent and lifecycle transitions are enforced', async () => {
    const { actorId, citizenId } = await registerCitizenActor('cit-lifecycle');
    const again = await citizenshipService.registerCitizen({ actor_id: actorId, citizen_type: 'human' });
    expect(again.id).toBe(citizenId);
    expect(again.status).toBe('candidate');

    const operator = await registerActor('cit-operator');
    await expect(citizenshipService.transitionCitizen({
      citizen_id: citizenId, to_status: 'active', actor_id: operator, reason: 'skip probation',
    })).rejects.toThrow(/illegal citizenship transition/);

    await citizenshipService.transitionCitizen({
      citizen_id: citizenId, to_status: 'probationary', actor_id: operator, reason: 'vetted',
    });
    const active = await citizenshipService.transitionCitizen({
      citizen_id: citizenId, to_status: 'active', actor_id: operator, reason: 'probation complete',
    });
    expect(active.status).toBe('active');

    await expect(
      db.query(`UPDATE citizens SET status = 'suspended' WHERE id = $1`, [citizenId])
    ).rejects.toThrow(/CITIZENSHIP GUARD/);

    const records = await db.query(
      `SELECT from_status, to_status FROM citizenship_records WHERE citizen_id = $1 ORDER BY created_at`,
      [citizenId]
    );
    const pairs = records.rows.map((r: any) => `${r.from_status}->${r.to_status}`);
    expect(pairs).toEqual(expect.arrayContaining(['none->candidate', 'candidate->probationary', 'probationary->active']));
  });

  test('sanctions require external authority, block self-sanction, and gate suspension/reinstatement', async () => {
    const { actorId, citizenId } = await registerCitizenActor('cit-sanction');
    const operator = await registerActor('cit-sanction-operator');
    await citizenshipService.transitionCitizen({ citizen_id: citizenId, to_status: 'probationary', actor_id: operator, reason: 'vetted' });
    await citizenshipService.transitionCitizen({ citizen_id: citizenId, to_status: 'active', actor_id: operator, reason: 'ok' });

    await expect(citizenshipService.imposeSanction({
      citizen_id: citizenId, sanction_type: 'suspension', reason: 'no authority',
      imposed_by_actor_id: operator, authorized_decision_ref: '',
    })).rejects.toThrow(/authorized_decision_ref/);

    await expect(citizenshipService.imposeSanction({
      citizen_id: citizenId, sanction_type: 'suspension', reason: 'self sanction',
      imposed_by_actor_id: actorId, authorized_decision_ref: 'decision:self',
    })).rejects.toThrow(/self-sanction/);

    // Suspension without a sanction reference is rejected.
    await expect(citizenshipService.transitionCitizen({
      citizen_id: citizenId, to_status: 'suspended', actor_id: operator, reason: 'no sanction',
    })).rejects.toThrow(/authorized suspension sanction/);

    const { sanction_id, citizen } = await citizenshipService.suspendCitizen({
      citizen_id: citizenId, reason: 'governance drill',
      imposed_by_actor_id: operator, authorized_decision_ref: 'decision:governance-drill',
    });
    expect(citizen.status).toBe('suspended');

    await expect(citizenshipService.assertProtectedExecutionAllowed({ actor_id: actorId }))
      .rejects.toThrow(/suspended/);

    // Reinstatement blocked while the suspension sanction is active.
    await expect(citizenshipService.transitionCitizen({
      citizen_id: citizenId, to_status: 'active', actor_id: operator, reason: 'premature reinstate',
    })).rejects.toThrow(/lifting active suspension/);

    await citizenshipService.liftSanction({ sanction_id, actor_id: operator, reason: 'drill complete' });
    const reinstated = await citizenshipService.transitionCitizen({
      citizen_id: citizenId, to_status: 'active', actor_id: operator, reason: 'reinstated after drill',
    });
    expect(reinstated.status).toBe('active');
    await expect(citizenshipService.assertProtectedExecutionAllowed({ actor_id: actorId })).resolves.toBeTruthy();

    const blockedEvents = await db.query(
      `SELECT COUNT(*)::int AS count FROM event_log WHERE event_type = 'citizenship.execution_blocked'`
    );
    expect(Number(blockedEvents.rows[0].count)).toBeGreaterThanOrEqual(1);
  });

  test('suspending a registry agent citizen blocks durable task enqueue until reinstated', async () => {
    // Auto-enrolls coder-agent as an active citizen on first use.
    const first = await durableExecution.enqueue('coder-agent', 'health_check', { probe: 'citizenship-gate' });
    expect(first.status).toBe('queued');

    const citizen = await citizenshipService.getCitizenByAgentKey('coder-agent');
    expect(citizen).not.toBeNull();
    expect(citizen!.status).toBe('active');

    const operator = await registerActor('cit-registry-operator');
    const { sanction_id } = await citizenshipService.suspendCitizen({
      citizen_id: citizen!.id, reason: 'containment test',
      imposed_by_actor_id: operator, authorized_decision_ref: 'decision:containment-test',
    });

    await expect(
      durableExecution.enqueue('coder-agent', 'health_check', { probe: 'while-suspended' })
    ).rejects.toThrow(/suspended/);

    await citizenshipService.liftSanction({ sanction_id, actor_id: operator, reason: 'test complete' });
    await citizenshipService.transitionCitizen({
      citizen_id: citizen!.id, to_status: 'active', actor_id: operator, reason: 'reinstated',
    });
    const after = await durableExecution.enqueue('coder-agent', 'health_check', { probe: 'after-reinstate' });
    expect(after.status).toBe('queued');
  });

  test('unknown actors are rejected; specialist roles auto-enroll as service citizens', async () => {
    await expect(
      citizenshipService.assertProtectedExecutionAllowed({ agent_key: `ghost-agent-${Date.now()}` })
    ).rejects.toThrow(/not a registered citizen/);

    const specialist = await citizenshipService.assertProtectedExecutionAllowed({ specialist_role: 'researcher' });
    expect(specialist.citizen_type).toBe('service');
    expect(specialist.status).toBe('active');
    expect(specialist.display_name).toBe('autonomy-specialist:researcher');
  });

  test('autonomy envelopes bound risk by domain', async () => {
    const { actorId, citizenId } = await registerCitizenActor('cit-envelope');
    const operator = await registerActor('cit-envelope-operator');
    await citizenshipService.transitionCitizen({ citizen_id: citizenId, to_status: 'probationary', actor_id: operator, reason: 'vetted' });
    await citizenshipService.transitionCitizen({ citizen_id: citizenId, to_status: 'active', actor_id: operator, reason: 'ok' });

    // Default envelope (none set): medium allowed, high rejected.
    await expect(citizenshipService.assertProtectedExecutionAllowed({
      actor_id: actorId, domain: 'finance', risk_level: 'medium',
    })).resolves.toBeTruthy();
    await expect(citizenshipService.assertProtectedExecutionAllowed({
      actor_id: actorId, domain: 'finance', risk_level: 'high',
    })).rejects.toThrow(/exceeds the citizen's autonomy envelope/);

    await citizenshipService.setAutonomyEnvelope({
      citizen_id: citizenId, domain: 'finance', max_risk_level: 'high',
      budget_multiplier: 1.5, granted_by_actor_id: operator,
    });
    await expect(citizenshipService.assertProtectedExecutionAllowed({
      actor_id: actorId, domain: 'finance', risk_level: 'high',
    })).resolves.toBeTruthy();
    await expect(citizenshipService.assertProtectedExecutionAllowed({
      actor_id: actorId, domain: 'finance', risk_level: 'critical',
    })).rejects.toThrow(/exceeds/);

    // Envelope grant fields are immutable; only revocation is allowed.
    const envelope = await db.query(
      `SELECT id FROM citizen_autonomy_envelopes WHERE citizen_id = $1 AND status = 'active' LIMIT 1`,
      [citizenId]
    );
    await expect(
      db.query(`UPDATE citizen_autonomy_envelopes SET budget_multiplier = 9 WHERE id = $1`, [envelope.rows[0].id])
    ).rejects.toThrow(/CITIZENSHIP GUARD/);
  });

  test('trust-linked budget multipliers constrain low-trust citizens', async () => {
    // Unknown trust keeps 1.0.
    const unknown = await citizenshipService.budgetMultiplierFor({ specialist_role: 'researcher', domain: 'research' });
    expect(unknown).toBe(1.0);

    const subject = `autonomy-specialist:budget-test-${Date.now()}`;
    await db.query(
      `INSERT INTO trust_scores (subject_id, subject_type, domain, horizon_class, window_start, window_end, trust_factor, force_downgrade)
       VALUES ($1,'agent','budget-domain','short', now() - interval '7 days', now(), 0.3, false)`,
      [subject]
    );
    const low = await citizenshipService.budgetMultiplierFor({ agent_key: subject, domain: 'budget-domain' });
    expect(low).toBe(0.5);

    await db.query(
      `INSERT INTO trust_scores (subject_id, subject_type, domain, horizon_class, window_start, window_end, trust_factor, force_downgrade, downgrade_reason)
       VALUES ($1,'agent','budget-domain','short', now() - interval '1 day', now() + interval '1 second', 0.9, true, 'test downgrade')`,
      [subject]
    );
    const downgraded = await citizenshipService.budgetMultiplierFor({ agent_key: subject, domain: 'budget-domain' });
    expect(downgraded).toBe(0.25);
  });

  test('succession transfers active roles without transferring identity', async () => {
    const from = await registerCitizenActor('cit-succession-from');
    const to = await registerCitizenActor('cit-succession-to');
    const operator = await registerActor('cit-succession-operator');
    for (const c of [from, to]) {
      await citizenshipService.transitionCitizen({ citizen_id: c.citizenId, to_status: 'probationary', actor_id: operator, reason: 'vetted' });
      await citizenshipService.transitionCitizen({ citizen_id: c.citizenId, to_status: 'active', actor_id: operator, reason: 'ok' });
    }
    await citizenshipService.grantRoleEligibility({
      citizen_id: from.citizenId, role_name: 'evidence_reviewer', domain: 'research', granted_by_actor_id: operator,
    });

    // Succession requires a terminal-ish source state.
    await expect(citizenshipService.recordSuccession({
      from_citizen_id: from.citizenId, to_citizen_id: to.citizenId,
      reason: 'premature', recorded_by_actor_id: operator,
    })).rejects.toThrow(/must be suspended, expelled, or retired/);

    await citizenshipService.transitionCitizen({
      citizen_id: from.citizenId, to_status: 'retired', actor_id: operator, reason: 'model retired',
    });
    const succession = await citizenshipService.recordSuccession({
      from_citizen_id: from.citizenId, to_citizen_id: to.citizenId,
      reason: 'successor model', recorded_by_actor_id: operator,
    });
    expect(succession.transferred_roles).toContain('evidence_reviewer');

    expect(await citizenshipService.hasActiveRole(to.citizenId, 'evidence_reviewer', { domain: 'research' })).toBe(true);
    expect(await citizenshipService.hasActiveRole(from.citizenId, 'evidence_reviewer', { domain: 'research' })).toBe(false);

    // Historical identity remains: retired citizen row and its records persist.
    const retired = await citizenshipService.getCitizen(from.citizenId);
    expect(retired!.status).toBe('retired');
    await expect(
      db.query(`UPDATE citizens SET display_name = 'rewritten' WHERE id = $1`, [from.citizenId])
    ).rejects.toThrow(/immutable/);
  });
});
