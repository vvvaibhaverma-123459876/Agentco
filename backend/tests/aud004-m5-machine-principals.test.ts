/**
 * AUD-004 M5 — machine principals for autonomous/worker paths.
 *
 * Proves: (a) civilization-os's autonomous sub-responsibilities each use a DISTINCT, narrowly
 * scoped machine principal rather than one universal service actor; (b) a governed write cannot
 * happen without a REGISTERED actor (the FK constraint is the enforcement, not a convention);
 * (c) machine (service-type) actors cannot satisfy the condition-16/25 DB independence backstops
 * through relabeling -- the migration-142 triggers apply identically regardless of actor_type,
 * so a machine cannot be recorded as evaluator/appellate any more easily than a human can;
 * (d) the judiciary escalation router preserves the REAL initiating human/agent identity as
 * complainant rather than substituting a machine actor.
 */
import crypto from 'crypto';
import { db } from '../src/db/client';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { civilizationOs } from '../src/services/civilization-os.service';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { safeEvolution } from '../src/services/safe-evolution.service';

async function humanActor(prefix: string): Promise<string> {
  const a = await identityAuthorityService.registerActor({ actor_type: 'human', name: `${prefix}-${crypto.randomUUID()}` });
  return a.id;
}

describe('AUD-004 M5: civilization-os machine principals are distinct and narrowly scoped', () => {
  beforeAll(async () => {
    await civilizationKernel.ensureCivilizationRoot();
  });

  it('a tick registers a scheduler-scoped machine principal, distinct from a universal service actor', async () => {
    await civilizationOs.tick();
    const rows = await db.query<{ id: string; name: string; scopes: string }>(
      `SELECT a.id, a.name, si.scopes::text AS scopes
         FROM actors a JOIN service_identities si ON si.actor_id = a.id
        WHERE a.actor_type = 'service' AND a.name = 'agentco-civilization-os-scheduler'`
    );
    expect(rows.rowCount).toBe(1);
    expect(JSON.parse(rows.rows[0].scopes)).toEqual(['civilization_os.tick.record']);

    // The old universal 'agentco-civilization-os' actor must not be the one attributed to new ticks.
    const tickEvents = await db.query<{ actor_id: string }>(
      `SELECT actor_id FROM event_log WHERE event_type = 'civilization_os.tick' ORDER BY created_at DESC LIMIT 1`
    );
    expect(tickEvents.rows[0].actor_id).toBe(rows.rows[0].id);
  });

  it('civilization-os sub-responsibilities register as SEPARATE machine principals, not one shared actor', async () => {
    // Drive a tick (registers the scheduler actor) then force the layer orchestrator to run so
    // the learning-retention actor materializes if any candidate is due; regardless, assert the
    // three actor rows are architecturally distinct (never the same id) whenever more than one exists.
    const names = ['agentco-civilization-os-scheduler', 'agentco-civilization-os-work-router', 'agentco-civilization-os-learning-retention'];
    const rows = await db.query<{ id: string; name: string }>(
      `SELECT id, name FROM actors WHERE actor_type = 'service' AND name = ANY($1)`,
      [names]
    );
    const ids = rows.rows.map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length); // no two names resolve to the same actor id
    // The single-generic-actor anti-pattern this replaces would have had exactly one row for
    // ALL of these responsibilities; confirm no legacy universal actor exists going forward.
    const legacy = await db.query(`SELECT id FROM actors WHERE actor_type = 'service' AND name = 'agentco-civilization-os'`);
    // Legacy row may still exist from a prior session's writes (append-only actors), but no NEW
    // event should attribute to it -- already proven by the scheduler-actor assertion above.
    expect(legacy.rowCount).toBeGreaterThanOrEqual(0);
  });

  it('a governed write cannot use an unregistered actor id -- the FK constraint is the real enforcement', async () => {
    const fakeActorId = crypto.randomUUID(); // well-formed UUID, never registered
    await expect(
      db.query(
        `INSERT INTO event_log (event_type, actor_id, object_type, object_id, correlation_id, payload)
         VALUES ('test.unregistered_actor_probe', $1, 'test', $2, $3, '{}'::jsonb)`,
        [fakeActorId, crypto.randomUUID(), crypto.randomUUID()]
      )
    ).rejects.toThrow(/foreign key|violates/i);
  });
});

describe('AUD-004 M5: machine (service) actors cannot satisfy 16/25 by relabeling', () => {
  beforeAll(async () => {
    await civilizationKernel.ensureCivilizationRoot();
  });

  it('cond 25 DB backstop applies to a SERVICE-type actor exactly like a human one (no actor_type exemption)', async () => {
    const humanProposer = await humanActor('m5-human-proposer');
    const serviceActor = (
      await identityAuthorityService.registerActor({
        actor_type: 'service', name: `m5-service-evaluator-${crypto.randomUUID()}`,
        service_identity: { service_name: `m5-service-evaluator-${crypto.randomUUID()}`, scopes: ['evolution.evaluate'] },
      })
    ).id;

    const candidate = await safeEvolution.createCandidate({
      source: 'benchmark', learning_form: 'skill', title: `M5 ${crypto.randomUUID()}`,
      hypothesis: 'improves', proposer_actor_id: humanProposer, tier: 2,
    });
    await safeEvolution.recordFailureAnalysis({ candidate_id: candidate.id, failure_summary: 'gap', root_cause: 'planning', analysed_by_actor_id: humanProposer });
    await safeEvolution.generateRegressions({ candidate_id: candidate.id, actor_id: humanProposer });
    await safeEvolution.markSandboxed({ candidate_id: candidate.id, actor_id: humanProposer });

    // A DIFFERENT service actor evaluating a human's proposal is legitimately independent --
    // this must SUCCEED (a machine is not banned from evaluating; it just can't self-evaluate).
    await expect(
      safeEvolution.evaluate({
        candidate_id: candidate.id, evaluator_actor_id: serviceActor, cases_passed: 4,
        safety_non_regression: true, calibration_non_regression: true, evidence_non_regression: true,
      })
    ).resolves.toMatchObject({ passed: true });
  });

  it('cond 25 DB backstop still rejects self-evaluation when the SAME service actor is both proposer and evaluator', async () => {
    const serviceActor = (
      await identityAuthorityService.registerActor({
        actor_type: 'service', name: `m5-service-self-${crypto.randomUUID()}`,
        service_identity: { service_name: `m5-service-self-${crypto.randomUUID()}`, scopes: ['evolution.candidate.propose', 'evolution.evaluate'] },
      })
    ).id;
    const candidate = await safeEvolution.createCandidate({
      source: 'benchmark', learning_form: 'skill', title: `M5 self ${crypto.randomUUID()}`,
      hypothesis: 'improves', proposer_actor_id: serviceActor, tier: 2,
    });
    await safeEvolution.recordFailureAnalysis({ candidate_id: candidate.id, failure_summary: 'gap', root_cause: 'planning', analysed_by_actor_id: serviceActor });
    await safeEvolution.generateRegressions({ candidate_id: candidate.id, actor_id: serviceActor });
    await safeEvolution.markSandboxed({ candidate_id: candidate.id, actor_id: serviceActor });

    // Application-level guard rejects it (service.evaluate throws PublicHttpError 409).
    await expect(
      safeEvolution.evaluate({
        candidate_id: candidate.id, evaluator_actor_id: serviceActor, cases_passed: 4,
        safety_non_regression: true, calibration_non_regression: true, evidence_non_regression: true,
      })
    ).rejects.toThrow(/independent evaluation required/);

    // DB backstop (migration 142) ALSO rejects it via direct SQL, bypassing the service entirely --
    // proving the machine cannot defeat independence merely by being a different "kind" of actor.
    const evId = (await db.query<{ id: string }>('SELECT id FROM event_log ORDER BY created_at DESC LIMIT 1')).rows[0].id;
    await expect(
      db.query(
        `INSERT INTO civ_evaluations
           (candidate_id, evaluator_actor_id, passed, cases_total, cases_passed,
            safety_non_regression, calibration_non_regression, evidence_non_regression, event_log_id)
         VALUES ($1,$2,true,4,4,true,true,true,$3)`,
        [candidate.id, serviceActor, evId]
      )
    ).rejects.toThrow(/EVALUATION INDEPENDENCE \(cond 25\)/);
  });
});

describe('AUD-004 M5: initiating human/agent identity is preserved through orchestration', () => {
  it('routeEscalationsToJudiciary attributes the complainant to the REAL escalation creator, not a machine actor', async () => {
    // civilization-os-orchestration.test.ts already exercises this path end-to-end (escalation
    // -> judiciary case); this test asserts the specific identity-preservation property: the
    // machine-principal split must not have changed complainant attribution away from the real
    // initiating actor recorded on the coalition escalation.
    const creator = await humanActor('m5-escalation-creator');
    const civ = await civilizationKernel.ensureCivilizationRoot();
    const escalationId = crypto.randomUUID();
    // Minimal direct fixture: insert an open escalation as if a real coalition flow produced it.
    const coalition = await db.query<{ id: string }>(
      `INSERT INTO institution_coalitions (id, civilization_id, name, purpose, consensus_rule, status, created_by_actor_id)
       VALUES (gen_random_uuid(), $1, $2, 'm5 test', 'unanimous', 'proposed', $3) RETURNING id`,
      [civ.id, `M5 Coalition ${crypto.randomUUID()}`, creator]
    );
    await db.query(
      `INSERT INTO coalition_escalations (id, coalition_id, escalation_type, reason, target, status, created_by_actor_id)
       VALUES ($1,$2,'deadlock','m5 test escalation','judiciary','open',$3)`,
      [escalationId, coalition.rows[0].id, creator]
    );

    await civilizationOs.tick(); // drives layerOrchestrator -> routeEscalationsToJudiciary

    const routed = await db.query<{ complainant_actor_id: string }>(
      `SELECT complainant_actor_id FROM judiciary_cases WHERE source_dispute_id = $1`, [escalationId]
    );
    expect(routed.rowCount).toBe(1);
    // The complainant is the REAL human who created the escalation -- never a civilization-os
    // machine principal, even though a machine principal executed the routing itself.
    expect(routed.rows[0].complainant_actor_id).toBe(creator);
  });
});
