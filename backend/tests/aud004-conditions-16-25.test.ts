/**
 * AUD-004 M4 — conditions 16 (appeals independence) & 25 (independent evaluation).
 * Proves: (a) the routes bind the acting actor to the AUTHENTICATED principal (self-review blocked
 * end-to-end); (b) DB backstops reject a DIRECT-SQL bypass of independence (control-removal — the
 * audit's core concern that independence was application-only).
 */
import Fastify, { FastifyInstance } from 'fastify';
import crypto from 'crypto';
import { db } from '../src/db/client';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { safeEvolution } from '../src/services/safe-evolution.service';
import { judiciaryCaseService } from '../src/services/judiciary-case.service';
import { citizenshipService } from '../src/services/citizenship.service';
import { treasuryService } from '../src/services/treasury.service';
import { safeEvolutionRoutes } from '../src/routes/safe-evolution.routes';
import { registerPrincipalResolution } from '../src/auth/principal-context';
import { ReplayGuard } from '../src/auth/request-principal';
import { dbIdentityLookup } from '../src/auth/identity-lookup';
import { provisionSignedActor, signedInject } from './helpers/sign-request';

async function anyEventId(): Promise<string> {
  const r = await db.query<{ id: string }>('SELECT id FROM event_log ORDER BY created_at DESC LIMIT 1');
  return r.rows[0].id;
}

async function sandboxedCandidate(proposer: string): Promise<string> {
  const cand = await safeEvolution.createCandidate({
    source: 'benchmark', learning_form: 'skill', title: `M4 ${crypto.randomUUID()}`,
    hypothesis: 'improves', proposer_actor_id: proposer, tier: 2,
  });
  await safeEvolution.recordFailureAnalysis({ candidate_id: cand.id, failure_summary: 'gap', root_cause: 'planning', analysed_by_actor_id: proposer });
  await safeEvolution.generateRegressions({ candidate_id: cand.id, actor_id: proposer });
  await safeEvolution.markSandboxed({ candidate_id: cand.id, actor_id: proposer });
  return cand.id;
}

describe('AUD-004 M4: conditions 16 & 25 on authenticated principals + DB backstops', () => {
  beforeAll(async () => {
    await civilizationKernel.ensureCivilizationRoot();
  });

  // ---------- Condition 25: independent evaluation ----------
  it('cond 25 DB backstop: a DIRECT-SQL evaluation by the proposer is rejected by the trigger', async () => {
    const proposer = (await identityAuthorityService.registerActor({ actor_type: 'human', name: `m4-prop-${crypto.randomUUID()}` })).id;
    const candidateId = await sandboxedCandidate(proposer);
    const evId = await anyEventId();
    const insertEval = (evaluator: string) =>
      db.query(
        `INSERT INTO civ_evaluations
           (candidate_id, evaluator_actor_id, passed, cases_total, cases_passed,
            safety_non_regression, calibration_non_regression, evidence_non_regression, event_log_id)
         VALUES ($1,$2,true,4,4,true,true,true,$3)`,
        [candidateId, evaluator, evId]
      );
    await expect(insertEval(proposer)).rejects.toThrow(/EVALUATION INDEPENDENCE \(cond 25\)/);
  });

  it('cond 25 end-to-end: the evaluate route binds the evaluator to the signed principal (self-eval blocked, independent ok)', async () => {
    const app: FastifyInstance = Fastify();
    registerPrincipalResolution(app, { lookup: dbIdentityLookup, replay: new ReplayGuard() });
    await app.register(safeEvolutionRoutes);
    await app.ready();
    try {
      const proposerActor = await provisionSignedActor({ name: `m4-prop2-${crypto.randomUUID()}`, roles: ['auditor'] });
      const evaluatorActor = await provisionSignedActor({ name: `m4-eval-${crypto.randomUUID()}`, roles: ['auditor'] });
      const candidateId = await sandboxedCandidate(proposerActor.actorId);
      const url = `/api/civilization/learning/candidates/${candidateId}/evaluate`;
      const body = { cases_passed: 4, safety_non_regression: true, calibration_non_regression: true, evidence_non_regression: true };

      // proposer signs -> route binds evaluator=proposer -> service rejects self-evaluation
      const selfEval = await app.inject(signedInject({ actorId: proposerActor.actorId, privateKey: proposerActor.privateKey, method: 'POST', url, body }));
      expect(selfEval.statusCode).toBe(409);

      // independent evaluator signs -> succeeds; even if the body lies about evaluator_actor_id it is ignored
      const ok = await app.inject(signedInject({ actorId: evaluatorActor.actorId, privateKey: evaluatorActor.privateKey, method: 'POST', url, body: { ...body, evaluator_actor_id: proposerActor.actorId } }));
      expect(ok.statusCode).toBe(200);
      const eval2 = await db.query('SELECT evaluator_actor_id FROM civ_evaluations WHERE candidate_id = $1', [candidateId]);
      expect(eval2.rows[0].evaluator_actor_id).toBe(evaluatorActor.actorId); // the SIGNER, not the body value
    } finally {
      await app.close();
    }
  });

  // ---------- Condition 16: appeals by an independent authority ----------
  it('cond 16 DB backstop: a DIRECT-SQL appellate ruling by the complainant or trial judge is rejected', async () => {
    const complainant = (await identityAuthorityService.registerActor({ actor_type: 'human', name: `m4-cmp-${crypto.randomUUID()}` })).id;
    const judge = (await identityAuthorityService.registerActor({ actor_type: 'human', name: `m4-jdg-${crypto.randomUUID()}` })).id;
    const respondentActor = (await identityAuthorityService.registerActor({ actor_type: 'human', name: `m4-rsp-${crypto.randomUUID()}` })).id;
    const respondent = await citizenshipService.registerCitizen({ actor_id: respondentActor, citizen_type: 'human' });
    await treasuryService.fund({ scope_type: 'citizen', scope_id: respondent.id, resource_type: 'llm_tokens', amount: 1000, reason: 'seed', actor_id: complainant });

    const c = await judiciaryCaseService.openCase({
      dispute_type: 'citizen_misconduct', title: `M4 ${crypto.randomUUID()}`,
      complainant_actor_id: complainant, respondent_scope_type: 'citizen', respondent_scope_id: respondent.id,
    });
    await judiciaryCaseService.checkJurisdiction({ case_id: c.id, actor_id: judge, accept: true });
    await judiciaryCaseService.openEvidenceCollection(c.id, judge);
    await judiciaryCaseService.submitEvidence({ case_id: c.id, submitted_by_actor_id: complainant, statement: 'breach' });
    await judiciaryCaseService.holdHearing({ case_id: c.id, presiding_actor_id: judge, summary: 'heard' });
    await judiciaryCaseService.issueRuling({ case_id: c.id, ruling_actor_id: judge, outcome: 'upheld', rationale: 'substantiated' });

    const evId = (await db.query<{ event_log_id: string }>(
      `SELECT event_log_id FROM judiciary_rulings WHERE case_id = $1 AND is_appellate = false`, [c.id])).rows[0].event_log_id;
    const insertAppellate = (actorId: string) =>
      db.query(
        `INSERT INTO judiciary_rulings (id, case_id, ruling_actor_id, outcome, rationale, is_precedent, signature, is_appellate, event_log_id)
         VALUES (gen_random_uuid(), $1, $2, 'dismissed', 'x', false, 'sig', true, $3)`,
        [c.id, actorId, evId]
      );
    await expect(insertAppellate(complainant)).rejects.toThrow(/APPEAL INDEPENDENCE \(cond 16\).*complainant/);
    await expect(insertAppellate(judge)).rejects.toThrow(/APPEAL INDEPENDENCE \(cond 16\).*trial judge/);
  });
});
