import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { evidenceRegistry } from '../src/services/evidence-registry.service';
import { missionService } from '../src/services/mission.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql', '133_missions.sql',
  ]) {
    await migrationDb.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${file}`), 'utf8'));
  }
}

async function registerActor(prefix: string): Promise<string> {
  const actor = await identityAuthorityService.registerActor({
    actor_type: 'human', name: `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`,
  });
  return actor.id;
}

async function makeEvidence(actorId: string): Promise<string> {
  const snippet = `attested fact ${Date.now()}`;
  const evidence = await evidenceRegistry.register({
    actor_id: actorId,
    url: `https://example.com/evidence/${crypto.randomUUID()}`,
    title: 'mission evidence',
    snippet,
    content_hash: crypto.createHash('sha256').update(snippet).digest('hex'),
    source_type: 'analysis',
    is_public_access: true,
  });
  return evidence.id;
}

/** Drive a mission proposed -> evaluating. */
async function driveToEvaluating(missionId: string, actor: string): Promise<void> {
  const steps: Array<[string, string]> = [
    ['triaged', 'triage'], ['approved', 'approve'], ['funded', 'fund'],
    ['planned', 'plan'], ['assigned', 'assign'], ['executing', 'start'], ['evaluating', 'evaluate'],
  ];
  for (const [to, reason] of steps) {
    await missionService.transitionMission({ mission_id: missionId, to_status: to as any, actor_id: actor, reason });
  }
}

describe('objectives, goals, missions (C5)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('objective -> strategic goal -> mission chain records provenance', async () => {
    const actor = await registerActor('mission-chain');
    const root = await civilizationKernel.ensureCivilizationRoot();
    const objective = await civilizationKernel.createObjective({
      civilization_id: root.id, title: `Grow verified domains ${Date.now()}`, actor_id: actor,
    });
    const goal = await missionService.createStrategicGoal({
      title: `Onboard finance domain ${Date.now()}`, objective_id: objective.id, actor_id: actor,
    });
    const mission = await missionService.createMission({
      title: `Finance evidence sweep ${Date.now()}`, strategic_goal_id: goal.id, actor_id: actor,
    });
    expect(mission.status).toBe('proposed');
    expect(mission.strategic_goal_id).toBe(goal.id);

    const events = await db.query(
      `SELECT event_type FROM event_log WHERE object_id = $1 AND object_type = 'mission'`, [mission.id]
    );
    expect(events.rows.map((r: any) => r.event_type)).toContain('mission.created');
  });

  test('high-risk missions require review; illegal transitions rejected', async () => {
    const actor = await registerActor('mission-risk');
    const mission = await missionService.createMission({
      title: `Critical deploy ${Date.now()}`, risk_level: 'critical', actor_id: actor,
    });
    expect(mission.requires_review).toBe(true);

    await expect(missionService.transitionMission({
      mission_id: mission.id, to_status: 'executing', actor_id: actor, reason: 'skip ahead',
    })).rejects.toThrow(/illegal mission transition/);

    // Direct DB status mutation is blocked.
    await expect(
      db.query(`UPDATE missions SET status = 'completed' WHERE id = $1`, [mission.id])
    ).rejects.toThrow(/MISSION GUARD/);
  });

  test('mission dependencies are acyclic and block execution until satisfied', async () => {
    const actor = await registerActor('mission-deps');
    const a = await missionService.createMission({ title: `Dep-A ${Date.now()}`, actor_id: actor });
    const b = await missionService.createMission({
      title: `Dep-B ${Date.now()}`, depends_on_mission_ids: [a.id], actor_id: actor,
    });

    // Cycle prevention.
    await expect(missionService.addDependency(a.id, b.id)).rejects.toThrow(/cycle/);
    await expect(missionService.addDependency(a.id, a.id)).rejects.toThrow(/cannot depend on itself/);

    // B cannot start executing while A is unfinished.
    for (const [to, reason] of [['triaged', 't'], ['approved', 'a'], ['funded', 'f'], ['planned', 'p']] as Array<[string, string]>) {
      await missionService.transitionMission({ mission_id: b.id, to_status: to as any, actor_id: actor, reason });
    }
    await expect(missionService.transitionMission({
      mission_id: b.id, to_status: 'assigned', actor_id: actor, reason: 'assign',
    })).rejects.toThrow(/unfinished dependencies/);
  });

  test('mission completion is gated on workstreams, evidence, settlement, audit, and outcome', async () => {
    const actor = await registerActor('mission-gate');
    const mission = await missionService.createMission({ title: `Gated mission ${Date.now()}`, actor_id: actor });
    const ws = await missionService.addWorkstream({ mission_id: mission.id, title: 'primary', required: true, actor_id: actor });
    const task = await missionService.addTask({ workstream_id: ws.id, title: 'gather', actor_id: actor });
    await driveToEvaluating(mission.id, actor);

    // Not ready: everything missing.
    let readiness = await missionService.completionReadiness(mission.id);
    expect(readiness.ready).toBe(false);
    await expect(missionService.completeMission({ mission_id: mission.id, actor_id: actor, reason: 'premature' }))
      .rejects.toThrow(/completion blocked/);

    // Complete the task + workstream.
    await missionService.recordActionAttempt({ mission_task_id: task.id, actor_id: actor, outcome: 'succeeded' });
    await missionService.completeWorkstream({ workstream_id: ws.id, actor_id: actor });

    // Still blocked: no evidence/settlement/outcome.
    readiness = await missionService.completionReadiness(mission.id);
    expect(readiness.required_workstreams_complete).toBe(true);
    expect(readiness.has_evidence).toBe(false);

    const evidenceId = await makeEvidence(actor);
    await missionService.linkEvidence({ mission_id: mission.id, evidence_id: evidenceId, actor_id: actor });
    await missionService.recordSettlement({ mission_id: mission.id, settlement: { tokens_used: 100 }, actor_id: actor });
    await missionService.recordOutcome({ mission_id: mission.id, result: 'success', summary: 'evidence gathered', actor_id: actor });

    readiness = await missionService.completionReadiness(mission.id);
    expect(readiness.ready).toBe(true);

    const { attestation_id } = await missionService.completeMission({
      mission_id: mission.id, actor_id: actor, reason: 'all gates satisfied',
    });
    expect(attestation_id).toBeTruthy();

    const attestation = await missionService.getAttestation(mission.id);
    expect(attestation).not.toBeNull();
    expect(attestation!.attestation_hash).toBeTruthy();
    expect((attestation!.evidence_ids as string[])).toContain(evidenceId);
    expect((attestation!.task_graph as any).workstreams.length).toBe(1);
    expect((attestation!.outcome as any).result).toBe('success');

    const settled = await missionService.settleMission({ mission_id: mission.id, actor_id: actor, reason: 'settle' });
    expect(settled.status).toBe('settled');
  });

  test('incomplete workstream cannot be completed while it has running tasks', async () => {
    const actor = await registerActor('mission-ws');
    const mission = await missionService.createMission({ title: `WS mission ${Date.now()}`, actor_id: actor });
    const ws = await missionService.addWorkstream({ mission_id: mission.id, title: 'primary', actor_id: actor });
    await missionService.addTask({ workstream_id: ws.id, title: 'pending task', actor_id: actor });
    await expect(missionService.completeWorkstream({ workstream_id: ws.id, actor_id: actor }))
      .rejects.toThrow(/incomplete tasks/);
  });

  test('failed action attempts count attempts and compensation flags reversible tasks', async () => {
    const actor = await registerActor('mission-attempts');
    const mission = await missionService.createMission({ title: `Attempt mission ${Date.now()}`, actor_id: actor });
    const ws = await missionService.addWorkstream({ mission_id: mission.id, title: 'ws', actor_id: actor });
    const task = await missionService.addTask({ workstream_id: ws.id, title: 'risky', reversible: true, actor_id: actor });

    const first = await missionService.recordActionAttempt({ mission_task_id: task.id, actor_id: actor, outcome: 'failed' });
    expect(first.attempt_number).toBe(1);
    const comp = await missionService.recordActionAttempt({ mission_task_id: task.id, actor_id: actor, outcome: 'compensated' });
    expect(comp.attempt_number).toBe(2);

    const row = await db.query(`SELECT attempts, compensated FROM mission_tasks WHERE id = $1`, [task.id]);
    expect(row.rows[0].attempts).toBe(2);
    expect(row.rows[0].compensated).toBe(true);

    const attempts = await db.query(
      `SELECT outcome FROM mission_action_attempts WHERE mission_task_id = $1 ORDER BY attempt_number`, [task.id]
    );
    expect(attempts.rows.map((r: any) => r.outcome)).toEqual(['failed', 'compensated']);
  });
});
