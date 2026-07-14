import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { capabilityExpansion } from '../src/services/capability-expansion.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql', '135_governance.sql', '136_judiciary.sql',
    '137_collective_epistemics.sql', '138_safe_evolution.sql', '139_capability_expansion.sql',
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

const STAGES = ['risk_review', 'benchmark_design', 'limited_trial', 'calibration_review', 'governance_review'] as const;

async function driveThroughGate(proposalId: string, actorId: string): Promise<void> {
  for (const stage of STAGES) {
    await capabilityExpansion.recordStage({ proposal_id: proposalId, stage, passed: true, summary: `${stage} ok`, actor_id: actorId });
  }
}

describe('capability and domain expansion (C11)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('SCENARIO F: propose -> full gate -> approve -> grant -> route -> restrict -> revoke changes routing', async () => {
    const proposer = await actor('exp-proposer');
    const approver = await actor('exp-approver');
    const stageOfficer = await actor('exp-officer');
    const domain = `medical-triage-${Date.now()}`;
    const capability = `triage_advice_${Date.now()}`;
    const institutionId = `inst-${Date.now()}`;

    const proposal = await capabilityExpansion.propose({
      expansion_type: 'capability_expansion', domain_key: domain, capability_key: capability,
      title: 'Onboard medical triage advice', proposer_actor_id: proposer, competence_proof_id: 'proof:comp-42',
    });
    expect(proposal.status).toBe('proposed');

    // A registry row alone cannot activate — must pass the whole gate before approval.
    await expect(capabilityExpansion.approve({ proposal_id: proposal.id, approver_actor_id: approver }))
      .rejects.toThrow(/governance-reviewed/);

    await driveThroughGate(proposal.id, stageOfficer);

    // Proposer cannot self-approve.
    await expect(capabilityExpansion.approve({ proposal_id: proposal.id, approver_actor_id: proposer }))
      .rejects.toThrow(/cannot approve their own expansion/);

    const approved = await capabilityExpansion.approve({ proposal_id: proposal.id, approver_actor_id: approver });
    expect(approved.status).toBe('approved');

    // Grant the capability to an institution.
    const grant = await capabilityExpansion.grantCapability({
      proposal_id: proposal.id, capability_key: capability, domain_key: domain,
      grantee_scope_type: 'institution', grantee_scope_id: institutionId, actor_id: approver,
    });
    expect(grant.version).toBe(1);

    // Routing: capability is active → new work is allowed.
    let check = await capabilityExpansion.isCapabilityActive({
      capability_key: capability, domain_key: domain, grantee_scope_type: 'institution', grantee_scope_id: institutionId,
    });
    expect(check.active).toBe(true);
    await expect(capabilityExpansion.assertCapabilityGranted({
      capability_key: capability, domain_key: domain, grantee_scope_type: 'institution', grantee_scope_id: institutionId,
    })).resolves.toBeUndefined();

    // Restrict → routing flips immediately (restricted is not active for new work).
    await capabilityExpansion.restrictCapability({ grant_id: grant.grant_id, actor_id: approver, restriction: { max_risk: 'low' }, reason: 'safety concern' });
    check = await capabilityExpansion.isCapabilityActive({
      capability_key: capability, domain_key: domain, grantee_scope_type: 'institution', grantee_scope_id: institutionId,
    });
    expect(check.active).toBe(false);
    expect(check.status).toBe('restricted');
    await expect(capabilityExpansion.assertCapabilityGranted({
      capability_key: capability, domain_key: domain, grantee_scope_type: 'institution', grantee_scope_id: institutionId,
    })).rejects.toThrow(/new work blocked/);

    // Revoke → grant is gone; revoked domains stop receiving new work.
    await capabilityExpansion.revokeCapability({ grant_id: grant.grant_id, actor_id: approver, reason: 'incident' });
    check = await capabilityExpansion.isCapabilityActive({
      capability_key: capability, domain_key: domain, grantee_scope_type: 'institution', grantee_scope_id: institutionId,
    });
    expect(check.active).toBe(false);
    expect(check.status).toBeNull();

    // Revoked grant is terminal.
    await expect(
      db.query(`UPDATE capability_grants SET status = 'active' WHERE id = $1`, [grant.grant_id])
    ).rejects.toThrow(/EXPANSION GUARD/);
  });

  test('a failed gate stage rejects the proposal', async () => {
    const proposer = await actor('exp-fail');
    const officer = await actor('exp-fail-officer');
    const proposal = await capabilityExpansion.propose({
      expansion_type: 'domain_onboarding', domain_key: `risky-${Date.now()}`,
      title: 'risky domain', proposer_actor_id: proposer, competence_proof_id: 'proof:x',
    });
    await capabilityExpansion.recordStage({ proposal_id: proposal.id, stage: 'risk_review', passed: true, summary: 'ok', actor_id: officer });
    await capabilityExpansion.recordStage({ proposal_id: proposal.id, stage: 'benchmark_design', passed: false, summary: 'benchmark unsafe', actor_id: officer });
    const p = await capabilityExpansion.getProposal(proposal.id);
    expect(p!.status).toBe('rejected');
    // No further stages on a rejected proposal.
    await expect(capabilityExpansion.recordStage({ proposal_id: proposal.id, stage: 'limited_trial', passed: true, summary: 'x', actor_id: officer }))
      .rejects.toThrow(/terminal|requires status/);
  });

  test('approval requires a competence proof', async () => {
    const proposer = await actor('exp-noproof');
    const officer = await actor('exp-noproof-officer');
    const approver = await actor('exp-noproof-approver');
    const proposal = await capabilityExpansion.propose({
      expansion_type: 'domain_onboarding', domain_key: `noproof-${Date.now()}`,
      title: 'no proof domain', proposer_actor_id: proposer, // no competence_proof_id
    });
    await driveThroughGate(proposal.id, officer);
    await expect(capabilityExpansion.approve({ proposal_id: proposal.id, approver_actor_id: approver }))
      .rejects.toThrow(/requires a competence proof/);
  });

  test('gate stages must be completed in order', async () => {
    const proposer = await actor('exp-order');
    const officer = await actor('exp-order-officer');
    const proposal = await capabilityExpansion.propose({
      expansion_type: 'domain_onboarding', domain_key: `order-${Date.now()}`,
      title: 'order domain', proposer_actor_id: proposer, competence_proof_id: 'proof:o',
    });
    // Skipping risk_review to benchmark_design is rejected.
    await expect(capabilityExpansion.recordStage({ proposal_id: proposal.id, stage: 'benchmark_design', passed: true, summary: 'x', actor_id: officer }))
      .rejects.toThrow(/requires status proposed|risk_review/);
  });
});
