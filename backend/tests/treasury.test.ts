import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { treasuryService } from '../src/services/treasury.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql',
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

function uniqueScope(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

describe('civilization economy / treasury (C6)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('accounts open idempotently, funding credits balance', async () => {
    const actor = await registerActor('treasury-fund');
    const scopeId = uniqueScope('civ');
    const account = await treasuryService.openAccount({
      scope_type: 'civilization', scope_id: scopeId, resource_type: 'llm_tokens', actor_id: actor,
    });
    const again = await treasuryService.openAccount({
      scope_type: 'civilization', scope_id: scopeId, resource_type: 'llm_tokens', actor_id: actor,
    });
    expect(again.id).toBe(account.id);

    await treasuryService.fund({
      scope_type: 'civilization', scope_id: scopeId, resource_type: 'llm_tokens',
      amount: 100000, reason: 'initial grant', actor_id: actor,
    });
    const balance = await treasuryService.balance('civilization', scopeId, 'llm_tokens');
    expect(balance!.balance).toBe(100000);
  });

  test('budget proposal -> approve -> allocate transfers between scopes; proposer cannot self-approve; allocation is idempotent', async () => {
    const proposer = await registerActor('treasury-proposer');
    const approver = await registerActor('treasury-approver');
    const civScope = uniqueScope('civ');
    const instScope = uniqueScope('inst');

    await treasuryService.fund({
      scope_type: 'civilization', scope_id: civScope, resource_type: 'compute',
      amount: 5000, reason: 'seed', actor_id: proposer,
    });

    const proposal = await treasuryService.proposeBudget({
      from_scope: { type: 'civilization', id: civScope },
      to_scope: { type: 'institution', id: instScope },
      resource_type: 'compute', amount: 1200, justification: 'institution operating budget', actor_id: proposer,
    });

    await expect(treasuryService.decideBudget({ proposal_id: proposal.id, approve: true, actor_id: proposer }))
      .rejects.toThrow(/cannot be approved by its own proposer/);

    await treasuryService.decideBudget({ proposal_id: proposal.id, approve: true, actor_id: approver });
    const alloc1 = await treasuryService.allocateBudget({ proposal_id: proposal.id, actor_id: approver });
    const alloc2 = await treasuryService.allocateBudget({ proposal_id: proposal.id, actor_id: approver });
    expect(alloc2.allocation_id).toBe(alloc1.allocation_id); // idempotent, no double transfer

    const from = await treasuryService.balance('civilization', civScope, 'compute');
    const to = await treasuryService.balance('institution', instScope, 'compute');
    expect(from!.balance).toBe(3800);
    expect(to!.balance).toBe(1200);
  });

  test('resource policy blocks over-risk / low-trust / over-cap requests and queues on exhaustion', async () => {
    const actor = await registerActor('treasury-policy');
    const scope = uniqueScope('inst');
    await treasuryService.fund({
      scope_type: 'institution', scope_id: scope, resource_type: 'money', amount: 500, reason: 'seed', actor_id: actor,
    });
    const policyKey = `spend-${Date.now()}`;
    await treasuryService.setPolicy({
      policy_key: policyKey, resource_type: 'money', max_risk_level: 'medium',
      min_trust_factor: 0.5, per_request_cap: 200, requires_review_above: 100, actor_id: actor,
    });

    // Exhaustion -> queue.
    expect((await treasuryService.evaluateRequest({
      scope_type: 'institution', scope_id: scope, resource_type: 'money', amount: 10000, policy_key: policyKey,
    })).decision).toBe('queue');

    // Over-risk -> block.
    expect((await treasuryService.evaluateRequest({
      scope_type: 'institution', scope_id: scope, resource_type: 'money', amount: 50, policy_key: policyKey, risk_level: 'high',
    })).decision).toBe('block');

    // Low trust -> block.
    expect((await treasuryService.evaluateRequest({
      scope_type: 'institution', scope_id: scope, resource_type: 'money', amount: 50, policy_key: policyKey, trust_factor: 0.2,
    })).decision).toBe('block');

    // Over per-request cap -> block.
    expect((await treasuryService.evaluateRequest({
      scope_type: 'institution', scope_id: scope, resource_type: 'money', amount: 300, policy_key: policyKey,
    })).decision).toBe('block');

    // Over review threshold -> requires_review.
    expect((await treasuryService.evaluateRequest({
      scope_type: 'institution', scope_id: scope, resource_type: 'money', amount: 150, policy_key: policyKey, trust_factor: 0.9,
    })).decision).toBe('requires_review');

    // Within everything -> allow.
    expect((await treasuryService.evaluateRequest({
      scope_type: 'institution', scope_id: scope, resource_type: 'money', amount: 50, policy_key: policyKey, trust_factor: 0.9,
    })).decision).toBe('allow');
  });

  test('penalties require an authorized decision reference and debit the target on application', async () => {
    const actor = await registerActor('treasury-penalty');
    const scope = uniqueScope('citizen');
    await treasuryService.fund({
      scope_type: 'citizen', scope_id: scope, resource_type: 'llm_tokens', amount: 1000, reason: 'grant', actor_id: actor,
    });

    await expect(treasuryService.imposePenalty({
      target_scope: { type: 'citizen', id: scope }, resource_type: 'llm_tokens', amount: 200,
      reason: 'policy breach', authorized_decision_ref: '', authority: 'judiciary', actor_id: actor,
    })).rejects.toThrow(/authorized decision reference/);

    const penalty = await treasuryService.imposePenalty({
      target_scope: { type: 'citizen', id: scope }, resource_type: 'llm_tokens', amount: 200,
      reason: 'policy breach', authorized_decision_ref: 'ruling:judiciary-9', authority: 'judiciary', actor_id: actor,
    });
    expect(penalty.applied).toBe(true);
    const balance = await treasuryService.balance('citizen', scope, 'llm_tokens');
    expect(balance!.balance).toBe(800);

    // Imposition fields are immutable.
    await expect(
      db.query(`UPDATE penalties SET amount = 1 WHERE id = $1`, [penalty.id])
    ).rejects.toThrow(/PENALTY GUARD/);
  });

  test('cost attribution rolls up by dimension; reconciliation detects a balanced ledger', async () => {
    const actor = await registerActor('treasury-cost');
    const root = await civilizationKernel.ensureCivilizationRoot();
    const scope = uniqueScope('inst');
    await treasuryService.fund({
      scope_type: 'institution', scope_id: scope, resource_type: 'tool_calls', amount: 300, reason: 'seed', actor_id: actor,
    });

    const researchDomain = uniqueScope('research');
    const financeDomain = uniqueScope('finance');
    await treasuryService.recordCost({ resource_type: 'tool_calls', amount: 40, domain: researchDomain, actor_id: actor });
    await treasuryService.recordCost({ resource_type: 'tool_calls', amount: 60, domain: researchDomain, actor_id: actor });
    await treasuryService.recordCost({ resource_type: 'tool_calls', amount: 25, domain: financeDomain, actor_id: actor });

    const rollup = await treasuryService.costRollup('domain', 'tool_calls');
    const research = rollup.find(r => r.key === researchDomain);
    expect(research!.total).toBe(100);

    const recon = await treasuryService.reconcile({ resource_type: 'tool_calls', actor_id: actor });
    expect(recon.balanced).toBe(true);
    expect(recon.imbalance).toBe(0);
    expect(recon.ledger_balance).toBeGreaterThanOrEqual(300);

    const runs = await db.query(
      `SELECT balanced FROM reconciliation_runs WHERE civilization_id = $1 AND resource_type = 'tool_calls' ORDER BY created_at DESC LIMIT 1`,
      [root.id]
    );
    expect(runs.rows[0].balanced).toBe(true);
  });
});
