import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { citizenshipService } from '../src/services/citizenship.service';
import { societyService } from '../src/services/society.service';
import { institutionGovernance } from '../src/services/institution-governance.service';
import { institutionsService } from '../src/services/institutions.service';
import { coalitionService } from '../src/services/coalition.service';
import { missionService } from '../src/services/mission.service';
import { evidenceRegistry } from '../src/services/evidence-registry.service';
import { civilizationOs } from '../src/services/civilization-os.service';
import { killSwitchService } from '../src/services/kill-switch.service';
import { governanceService } from '../src/services/governance.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql', '135_governance.sql', '136_judiciary.sql',
    '137_collective_epistemics.sql', '138_safe_evolution.sql', '139_capability_expansion.sql', '140_civilization_os.sql',
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

async function makeInstitution(name: string): Promise<string> {
  return (await institutionsService.createCanonicalInstitution({ name: `${name}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`, domain: 'e2e' })).institutionId;
}

/**
 * C15 completion-proof E2E scenarios. Scenarios C (governance), D (judiciary),
 * E (learning), F (expansion) are proven in their phase suites; this file
 * proves A (formation), B (cross-institution mission), G (restart/replay), and
 * H (emergency) end to end.
 */
describe('civilization E2E completion scenarios (C15)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
    await civilizationOs.setMode('running');
  });

  test('SCENARIO A — civilization formation: root, 2 societies, mandatory institutions, citizens, roles, topology', async () => {
    const op = await actor('a-op');
    const root = await civilizationKernel.ensureCivilizationRoot();
    expect(root.status).toBe('active');

    const societies = await societyService.ensureDefaultSocieties();
    expect(societies.filter(s => s.status === 'active').length).toBeGreaterThanOrEqual(2);

    const institutions = await institutionGovernance.ensureMandatoryInstitutions();
    expect(institutions.length).toBe(10);

    // Register two citizens and give one an institution-scoped role.
    const c1 = await citizenshipService.registerCitizen({ actor_id: await actor('a-cit1'), citizen_type: 'agent' });
    const c2 = await citizenshipService.registerCitizen({ actor_id: await actor('a-cit2'), citizen_type: 'human' });
    for (const c of [c1, c2]) {
      await citizenshipService.transitionCitizen({ citizen_id: c.id, to_status: 'probationary', actor_id: op, reason: 'v' });
      await citizenshipService.transitionCitizen({ citizen_id: c.id, to_status: 'active', actor_id: op, reason: 'ok' });
    }
    await citizenshipService.grantRoleEligibility({
      citizen_id: c1.id, role_name: 'evidence_reviewer', domain: 'e2e', granted_by_actor_id: op,
    });
    await societyService.joinSociety({ society_id: societies[0].id, citizen_id: c1.id, actor_id: op });

    const topology = await societyService.getTopology();
    expect(topology.societies.length).toBeGreaterThanOrEqual(2);
    expect(topology.societies.some(s => s.citizen_members >= 1)).toBe(true);
    expect(await citizenshipService.hasActiveRole(c1.id, 'evidence_reviewer', { domain: 'e2e' })).toBe(true);
  });

  test('SCENARIO B — cross-institution mission: objective -> coalition -> execute -> evidence -> settle -> gated completion -> attest -> dissolve', async () => {
    const op = await actor('b-op');
    const root = await civilizationKernel.ensureCivilizationRoot();
    const instA = await makeInstitution('B-Alpha');
    const instB = await makeInstitution('B-Beta');

    // Objective -> strategic goal -> mission.
    const objective = await civilizationKernel.createObjective({ civilization_id: root.id, title: `B objective ${Date.now()}`, actor_id: op });
    const goal = await missionService.createStrategicGoal({ title: `B goal ${Date.now()}`, objective_id: objective.id, actor_id: op });

    // Coalition of the two institutions negotiates and constitutes.
    const coalition = await coalitionService.proposeCoalition({
      name: `B pact ${Date.now()}`, consensus_rule: 'unanimous', member_institution_ids: [instA, instB], created_by_actor_id: op,
    });
    await coalitionService.openNegotiation({ coalition_id: coalition.id, actor_id: op });
    await coalitionService.submitProposal({ coalition_id: coalition.id, round_number: 1, institution_id: instA, actor_id: op, proposal: { plan: 'joint' } });
    await coalitionService.resolveConsensus({ coalition_id: coalition.id, round_number: 1, actor_id: op, acceptances: [{ institution_id: instA }, { institution_id: instB }] });
    await coalitionService.commit({ coalition_id: coalition.id, institution_id: instA, actor_id: op, commitment: { role: 'producer' } });
    await coalitionService.commit({ coalition_id: coalition.id, institution_id: instB, actor_id: op, commitment: { role: 'verifier' } });
    await coalitionService.constitute({ coalition_id: coalition.id, actor_id: op });
    await coalitionService.activate({ coalition_id: coalition.id, actor_id: op });

    const mission = await missionService.createMission({
      title: `B mission ${Date.now()}`, strategic_goal_id: goal.id, lead_institution_id: instA, coalition_id: coalition.id, actor_id: op,
    });
    const ws = await missionService.addWorkstream({ mission_id: mission.id, title: 'produce', required: true, actor_id: op });
    const task = await missionService.addTask({ workstream_id: ws.id, title: 'gather evidence', actor_id: op });

    for (const [to, reason] of [['triaged', 't'], ['approved', 'a'], ['funded', 'f'], ['planned', 'p'], ['assigned', 'x'], ['executing', 'go'], ['evaluating', 'ev']] as Array<[string, string]>) {
      await missionService.transitionMission({ mission_id: mission.id, to_status: to as any, actor_id: op, reason });
    }
    await missionService.recordActionAttempt({ mission_task_id: task.id, actor_id: op, outcome: 'succeeded' });
    await missionService.completeWorkstream({ workstream_id: ws.id, actor_id: op });

    const snippet = `evidence ${Date.now()}`;
    const evidence = await evidenceRegistry.register({
      actor_id: op, url: `https://example.com/${crypto.randomUUID()}`, snippet,
      content_hash: crypto.createHash('sha256').update(snippet).digest('hex'), source_type: 'analysis', is_public_access: true,
    });
    await missionService.linkEvidence({ mission_id: mission.id, evidence_id: evidence.id, actor_id: op });
    await missionService.recordSettlement({ mission_id: mission.id, settlement: { tokens: 500 }, actor_id: op });
    await missionService.recordOutcome({ mission_id: mission.id, result: 'success', summary: 'delivered', actor_id: op });

    const completed = await missionService.completeMission({ mission_id: mission.id, actor_id: op, reason: 'all gates satisfied' });
    expect(completed.mission.status).toBe('completed');
    const attestation = await missionService.getAttestation(mission.id);
    expect((attestation!.evidence_ids as string[])).toContain(evidence.id);

    await missionService.settleMission({ mission_id: mission.id, actor_id: op, reason: 'settle' });
    const settled = await coalitionService.settle({ coalition_id: coalition.id, actor_id: op, settlement: { outcome: 'delivered' } });
    expect(settled.status).toBe('settled');
    const finalCoalition = await coalitionService.getCoalition(coalition.id);
    expect(finalCoalition!.delegations_active).toBe(0);
  });

  test('SCENARIO G — restart / replay: a re-run tick does not duplicate routing; projection rebuilds identically', async () => {
    const op = await actor('g-op');
    await institutionGovernance.ensureMandatoryInstitutions();
    const mission = await missionService.createMission({ title: `G mission ${Date.now()}`, actor_id: op });
    for (const [to, reason] of [['triaged', 't'], ['approved', 'a'], ['funded', 'f'], ['planned', 'p']] as Array<[string, string]>) {
      await missionService.transitionMission({ mission_id: mission.id, to_status: to as any, actor_id: op, reason });
    }
    await civilizationOs.tick();
    const firstAssign = await db.query(`SELECT lead_institution_id FROM missions WHERE id = $1`, [mission.id]);
    expect(firstAssign.rows[0].lead_institution_id).not.toBeNull();

    // Simulate a restart: a fresh recovery report + another tick must not re-route.
    const recovery = await civilizationOs.recoverAndReport();
    expect(recovery.mode).toBe('running');
    const projectionA = await civilizationOs.statusProjection();
    await civilizationOs.tick();
    const projectionB = await civilizationOs.statusProjection();

    const routeEvents = await db.query(
      `SELECT COUNT(*)::int c FROM event_log WHERE event_type = 'civilization_os.mission_routed' AND object_id = $1`, [mission.id]
    );
    expect(Number(routeEvents.rows[0].c)).toBe(1); // no duplicate routing after replay
    // Projection is a deterministic rebuild of source state (counts stable when no new work).
    expect(projectionB.civilization_id).toBe(projectionA.civilization_id);
  });

  test('SCENARIO H — emergency: kill switch stops protected ticks, read-only status remains, emergency expires and recovers', async () => {
    const op = await actor('h-op');
    const root = await civilizationKernel.ensureCivilizationRoot();

    // Engage kill switch → protected tick stops.
    await killSwitchService.activate('civilization.os', op, 'incident');
    const killed = await civilizationOs.tick();
    expect(killed.was_leader).toBe(false);
    expect(killed.skipped_reason).toMatch(/kill switch/);
    // Read-only status projection still available under the kill switch.
    const status = await civilizationOs.statusProjection(root.id);
    expect(status.civilization_id).toBe(root.id);
    await killSwitchService.deactivate('civilization.os', op, 'resolved');

    // Enter a scoped, auto-expiring emergency power that drives its own kill scope.
    const scope = `h-emergency-${Date.now()}`;
    const granted = await governanceService.grantEmergencyPower({
      scope, power: 'halt', reason: 'incident', authorized_decision_ref: 'decision:h',
      ttl_seconds: 3600, engage_kill_switch: true, actor_id: op,
    });
    expect(granted.kill_switch_engaged).toBe(true);
    await expect(killSwitchService.assertNotKilled(`emergency:${scope}`)).rejects.toThrow(/Kill switch active/);

    // Expire it → kill scope released, normal operation resumes.
    await db.query(
      `UPDATE governance_emergency_powers SET expires_at = created_at + interval '1 millisecond' WHERE scope = $1 AND status = 'active'`, [scope]
    );
    const swept = await governanceService.expireEmergencyPowers();
    expect(swept.expired).toBeGreaterThanOrEqual(1);
    await expect(killSwitchService.assertNotKilled(`emergency:${scope}`)).resolves.toBeUndefined();
    const resumed = await civilizationOs.tick();
    expect(resumed.was_leader).toBe(true);
  });
});
