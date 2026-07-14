import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { governanceService } from '../src/services/governance.service';
import { policyEnforcement } from '../src/services/policy-enforcement.service';
import { missionService } from '../src/services/mission.service';
import { killSwitchService } from '../src/services/kill-switch.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql', '135_governance.sql',
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

/** Drive an approved policy_change proposal (>=1 yes vote, simple majority). */
async function passPolicyProposal(body: Record<string, unknown>): Promise<{ proposalId: string; author: string; other: string }> {
  const author = await actor('gov-author');
  const sponsor = await actor('gov-sponsor');
  const voter = await actor('gov-voter');
  const proposal = await governanceService.createProposal({
    title: `Policy ${Date.now()}`, proposal_type: 'policy_change', body, actor_id: author,
  });
  await governanceService.sponsor({ proposal_id: proposal.id, sponsor_actor_id: sponsor });
  await governanceService.recordImpactAssessment({ proposal_id: proposal.id, assessor_actor_id: sponsor, risk_level: 'medium', summary: 'ok' });
  await governanceService.openDeliberation(proposal.id, sponsor);
  await governanceService.recordDeliberation({ proposal_id: proposal.id, actor_id: sponsor, position: 'support', argument: 'needed' });
  await governanceService.openVoting(proposal.id, sponsor);
  await governanceService.castVote({ proposal_id: proposal.id, voter_actor_id: sponsor, vote: 'yes' });
  await governanceService.castVote({ proposal_id: proposal.id, voter_actor_id: voter, vote: 'yes' });
  const decision = await governanceService.closeVoting({ proposal_id: proposal.id, actor_id: sponsor });
  expect(decision.outcome).toBe('approved');
  return { proposalId: proposal.id, author, other: sponsor };
}

describe('governance and constitution (C7)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('SCENARIO C: activating a policy blocks a previously-allowed action; rollback restores it', async () => {
    // Baseline: a critical mission can be created.
    const missionActor = await actor('gov-mission');
    const before = await missionService.createMission({ title: `Pre-policy ${Date.now()}`, risk_level: 'critical', actor_id: missionActor });
    expect(before.status).toBe('proposed');

    // Activate a policy that blocks mission.create at critical risk.
    const { proposalId } = await passPolicyProposal({
      policy_key: `block-critical-missions-${Date.now()}`,
      effect: 'block', match_action_type: 'mission.create', match_min_risk: 'critical',
      description: 'freeze new critical missions',
    });
    const activator = await actor('gov-activator');
    const { runtime_policy_id } = await governanceService.activateProposal({ proposal_id: proposalId, actor_id: activator });
    expect(runtime_policy_id).not.toBeNull();

    // Runtime behaviour changed: a critical mission is now blocked...
    await expect(missionService.createMission({ title: `Blocked ${Date.now()}`, risk_level: 'critical', actor_id: missionActor }))
      .rejects.toThrow(/blocked by governance policy/);
    // ...but a low-risk mission (below the threshold) still passes.
    const lowRisk = await missionService.createMission({ title: `Low ${Date.now()}`, risk_level: 'low', actor_id: missionActor });
    expect(lowRisk.status).toBe('proposed');

    // Roll back the policy → behaviour restored.
    await governanceService.rollbackPolicy({ runtime_policy_id: runtime_policy_id!, actor_id: activator, reason: 'drill complete' });
    const after = await missionService.createMission({ title: `Post-rollback ${Date.now()}`, risk_level: 'critical', actor_id: missionActor });
    expect(after.status).toBe('proposed');

    const proposal = await governanceService.getProposal(proposalId);
    expect(proposal!.status).toBe('rolled_back');
  });

  test('separation of duties: author cannot sponsor or vote on own proposal', async () => {
    const author = await actor('gov-sod');
    const proposal = await governanceService.createProposal({
      title: `SoD ${Date.now()}`, proposal_type: 'general', actor_id: author,
    });
    await expect(governanceService.sponsor({ proposal_id: proposal.id, sponsor_actor_id: author }))
      .rejects.toThrow(/cannot be sponsored by its own author/);

    const sponsor = await actor('gov-sod-sponsor');
    await governanceService.sponsor({ proposal_id: proposal.id, sponsor_actor_id: sponsor });
    await governanceService.recordImpactAssessment({ proposal_id: proposal.id, assessor_actor_id: sponsor, risk_level: 'low', summary: 'ok' });
    await governanceService.openDeliberation(proposal.id, sponsor);
    await governanceService.openVoting(proposal.id, sponsor);
    await expect(governanceService.castVote({ proposal_id: proposal.id, voter_actor_id: author, vote: 'yes' }))
      .rejects.toThrow(/author cannot vote on their own proposal/);
  });

  test('tier-0 constitutional invariants cannot be changed by proposal; constitutional proposals need supermajority + 3 votes', async () => {
    const author = await actor('gov-const');
    await expect(governanceService.createProposal({
      title: 'weaken firewall', proposal_type: 'constitution_change',
      body: { invariant_key: 'reality_simulation_firewall' }, actor_id: author,
    })).rejects.toThrow(/tier-0 invariant .* cannot be changed/);

    const proposal = await governanceService.createProposal({
      title: `Add invariant ${Date.now()}`, proposal_type: 'constitution_change',
      body: { invariant_key: 'new_custom_invariant' }, actor_id: author,
    });
    expect(proposal.quorum_rule).toBe('supermajority');
    expect(proposal.min_votes).toBeGreaterThanOrEqual(3);
  });

  test('quorum: a proposal below min_votes is rejected', async () => {
    const author = await actor('gov-quorum');
    const sponsor = await actor('gov-quorum-sponsor');
    const proposal = await governanceService.createProposal({
      title: `High bar ${Date.now()}`, proposal_type: 'general', min_votes: 5, actor_id: author,
    });
    await governanceService.sponsor({ proposal_id: proposal.id, sponsor_actor_id: sponsor });
    await governanceService.recordImpactAssessment({ proposal_id: proposal.id, assessor_actor_id: sponsor, risk_level: 'low', summary: 'ok' });
    await governanceService.openDeliberation(proposal.id, sponsor);
    await governanceService.openVoting(proposal.id, sponsor);
    await governanceService.castVote({ proposal_id: proposal.id, voter_actor_id: sponsor, vote: 'yes' });
    const decision = await governanceService.closeVoting({ proposal_id: proposal.id, actor_id: sponsor });
    expect(decision.outcome).toBe('rejected'); // only 1 of 5 required votes
  });

  test('require_review policy surfaces a review decision without blocking', async () => {
    const { proposalId } = await passPolicyProposal({
      policy_key: `review-high-missions-${Date.now()}`,
      effect: 'require_review', match_action_type: 'mission.create', match_min_risk: 'high',
    });
    const activator = await actor('gov-review-activator');
    await governanceService.activateProposal({ proposal_id: proposalId, actor_id: activator });

    const decision = await policyEnforcement.evaluate({ action_type: 'mission.create', risk_level: 'high' });
    expect(decision.decision).toBe('require_review');
    // require_review does not throw at the mission gate.
    const missionActor = await actor('gov-review-mission');
    const mission = await missionService.createMission({ title: `Review-req ${Date.now()}`, risk_level: 'high', actor_id: missionActor });
    expect(mission.status).toBe('proposed');
  });

  test('emergency powers engage the kill switch and auto-expire', async () => {
    const opsActor = await actor('gov-emergency');
    const scope = `containment-${Date.now()}`;
    const granted = await governanceService.grantEmergencyPower({
      scope, power: 'halt_promotions', reason: 'incident', authorized_decision_ref: 'decision:incident-7',
      ttl_seconds: 3600, engage_kill_switch: true, actor_id: opsActor,
    });
    expect(granted.kill_switch_engaged).toBe(true);
    await expect(killSwitchService.assertNotKilled(`emergency:${scope}`)).rejects.toThrow(/Kill switch active/);

    // ttl requires bounds.
    await expect(governanceService.grantEmergencyPower({
      scope: `${scope}-bad`, power: 'x', reason: 'y', authorized_decision_ref: 'd', ttl_seconds: 0, actor_id: opsActor,
    })).rejects.toThrow(/ttl_seconds/);

    // Force-expire (expires_at must stay > created_at per CHECK, but already
    // in the past relative to now()) and confirm the kill switch is released.
    await db.query(
      `UPDATE governance_emergency_powers SET expires_at = created_at + interval '1 millisecond' WHERE scope = $1 AND status = 'active'`,
      [scope]
    );
    const swept = await governanceService.expireEmergencyPowers();
    expect(swept.expired).toBeGreaterThanOrEqual(1);
    await expect(killSwitchService.assertNotKilled(`emergency:${scope}`)).resolves.toBeUndefined();
  });
});
