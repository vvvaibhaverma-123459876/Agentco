import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { resourceLedger } from './resource-ledger.service';
import { civilizationKernel } from './civilization-kernel.service';
import { PublicHttpError } from '../http-errors';

/**
 * Civilization economy / treasury (build phase C6).
 *
 * Scopes resource accounts to the civilization hierarchy and governs
 * allocation over them. Two-phase reserve/settle stays in
 * ResourceLedgerService; this layer adds budgeting, penalties (which require
 * governance or judiciary authority), cost attribution, and reconciliation.
 *
 * Every treasury-backed resource account is owned by a single economy service
 * actor; scope is tracked in treasury_accounts. Balances therefore reconcile
 * against the canonical ledger without a parallel balance store.
 */

export type ScopeType = 'civilization' | 'society' | 'institution' | 'coalition' | 'mission' | 'citizen';
export type EconomyResource = 'compute' | 'llm_tokens' | 'tool_calls' | 'money' | 'time_seconds' | 'memory_bytes' | 'human_review';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

const RISK_RANK: Record<RiskLevel, number> = { low: 0, medium: 1, high: 2, critical: 3 };
const RESOURCE_UNIT: Record<EconomyResource, string> = {
  compute: 'core_seconds', llm_tokens: 'tokens', tool_calls: 'calls', money: 'usd_cents',
  time_seconds: 'seconds', memory_bytes: 'bytes', human_review: 'review_minutes',
};

export interface TreasuryAccountRecord {
  id: string;
  civilization_id: string;
  scope_type: ScopeType;
  scope_id: string;
  resource_type: EconomyResource;
  resource_account_id: string;
  status: 'active' | 'frozen' | 'closed';
}

export class TreasuryService {
  // -------------------------------------------------------------------------
  // Accounts
  // -------------------------------------------------------------------------

  async openAccount(input: {
    scope_type: ScopeType; scope_id: string; resource_type: EconomyResource; actor_id: string;
    civilization_id?: string;
  }): Promise<TreasuryAccountRecord> {
    const existing = await this.getAccount(input.scope_type, input.scope_id, input.resource_type);
    if (existing) return existing;

    const civilizationId = input.civilization_id ?? (await this.rootId());
    // Each scope owns its resource accounts via a dedicated actor, so the
    // ledger's (owner, resource_type) uniqueness gives exactly one account per
    // (scope, resource_type) — balances never collapse across scopes.
    const scopeActor = await this.scopeActor(input.scope_type, input.scope_id);
    const resourceAccount = await resourceLedger.createAccount({
      owner_actor_id: scopeActor,
      resource_type: input.resource_type,
      unit: RESOURCE_UNIT[input.resource_type],
      metadata: { scope_type: input.scope_type, scope_id: input.scope_id },
    });

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const accountId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'treasury.account_opened',
        actor_id: input.actor_id,
        object_type: 'treasury_account',
        object_id: accountId,
        correlation_id: crypto.randomUUID(),
        payload: { scope_type: input.scope_type, scope_id: input.scope_id, resource_type: input.resource_type },
      });
      const inserted = await client.query<TreasuryAccountRecord>(
        `INSERT INTO treasury_accounts
           (id, civilization_id, scope_type, scope_id, resource_type, resource_account_id, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
         ON CONFLICT (scope_type, scope_id, resource_type) DO UPDATE SET updated_at = now()
         RETURNING id, civilization_id, scope_type, scope_id, resource_type, resource_account_id, status`,
        [accountId, civilizationId, input.scope_type, input.scope_id, input.resource_type,
         resourceAccount.id, input.actor_id, event.id]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getAccount(scopeType: ScopeType, scopeId: string, resourceType: EconomyResource): Promise<TreasuryAccountRecord | null> {
    const result = await db.query<TreasuryAccountRecord>(
      `SELECT id, civilization_id, scope_type, scope_id, resource_type, resource_account_id, status
         FROM treasury_accounts WHERE scope_type = $1 AND scope_id = $2 AND resource_type = $3 LIMIT 1`,
      [scopeType, scopeId, resourceType]
    );
    return result.rows[0] ?? null;
  }

  async balance(scopeType: ScopeType, scopeId: string, resourceType: EconomyResource): Promise<{ balance: number; reserved: number } | null> {
    const account = await this.getAccount(scopeType, scopeId, resourceType);
    if (!account) return null;
    const ledgerAccount = await resourceLedger.getAccount(account.resource_account_id);
    if (!ledgerAccount) return null;
    return { balance: Number(ledgerAccount.balance), reserved: Number((ledgerAccount as any).reserved_balance ?? 0) };
  }

  /** Fund a treasury account (mints resource into the scope's account). */
  async fund(input: {
    scope_type: ScopeType; scope_id: string; resource_type: EconomyResource; amount: number;
    reason: string; actor_id: string; idempotency_key?: string;
  }): Promise<{ balance: number }> {
    const account = await this.openAccount({
      scope_type: input.scope_type, scope_id: input.scope_id, resource_type: input.resource_type, actor_id: input.actor_id,
    });
    await resourceLedger.credit({
      account_id: account.resource_account_id,
      actor_id: input.actor_id,
      amount: input.amount,
      reason: input.reason,
      idempotency_key: input.idempotency_key ?? crypto.randomUUID(),
    });
    const balance = await this.balance(input.scope_type, input.scope_id, input.resource_type);
    return { balance: balance!.balance };
  }

  // -------------------------------------------------------------------------
  // Resource policies (risk/trust linked)
  // -------------------------------------------------------------------------

  async setPolicy(input: {
    policy_key: string; resource_type: EconomyResource; max_risk_level?: RiskLevel;
    min_trust_factor?: number; per_request_cap?: number; requires_review_above?: number; actor_id: string;
    civilization_id?: string;
  }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.rootId());
      await client.query(
        `UPDATE resource_policies SET status = 'revoked', revoked_at = now(), revoked_by_actor_id = $3
          WHERE civilization_id = $1 AND policy_key = $2 AND status = 'active'`,
        [civilizationId, input.policy_key, input.actor_id]
      );
      const policyId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'treasury.policy_set',
        actor_id: input.actor_id,
        object_type: 'resource_policy',
        object_id: policyId,
        correlation_id: crypto.randomUUID(),
        payload: { policy_key: input.policy_key, resource_type: input.resource_type },
      });
      await client.query(
        `INSERT INTO resource_policies
           (id, civilization_id, policy_key, resource_type, max_risk_level, min_trust_factor,
            per_request_cap, requires_review_above, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
        [policyId, civilizationId, input.policy_key, input.resource_type,
         input.max_risk_level ?? 'critical', input.min_trust_factor ?? 0,
         input.per_request_cap ?? null, input.requires_review_above ?? null, input.actor_id, event.id]
      );
      await client.query('COMMIT');
      return { id: policyId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Decide whether a resource request is allowed under active policy, given
   * the requester's risk level and (actor, domain) trust. Returns a decision;
   * exhaustion or policy breach yields block/queue/review rather than silent
   * failure.
   */
  async evaluateRequest(input: {
    scope_type: ScopeType; scope_id: string; resource_type: EconomyResource; amount: number;
    policy_key?: string; risk_level?: RiskLevel; trust_factor?: number;
  }): Promise<{ decision: 'allow' | 'block' | 'queue' | 'requires_review'; reason: string }> {
    if (input.amount <= 0) return { decision: 'block', reason: 'amount must be positive' };
    const balance = await this.balance(input.scope_type, input.scope_id, input.resource_type);
    if (!balance) return { decision: 'block', reason: 'no treasury account for scope' };
    const available = balance.balance - balance.reserved;
    if (available < input.amount) {
      return { decision: 'queue', reason: `insufficient available balance (${available} < ${input.amount})` };
    }
    if (input.policy_key) {
      const policy = await db.query<{
        max_risk_level: RiskLevel; min_trust_factor: string; per_request_cap: string | null; requires_review_above: string | null;
      }>(
        `SELECT max_risk_level, min_trust_factor, per_request_cap, requires_review_above
           FROM resource_policies WHERE policy_key = $1 AND status = 'active' LIMIT 1`,
        [input.policy_key]
      );
      if ((policy.rowCount ?? 0) === 1) {
        const p = policy.rows[0];
        const risk = input.risk_level ?? 'low';
        if (RISK_RANK[risk] > RISK_RANK[p.max_risk_level]) {
          return { decision: 'block', reason: `risk ${risk} exceeds policy max ${p.max_risk_level}` };
        }
        if ((input.trust_factor ?? 1) < Number(p.min_trust_factor)) {
          return { decision: 'block', reason: `trust ${input.trust_factor ?? 1} below policy min ${p.min_trust_factor}` };
        }
        if (p.per_request_cap !== null && input.amount > Number(p.per_request_cap)) {
          return { decision: 'block', reason: `amount exceeds per-request cap ${p.per_request_cap}` };
        }
        if (p.requires_review_above !== null && input.amount > Number(p.requires_review_above)) {
          return { decision: 'requires_review', reason: `amount exceeds review threshold ${p.requires_review_above}` };
        }
      }
    }
    return { decision: 'allow', reason: 'within balance and policy' };
  }

  // -------------------------------------------------------------------------
  // Budget proposals and allocations
  // -------------------------------------------------------------------------

  async proposeBudget(input: {
    from_scope: { type: ScopeType; id: string };
    to_scope: { type: ScopeType; id: string };
    resource_type: EconomyResource; amount: number; justification?: string; actor_id: string;
  }): Promise<{ id: string; status: string }> {
    if (input.amount <= 0) throw new PublicHttpError(400, 'amount must be positive');
    const from = await this.openAccount({
      scope_type: input.from_scope.type, scope_id: input.from_scope.id,
      resource_type: input.resource_type, actor_id: input.actor_id,
    });
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const proposalId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'treasury.budget_proposed',
        actor_id: input.actor_id,
        object_type: 'budget_proposal',
        object_id: proposalId,
        correlation_id: crypto.randomUUID(),
        payload: { from_scope: input.from_scope, to_scope: input.to_scope, amount: input.amount },
      });
      const inserted = await client.query<{ id: string; status: string }>(
        `INSERT INTO budget_proposals
           (id, civilization_id, from_treasury_account_id, to_scope_type, to_scope_id, resource_type, amount, justification, proposed_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
         RETURNING id, status`,
        [proposalId, from.civilization_id, from.id, input.to_scope.type, input.to_scope.id,
         input.resource_type, input.amount, input.justification ?? '', input.actor_id, event.id]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async decideBudget(input: { proposal_id: string; approve: boolean; actor_id: string }): Promise<{ status: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const proposal = await client.query<{ status: string; proposed_by_actor_id: string }>(
        `SELECT status, proposed_by_actor_id FROM budget_proposals WHERE id = $1 FOR UPDATE`,
        [input.proposal_id]
      );
      if ((proposal.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'proposal not found');
      if (proposal.rows[0].status !== 'proposed') throw new PublicHttpError(409, `proposal is ${proposal.rows[0].status}`);
      if (proposal.rows[0].proposed_by_actor_id === input.actor_id) {
        throw new PublicHttpError(409, 'a budget proposal cannot be approved by its own proposer');
      }
      const status = input.approve ? 'approved' : 'rejected';
      const event = await eventLog.appendWithClient(client, {
        event_type: `treasury.budget_${status}`,
        actor_id: input.actor_id,
        object_type: 'budget_proposal',
        object_id: input.proposal_id,
        correlation_id: crypto.randomUUID(),
        payload: { proposal_id: input.proposal_id },
      });
      await client.query(
        `UPDATE budget_proposals SET status = $2, decided_by_actor_id = $3, decided_at = now() WHERE id = $1`,
        [input.proposal_id, status, input.actor_id]
      );
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `budget proposal ${input.proposal_id} ${status}`,
        output_summary: `proposal is now ${status}`,
        confidence_score: 1, risk_level: 'medium', human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return { status };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** Execute an approved budget: two-phase transfer via the resource ledger. Idempotent per proposal. */
  async allocateBudget(input: { proposal_id: string; actor_id: string }): Promise<{ allocation_id: string }> {
    const proposal = await db.query<{
      civilization_id: string; from_treasury_account_id: string; to_scope_type: ScopeType;
      to_scope_id: string; resource_type: EconomyResource; amount: string; status: string;
    }>(
      `SELECT civilization_id, from_treasury_account_id, to_scope_type, to_scope_id, resource_type, amount, status
         FROM budget_proposals WHERE id = $1`,
      [input.proposal_id]
    );
    if ((proposal.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'proposal not found');
    const p = proposal.rows[0];
    if (p.status === 'allocated') {
      const existing = await db.query<{ id: string }>(`SELECT id FROM budget_allocations WHERE budget_proposal_id = $1`, [input.proposal_id]);
      return { allocation_id: existing.rows[0].id };
    }
    if (p.status !== 'approved') throw new PublicHttpError(409, `proposal must be approved to allocate (is ${p.status})`);

    const from = await db.query<{ resource_account_id: string }>(`SELECT resource_account_id FROM treasury_accounts WHERE id = $1`, [p.from_treasury_account_id]);
    const to = await this.openAccount({ scope_type: p.to_scope_type, scope_id: p.to_scope_id, resource_type: p.resource_type, actor_id: input.actor_id });
    const amount = Number(p.amount);

    // Idempotency keyed on the proposal so a re-run cannot double-transfer.
    const debit = await resourceLedger.debit({
      account_id: from.rows[0].resource_account_id,
      actor_id: input.actor_id, amount, reason: `budget allocation ${input.proposal_id}`,
      idempotency_key: `budget-debit-${input.proposal_id}`,
    });
    const credit = await resourceLedger.credit({
      account_id: to.resource_account_id,
      actor_id: input.actor_id, amount, reason: `budget allocation ${input.proposal_id}`,
      idempotency_key: `budget-credit-${input.proposal_id}`,
    });

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const allocationId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'treasury.budget_allocated',
        actor_id: input.actor_id,
        object_type: 'budget_allocation',
        object_id: allocationId,
        correlation_id: crypto.randomUUID(),
        payload: { proposal_id: input.proposal_id, amount },
      });
      await client.query(
        `INSERT INTO budget_allocations
           (id, budget_proposal_id, from_treasury_account_id, to_treasury_account_id, resource_type, amount,
            debit_transaction_id, credit_transaction_id, allocated_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
         ON CONFLICT (budget_proposal_id) DO NOTHING`,
        [allocationId, input.proposal_id, p.from_treasury_account_id, to.id, p.resource_type, amount,
         debit.id, credit.id, input.actor_id, event.id]
      );
      await client.query(`UPDATE budget_proposals SET status = 'allocated' WHERE id = $1`, [input.proposal_id]);
      await client.query('COMMIT');
      return { allocation_id: allocationId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // -------------------------------------------------------------------------
  // Penalties (governance/judiciary authority required)
  // -------------------------------------------------------------------------

  async imposePenalty(input: {
    target_scope: { type: ScopeType; id: string }; resource_type: EconomyResource; amount: number;
    reason: string; authorized_decision_ref: string; authority: 'governance' | 'judiciary'; actor_id: string;
    civilization_id?: string;
  }): Promise<{ id: string; applied: boolean }> {
    if (input.amount <= 0) throw new PublicHttpError(400, 'amount must be positive');
    if (!input.authorized_decision_ref || input.authorized_decision_ref.trim().length === 0) {
      throw new PublicHttpError(400, 'penalties require an authorized decision reference');
    }
    const account = await this.getAccount(input.target_scope.type, input.target_scope.id, input.resource_type);
    const civilizationId = input.civilization_id ?? (await this.rootId());

    // Apply as a debit when the target has an account with sufficient balance.
    let transactionId: string | null = null;
    let applied = false;
    if (account) {
      const ledgerAccount = await resourceLedger.getAccount(account.resource_account_id);
      if (ledgerAccount && Number(ledgerAccount.balance) >= input.amount) {
        const penaltyKey = crypto.randomUUID();
        const tx = await resourceLedger.debit({
          account_id: account.resource_account_id, actor_id: input.actor_id, amount: input.amount,
          reason: `penalty: ${input.reason}`, idempotency_key: `penalty-${penaltyKey}`,
        });
        transactionId = tx.id;
        applied = true;
      }
    }

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const penaltyId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'treasury.penalty_imposed',
        actor_id: input.actor_id,
        object_type: 'penalty',
        object_id: penaltyId,
        correlation_id: crypto.randomUUID(),
        payload: {
          target_scope: input.target_scope, amount: input.amount,
          authority: input.authority, authorized_decision_ref: input.authorized_decision_ref, applied,
        },
      });
      await client.query(
        `INSERT INTO penalties
           (id, civilization_id, target_scope_type, target_scope_id, treasury_account_id, resource_type, amount,
            reason, authorized_decision_ref, authority, status, transaction_id, imposed_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)`,
        [penaltyId, civilizationId, input.target_scope.type, input.target_scope.id, account?.id ?? null,
         input.resource_type, input.amount, input.reason, input.authorized_decision_ref, input.authority,
         applied ? 'applied' : 'imposed', transactionId, input.actor_id, event.id]
      );
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `impose ${input.authority} penalty on ${input.target_scope.type}:${input.target_scope.id}: ${input.reason}`,
        output_summary: `penalty ${penaltyId} ${applied ? 'applied' : 'imposed'} (authority ${input.authorized_decision_ref})`,
        confidence_score: 1, risk_level: 'high', human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return { id: penaltyId, applied };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // -------------------------------------------------------------------------
  // Cost attribution and reconciliation
  // -------------------------------------------------------------------------

  async recordCost(input: {
    resource_type: EconomyResource; amount: number; reason?: string; actor_id: string;
    mission_id?: string; institution_id?: string; citizen_id?: string; domain?: string; civilization_id?: string;
  }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.rootId());
      const recordId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'treasury.cost_attributed',
        actor_id: input.actor_id,
        object_type: 'cost_attribution_record',
        object_id: recordId,
        correlation_id: crypto.randomUUID(),
        payload: { resource_type: input.resource_type, amount: input.amount, mission_id: input.mission_id ?? null },
      });
      await client.query(
        `INSERT INTO cost_attribution_records
           (id, civilization_id, mission_id, institution_id, citizen_id, domain, resource_type, amount, reason, recorded_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)`,
        [recordId, civilizationId, input.mission_id ?? null, input.institution_id ?? null, input.citizen_id ?? null,
         input.domain ?? null, input.resource_type, input.amount, input.reason ?? '', input.actor_id, event.id]
      );
      await client.query('COMMIT');
      return { id: recordId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async costRollup(dimension: 'mission' | 'institution' | 'domain', resourceType?: EconomyResource): Promise<Array<{ key: string; total: number }>> {
    const column = dimension === 'mission' ? 'mission_id' : dimension === 'institution' ? 'institution_id' : 'domain';
    const result = await db.query<{ key: string; total: string }>(
      `SELECT ${column}::text AS key, SUM(amount) AS total
         FROM cost_attribution_records
        WHERE ${column} IS NOT NULL AND ($1::text IS NULL OR resource_type = $1)
        GROUP BY ${column} ORDER BY total DESC`,
      [resourceType ?? null]
    );
    return result.rows.map(r => ({ key: r.key, total: Number(r.total) }));
  }

  /**
   * Reconcile: the total balance across all treasury-scoped resource accounts
   * for a resource type must equal net funded minus net debited. Detects
   * ledger imbalance (which should never happen if allocations are atomic).
   */
  async reconcile(input: { resource_type: EconomyResource; actor_id: string; civilization_id?: string }): Promise<{
    balanced: boolean; computed_balance: number; ledger_balance: number; imbalance: number;
  }> {
    const civilizationId = input.civilization_id ?? (await this.rootId());
    const accounts = await db.query<{ resource_account_id: string }>(
      `SELECT resource_account_id FROM treasury_accounts WHERE resource_type = $1`, [input.resource_type]
    );
    let ledgerBalance = 0;
    for (const a of accounts.rows) {
      const acc = await resourceLedger.getAccount(a.resource_account_id);
      if (acc) ledgerBalance += Number(acc.balance);
    }
    // Computed balance recomputes each account's balance from its signed
    // transaction history (credit +, debit -, adjustment +) — the ledger's own
    // convention stores positive amounts with direction in transaction_type.
    const computed = await db.query<{ total: string }>(
      `SELECT COALESCE(SUM(
                CASE t.transaction_type WHEN 'debit' THEN -t.amount ELSE t.amount END
              ),0) AS total
         FROM civilization_resource_transactions t
         JOIN treasury_accounts ta ON ta.resource_account_id = t.account_id
        WHERE ta.resource_type = $1`,
      [input.resource_type]
    );
    const computedBalance = Number(computed.rows[0].total);
    const imbalance = Number((ledgerBalance - computedBalance).toFixed(6));
    const balanced = Math.abs(imbalance) < 1e-6;

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const runId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'treasury.reconciled',
        actor_id: input.actor_id,
        object_type: 'reconciliation_run',
        object_id: runId,
        correlation_id: crypto.randomUUID(),
        payload: { resource_type: input.resource_type, balanced, imbalance },
      });
      await client.query(
        `INSERT INTO reconciliation_runs
           (id, civilization_id, resource_type, computed_balance, ledger_balance, imbalance, balanced, run_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)`,
        [runId, civilizationId, input.resource_type, computedBalance, ledgerBalance, imbalance, balanced, input.actor_id, event.id]
      );
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
    return { balanced, computed_balance: computedBalance, ledger_balance: ledgerBalance, imbalance };
  }

  // -------------------------------------------------------------------------

  private async rootId(): Promise<string> {
    const root = await civilizationKernel.ensureCivilizationRoot();
    return root.id;
  }

  private async scopeActor(scopeType: ScopeType, scopeId: string): Promise<string> {
    const name = `treasury-scope:${scopeType}:${scopeId}`;
    const result = await db.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ role: 'treasury_scope', scope_type: scopeType, scope_id: scopeId })]
    );
    await db.query(
      `INSERT INTO service_identities (actor_id, service_name, scopes)
       VALUES ($1,$2,$3::jsonb) ON CONFLICT (actor_id) DO NOTHING`,
      [result.rows[0].id, name, JSON.stringify(['treasury.scope'])]
    );
    return result.rows[0].id;
  }
}

export const treasuryService = new TreasuryService();
