import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { FastifyInstance } from 'fastify';
import { build } from '../src/server';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { institutionsService } from '../src/services/institutions.service';
import { coalitionService } from '../src/services/coalition.service';
import { provisionSignedActor, signHeaders } from './helpers/sign-request';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
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

async function makeInstitution(name: string): Promise<string> {
  const created = await institutionsService.createCanonicalInstitution({
    name: `${name}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`, domain: 'coalitions',
  });
  return created.institutionId;
}

function authHeaders() {
  return process.env.AGENTCO_API_KEY ? { 'x-api-key': process.env.AGENTCO_API_KEY } : {};
}

// AUD-004: privileged coalition routes now require a signed principal, not just the API key.
function signed(actor: { actorId: string; privateKey: import('crypto').KeyObject }, method: string, url: string, body?: unknown) {
  return { ...authHeaders(), ...signHeaders({ actorId: actor.actorId, privateKey: actor.privateKey, method, url, body }) };
}

describe('institution coalitions (C4)', () => {
  let app: FastifyInstance;

  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
    app = await build();
  });

  afterAll(async () => {
    await app.close();
  });

  test('full lifecycle: propose -> negotiate -> commit -> constitute -> activate -> settle -> dissolve delegations', async () => {
    const operator = await registerActor('coal-lifecycle');
    const instA = await makeInstitution('Alpha');
    const instB = await makeInstitution('Beta');

    const coalition = await coalitionService.proposeCoalition({
      name: `Alpha-Beta Pact ${Date.now()}`,
      purpose: 'joint benchmark exchange',
      consensus_rule: 'unanimous',
      member_institution_ids: [instA, instB],
      created_by_actor_id: operator,
    });
    expect(coalition.status).toBe('proposed');

    const round = await coalitionService.openNegotiation({ coalition_id: coalition.id, actor_id: operator });
    expect(round.round_number).toBe(1);

    await coalitionService.submitProposal({
      coalition_id: coalition.id, round_number: 1, institution_id: instA, actor_id: operator,
      proposal: { terms: 'A delivers weekly' },
    });
    const consensus = await coalitionService.resolveConsensus({
      coalition_id: coalition.id, round_number: 1, actor_id: operator,
      acceptances: [{ institution_id: instA }, { institution_id: instB }],
    });
    expect(consensus.outcome).toBe('approved');

    // Constitution requires accepted commitments from all members.
    await expect(coalitionService.constitute({ coalition_id: coalition.id, actor_id: operator }))
      .rejects.toThrow(/accepted commitments/);
    await coalitionService.commit({ coalition_id: coalition.id, institution_id: instA, actor_id: operator, commitment: { role: 'producer' } });
    await coalitionService.commit({ coalition_id: coalition.id, institution_id: instB, actor_id: operator, commitment: { role: 'verifier' } });
    const constituted = await coalitionService.constitute({ coalition_id: coalition.id, actor_id: operator });
    expect(constituted.status).toBe('constituted');

    await coalitionService.activate({ coalition_id: coalition.id, actor_id: operator });
    await coalitionService.grantDelegation({
      coalition_id: coalition.id, from_institution_id: instA,
      delegated_authority_key: 'sign_on_behalf', granted_by_actor_id: operator,
    });

    const beforeSettle = await coalitionService.getCoalition(coalition.id);
    expect(beforeSettle!.delegations_active).toBe(1);

    const settled = await coalitionService.settle({
      coalition_id: coalition.id, actor_id: operator, settlement: { outcome: 'delivered', disputes: 0 },
    });
    expect(settled.status).toBe('settled');

    const afterSettle = await coalitionService.getCoalition(coalition.id);
    expect(afterSettle!.settled).toBe(true);
    expect(afterSettle!.delegations_active).toBe(0); // dissolution revoked delegated authority

    // Terminal coalition cannot transition further, even by direct DB write.
    await expect(
      db.query(`UPDATE institution_coalitions SET status = 'active' WHERE id = $1`, [coalition.id])
    ).rejects.toThrow(/COALITION GUARD/);
  });

  test('non-members cannot submit proposals; consensus deadlock escalates to governance', async () => {
    const operator = await registerActor('coal-deadlock');
    const instA = await makeInstitution('Gamma');
    const instB = await makeInstitution('Delta');
    const outsider = await makeInstitution('Outsider');

    const coalition = await coalitionService.proposeCoalition({
      name: `Gamma-Delta Pact ${Date.now()}`,
      consensus_rule: 'unanimous',
      member_institution_ids: [instA, instB],
      created_by_actor_id: operator,
    });
    await coalitionService.openNegotiation({ coalition_id: coalition.id, actor_id: operator });

    await expect(coalitionService.submitProposal({
      coalition_id: coalition.id, round_number: 1, institution_id: outsider, actor_id: operator,
      proposal: { terms: 'intrusion' },
    })).rejects.toThrow(/not an active member/);

    // Only one of two unanimous members accepts → deadlock → governance escalation.
    const consensus = await coalitionService.resolveConsensus({
      coalition_id: coalition.id, round_number: 1, actor_id: operator,
      acceptances: [{ institution_id: instA }],
    });
    expect(consensus.outcome).toBe('deadlocked');
    expect(consensus.escalation_id).toBeTruthy();

    const escalation = await db.query(
      `SELECT escalation_type, target FROM coalition_escalations WHERE id = $1`,
      [consensus.escalation_id]
    );
    expect(escalation.rows[0]).toEqual({ escalation_type: 'deadlock', target: 'governance' });
  });

  test('dissent is retained and cannot be silently discarded', async () => {
    const operator = await registerActor('coal-dissent');
    const instA = await makeInstitution('Epsilon');
    const instB = await makeInstitution('Zeta');
    const coalition = await coalitionService.proposeCoalition({
      name: `Epsilon-Zeta Pact ${Date.now()}`,
      consensus_rule: 'majority',
      member_institution_ids: [instA, instB],
      created_by_actor_id: operator,
    });
    await coalitionService.openNegotiation({ coalition_id: coalition.id, actor_id: operator });
    const dissent = await coalitionService.recordDissent({
      coalition_id: coalition.id, institution_id: instB, actor_id: operator,
      reason: 'terms disadvantage Zeta', round_number: 1,
    });
    expect(dissent.id).toBeTruthy();

    await expect(
      db.query(`UPDATE coalition_dissents SET reason = 'redacted' WHERE id = $1`, [dissent.id])
    ).rejects.toThrow(/append-only/);
    await expect(
      db.query(`DELETE FROM coalition_dissents WHERE id = $1`, [dissent.id])
    ).rejects.toThrow(/may not be deleted/);

    // A dissent message is also persisted in the coalition thread.
    const messages = await db.query(
      `SELECT COUNT(*)::int AS count FROM coalition_messages WHERE coalition_id = $1 AND message_type = 'dissent'`,
      [coalition.id]
    );
    expect(Number(messages.rows[0].count)).toBe(1);
  });

  test('failed coalitions retain complete settlement and dissent records', async () => {
    const operator = await registerActor('coal-failed');
    const instA = await makeInstitution('Eta');
    const instB = await makeInstitution('Theta');
    const coalition = await coalitionService.proposeCoalition({
      name: `Eta-Theta Pact ${Date.now()}`,
      member_institution_ids: [instA, instB],
      created_by_actor_id: operator,
    });
    await coalitionService.openNegotiation({ coalition_id: coalition.id, actor_id: operator });
    await coalitionService.recordDissent({
      coalition_id: coalition.id, institution_id: instA, actor_id: operator, reason: 'irreconcilable terms',
    });
    const failed = await coalitionService.terminate({
      coalition_id: coalition.id, actor_id: operator, terminal_status: 'failed',
      reason: 'negotiation collapsed',
    });
    expect(failed.status).toBe('failed');

    const full = await coalitionService.getCoalition(coalition.id);
    expect(full!.settled).toBe(true); // settlement record preserved even for failure
    expect(full!.dissents).toBe(1);
    const failureRow = await db.query(
      `SELECT failure_reason FROM institution_coalitions WHERE id = $1`,
      [coalition.id]
    );
    expect(failureRow.rows[0].failure_reason).toBe('negotiation collapsed');
  });

  test('weighted-majority consensus tallies stake weights', async () => {
    const operator = await registerActor('coal-weighted');
    const instA = await makeInstitution('Iota');
    const instB = await makeInstitution('Kappa');
    const instC = await makeInstitution('Lambda');
    const coalition = await coalitionService.proposeCoalition({
      name: `Weighted Pact ${Date.now()}`,
      consensus_rule: 'weighted_majority',
      member_institution_ids: [instA, instB, instC],
      created_by_actor_id: operator,
    });
    await coalitionService.openNegotiation({ coalition_id: coalition.id, actor_id: operator });
    // One high-weight acceptor outweighs the 3-member base (3.0): weight 2.0 alone is not > 1.5, need >1.5.
    const consensus = await coalitionService.resolveConsensus({
      coalition_id: coalition.id, round_number: 1, actor_id: operator,
      acceptances: [{ institution_id: instA, weight: 2.5 }],
    });
    expect(consensus.outcome).toBe('approved'); // 2.5*2=5 > base 3
  });

  test('routes return clean validation and not-found responses', async () => {
    const operator = await provisionSignedActor({ name: `coal-validate-${crypto.randomUUID()}`, roles: ['civilization_operator'] });
    const badCreate = await app.inject({
      method: 'POST',
      url: '/api/civilization/coalitions',
      headers: signed(operator, 'POST', '/api/civilization/coalitions', {}),
      payload: {},
    });
    expect(badCreate.statusCode).toBe(400);
    expect(JSON.parse(badCreate.body)).toEqual({ error: 'name is required' });

    const missing = await app.inject({
      method: 'GET',
      url: `/api/civilization/coalitions/${crypto.randomUUID()}`,
      headers: authHeaders(),
    });
    expect(missing.statusCode).toBe(404);
    expect(JSON.parse(missing.body)).toEqual({ error: 'not found' });
  });

  test('route-level lifecycle returns plain JSON through Fastify', async () => {
    const operatorId = await registerActor('coal-route');
    const operator = await provisionSignedActor({ name: `coal-route-signer-${crypto.randomUUID()}`, roles: ['civilization_operator'] });
    const instA = await makeInstitution('RouteAlpha');
    const instB = await makeInstitution('RouteBeta');

    const createUrl = '/api/civilization/coalitions';
    const createBody = {
      name: `Route Pact ${Date.now()}`,
      purpose: 'route-level lifecycle proof',
      consensus_rule: 'unanimous',
      member_institution_ids: [instA, instB],
      created_by_actor_id: operatorId,
    };
    const create = await app.inject({
      method: 'POST', url: createUrl, headers: signed(operator, 'POST', createUrl, createBody), payload: createBody,
    });
    expect(create.statusCode).toBe(201);
    const coalition = JSON.parse(create.body);
    expect(coalition.id).toBeTruthy();
    expect(coalition.status).toBe('proposed');
    // AUD-004: the AUTHENTICATED signer is now the coalition creator, not the body's created_by_actor_id.
    expect(coalition.created_by_actor_id).toBe(operator.actorId);

    const negotiateUrl = `/api/civilization/coalitions/${coalition.id}/negotiate`;
    const negotiate = await app.inject({
      method: 'POST', url: negotiateUrl, headers: signed(operator, 'POST', negotiateUrl, {}), payload: {},
    });
    expect(negotiate.statusCode).toBe(201);
    expect(JSON.parse(negotiate.body)).toEqual({ round_number: 1 });

    const proposalUrl = `/api/civilization/coalitions/${coalition.id}/proposals`;
    const proposalBody = { round_number: 1, institution_id: instA, proposal: { terms: 'route proof terms' } };
    const proposal = await app.inject({
      method: 'POST', url: proposalUrl, headers: signed(operator, 'POST', proposalUrl, proposalBody), payload: proposalBody,
    });
    expect(proposal.statusCode).toBe(201);
    expect(JSON.parse(proposal.body).id).toBeTruthy();

    const consensusUrl = `/api/civilization/coalitions/${coalition.id}/consensus`;
    const consensusBody = { round_number: 1, acceptances: [{ institution_id: instA }, { institution_id: instB }] };
    const consensus = await app.inject({
      method: 'POST', url: consensusUrl, headers: signed(operator, 'POST', consensusUrl, consensusBody), payload: consensusBody,
    });
    expect(consensus.statusCode).toBe(200);
    expect(JSON.parse(consensus.body).outcome).toBe('approved');

    for (const institution_id of [instA, instB]) {
      const commitUrl = `/api/civilization/coalitions/${coalition.id}/commitments`;
      const commitBody = { institution_id, commitment: { route: true } };
      const commitment = await app.inject({
        method: 'POST', url: commitUrl, headers: signed(operator, 'POST', commitUrl, commitBody), payload: commitBody,
      });
      expect(commitment.statusCode).toBe(201);
      expect(JSON.parse(commitment.body).id).toBeTruthy();
    }

    const constituteUrl = `/api/civilization/coalitions/${coalition.id}/constitute`;
    const constituted = await app.inject({
      method: 'POST', url: constituteUrl, headers: signed(operator, 'POST', constituteUrl, {}), payload: {},
    });
    expect(constituted.statusCode).toBe(200);
    expect(JSON.parse(constituted.body).status).toBe('constituted');

    const activateUrl = `/api/civilization/coalitions/${coalition.id}/activate`;
    const activated = await app.inject({
      method: 'POST', url: activateUrl, headers: signed(operator, 'POST', activateUrl, {}), payload: {},
    });
    expect(activated.statusCode).toBe(200);
    expect(JSON.parse(activated.body).status).toBe('active');

    const delegationUrl = `/api/civilization/coalitions/${coalition.id}/delegations`;
    const delegationBody = { from_institution_id: instA, delegated_authority_key: 'route_sign_on_behalf' };
    const delegation = await app.inject({
      method: 'POST', url: delegationUrl, headers: signed(operator, 'POST', delegationUrl, delegationBody), payload: delegationBody,
    });
    expect(delegation.statusCode).toBe(201);
    expect(JSON.parse(delegation.body).id).toBeTruthy();

    const settleUrl = `/api/civilization/coalitions/${coalition.id}/settle`;
    const settleBody = { settlement: { route: 'complete' } };
    const settled = await app.inject({
      method: 'POST', url: settleUrl, headers: signed(operator, 'POST', settleUrl, settleBody), payload: settleBody,
    });
    expect(settled.statusCode).toBe(200);
    expect(JSON.parse(settled.body).status).toBe('settled');

    const read = await app.inject({
      method: 'GET',
      url: `/api/civilization/coalitions/${coalition.id}`,
      headers: authHeaders(),
    });
    expect(read.statusCode).toBe(200);
    const body = JSON.parse(read.body);
    expect(body.settled).toBe(true);
    expect(body.delegations_active).toBe(0);
    expect(body).not.toHaveProperty('raw');
    expect(body).not.toHaveProperty('sent');
  });
});
