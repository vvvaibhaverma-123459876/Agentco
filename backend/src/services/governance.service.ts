import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { killSwitchService } from './kill-switch.service';
import { PublicHttpError } from '../http-errors';

/**
 * Governance and constitution (build phase C7).
 *
 * Proposal lifecycle: draft -> sponsored -> impact_review -> deliberation ->
 * voting -> approved|rejected -> activation_pending -> active ->
 * superseded|repealed|rolled_back. Approved `policy_change` proposals activate
 * a runtime_policy that the protected-action path consults, so activation
 * changes real behaviour and rollback restores it. Constitutional proposals
 * cannot alter tier-0 invariants and require a supermajority/unanimous rule.
 */

export type ProposalStatus =
  | 'draft' | 'sponsored' | 'impact_review' | 'deliberation' | 'voting'
  | 'approved' | 'rejected' | 'activation_pending' | 'active'
  | 'superseded' | 'repealed' | 'rolled_back';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
const RISK_RANK: Record<RiskLevel, number> = { low: 0, medium: 1, high: 2, critical: 3 };

const PROPOSAL_TRANSITIONS: Record<ProposalStatus, ProposalStatus[]> = {
  draft: ['sponsored'],
  sponsored: ['impact_review', 'rejected'],
  impact_review: ['deliberation', 'rejected'],
  deliberation: ['voting', 'rejected'],
  voting: ['approved', 'rejected'],
  approved: ['activation_pending', 'repealed'],
  rejected: [],
  activation_pending: ['active', 'repealed'],
  active: ['superseded', 'repealed', 'rolled_back'],
  superseded: [],
  repealed: [],
  rolled_back: [],
};

const TIER0_INVARIANT_KEYS = new Set([
  'only_reality_promotes', 'immutable_prediction_ledger', 'pre_registration_enforced',
  'reality_simulation_firewall', 'trusted_confidence_only', 'human_approval_gates',
  'immutable_audit_log', 'no_self_resolution', 'no_self_approval', 'external_ground_truth_only',
]);

const PROPOSAL_COLUMNS =
  'id, civilization_id, title, proposal_type, is_constitutional, body_json, status, quorum_rule, min_votes, proposed_by_actor_id, created_at, updated_at';

export interface ProposalRecord {
  id: string; civilization_id: string; title: string; proposal_type: string;
  is_constitutional: boolean; status: ProposalStatus; quorum_rule: string; min_votes: number;
  proposed_by_actor_id: string; body_json: Record<string, unknown>;
}

export class GovernanceService {
  // -------------------------------------------------------------------------
  // Proposal lifecycle
  // -------------------------------------------------------------------------

  async createProposal(input: {
    title: string;
    proposal_type: 'policy_change' | 'role_grant' | 'institution_power_change' | 'constitution_change' | 'budget_policy_change' | 'domain_onboarding' | 'general';
    body?: Record<string, unknown>;
    quorum_rule?: 'simple_majority' | 'supermajority' | 'unanimous';
    min_votes?: number;
    actor_id: string;
    civilization_id?: string;
  }): Promise<ProposalRecord> {
    if (!input.title || input.title.trim().length === 0) throw new PublicHttpError(400, 'title is required');
    const isConstitutional = input.proposal_type === 'constitution_change';

    // Tier-0 invariants cannot be changed by ordinary proposals.
    if (isConstitutional) {
      const target = (input.body?.invariant_key as string) ?? '';
      if (TIER0_INVARIANT_KEYS.has(target)) {
        throw new PublicHttpError(409, `tier-0 invariant '${target}' cannot be changed through a governance proposal`);
      }
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.rootId());
      const proposalId = crypto.randomUUID();
      // Constitutional changes require an elevated procedure.
      const quorumRule = isConstitutional ? (input.quorum_rule === 'unanimous' ? 'unanimous' : 'supermajority') : (input.quorum_rule ?? 'simple_majority');
      const minVotes = Math.max(input.min_votes ?? 1, isConstitutional ? 3 : 1);
      const event = await eventLog.appendWithClient(client, {
        event_type: 'governance.proposal_created',
        actor_id: input.actor_id,
        object_type: 'governance_proposal',
        object_id: proposalId,
        correlation_id: crypto.randomUUID(),
        payload: { title: input.title.trim(), proposal_type: input.proposal_type, is_constitutional: isConstitutional },
      });
      const inserted = await client.query<ProposalRecord>(
        `INSERT INTO governance_proposals
           (id, civilization_id, title, proposal_type, is_constitutional, body_json, quorum_rule, min_votes, proposed_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10)
         RETURNING ${PROPOSAL_COLUMNS}`,
        [proposalId, civilizationId, input.title.trim(), input.proposal_type, isConstitutional,
         JSON.stringify(input.body ?? {}), quorumRule, minVotes, input.actor_id, event.id]
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

  async sponsor(input: { proposal_id: string; sponsor_actor_id: string }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const proposal = await this.lockProposal(client, input.proposal_id);
      if (proposal.proposed_by_actor_id === input.sponsor_actor_id) {
        throw new PublicHttpError(409, 'a proposal cannot be sponsored by its own author (separation of duties)');
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: 'governance.proposal_sponsored',
        actor_id: input.sponsor_actor_id,
        object_type: 'governance_proposal',
        object_id: input.proposal_id,
        correlation_id: crypto.randomUUID(),
        payload: { sponsor: input.sponsor_actor_id },
      });
      await client.query(
        `INSERT INTO proposal_sponsors (proposal_id, sponsor_actor_id, event_log_id)
         VALUES ($1,$2,$3) ON CONFLICT DO NOTHING`,
        [input.proposal_id, input.sponsor_actor_id, event.id]
      );
      if (proposal.status === 'draft') {
        await this.setStatus(client, input.proposal_id, 'sponsored', input.sponsor_actor_id, 'sponsored');
      }
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async recordImpactAssessment(input: {
    proposal_id: string; assessor_actor_id: string; risk_level: RiskLevel; summary: string; detail?: Record<string, unknown>;
  }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const proposal = await this.lockProposal(client, input.proposal_id);
      if (proposal.status !== 'sponsored' && proposal.status !== 'impact_review') {
        throw new PublicHttpError(409, `impact assessment requires a sponsored proposal (is ${proposal.status})`);
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: 'governance.impact_assessed',
        actor_id: input.assessor_actor_id,
        object_type: 'impact_assessment',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { proposal_id: input.proposal_id, risk_level: input.risk_level },
      });
      await client.query(
        `INSERT INTO impact_assessments (proposal_id, assessor_actor_id, risk_level, summary, detail_json, event_log_id)
         VALUES ($1,$2,$3,$4,$5::jsonb,$6) ON CONFLICT (proposal_id) DO NOTHING`,
        [input.proposal_id, input.assessor_actor_id, input.risk_level, input.summary, JSON.stringify(input.detail ?? {}), event.id]
      );
      if (proposal.status === 'sponsored') {
        await this.setStatus(client, input.proposal_id, 'impact_review', input.assessor_actor_id, 'impact assessed');
      }
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async openDeliberation(proposalId: string, actorId: string): Promise<void> {
    await this.simpleAdvance(proposalId, 'impact_review', 'deliberation', actorId, 'deliberation opened');
  }

  async recordDeliberation(input: {
    proposal_id: string; actor_id: string; position: 'support' | 'oppose' | 'neutral'; argument: string;
  }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const proposal = await this.lockProposal(client, input.proposal_id);
      if (proposal.status !== 'deliberation') throw new PublicHttpError(409, 'proposal is not in deliberation');
      const event = await eventLog.appendWithClient(client, {
        event_type: 'governance.deliberation_recorded',
        actor_id: input.actor_id,
        object_type: 'deliberation',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { proposal_id: input.proposal_id, position: input.position },
      });
      await client.query(
        `INSERT INTO deliberations (proposal_id, actor_id, position, argument, event_log_id)
         VALUES ($1,$2,$3,$4,$5)`,
        [input.proposal_id, input.actor_id, input.position, input.argument, event.id]
      );
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async openVoting(proposalId: string, actorId: string): Promise<void> {
    await this.simpleAdvance(proposalId, 'deliberation', 'voting', actorId, 'voting opened');
  }

  async castVote(input: {
    proposal_id: string; voter_actor_id: string; vote: 'yes' | 'no' | 'abstain'; weight?: number;
  }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const proposal = await this.lockProposal(client, input.proposal_id);
      if (proposal.status !== 'voting') throw new PublicHttpError(409, 'proposal is not open for voting');
      // Conflict of interest: the proposal author cannot vote on their own proposal.
      if (proposal.proposed_by_actor_id === input.voter_actor_id) {
        throw new PublicHttpError(409, 'the proposal author cannot vote on their own proposal');
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: 'governance.vote_cast',
        actor_id: input.voter_actor_id,
        object_type: 'governance_vote',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { proposal_id: input.proposal_id, vote: input.vote },
      });
      await client.query(
        `INSERT INTO governance_votes (proposal_id, voter_actor_id, vote, weight, event_log_id)
         VALUES ($1,$2,$3,$4,$5)
         ON CONFLICT (proposal_id, voter_actor_id) DO NOTHING`,
        [input.proposal_id, input.voter_actor_id, input.vote, Math.min(10, Math.max(0.01, input.weight ?? 1)), event.id]
      );
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** Tally votes against the quorum rule and record the decision. */
  async closeVoting(input: { proposal_id: string; actor_id: string }): Promise<{ outcome: 'approved' | 'rejected'; tally: Record<string, number> }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const proposal = await this.lockProposal(client, input.proposal_id);
      if (proposal.status !== 'voting') throw new PublicHttpError(409, 'proposal is not open for voting');
      const votes = await client.query<{ vote: string; weight: string }>(
        `SELECT vote, weight FROM governance_votes WHERE proposal_id = $1`, [input.proposal_id]
      );
      let yes = 0, no = 0, abstain = 0, yesWeight = 0, noWeight = 0;
      for (const v of votes.rows) {
        const w = Number(v.weight);
        if (v.vote === 'yes') { yes++; yesWeight += w; }
        else if (v.vote === 'no') { no++; noWeight += w; }
        else abstain++;
      }
      const cast = yes + no;
      let outcome: 'approved' | 'rejected';
      if (cast < proposal.min_votes) {
        outcome = 'rejected';
      } else if (proposal.quorum_rule === 'unanimous') {
        outcome = no === 0 && yes >= proposal.min_votes ? 'approved' : 'rejected';
      } else if (proposal.quorum_rule === 'supermajority') {
        outcome = yesWeight >= (yesWeight + noWeight) * (2 / 3) && yes >= proposal.min_votes ? 'approved' : 'rejected';
      } else {
        outcome = yesWeight > noWeight ? 'approved' : 'rejected';
      }
      const tally = { yes, no, abstain, yes_weight: yesWeight, no_weight: noWeight };
      const event = await eventLog.appendWithClient(client, {
        event_type: `governance.proposal_${outcome}`,
        actor_id: input.actor_id,
        object_type: 'governance_decision',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { proposal_id: input.proposal_id, outcome, tally },
      });
      await client.query(
        `INSERT INTO governance_decisions (proposal_id, outcome, tally_json, decided_by_actor_id, event_log_id)
         VALUES ($1,$2,$3::jsonb,$4,$5) ON CONFLICT (proposal_id) DO NOTHING`,
        [input.proposal_id, outcome, JSON.stringify(tally), input.actor_id, event.id]
      );
      await this.setStatus(client, input.proposal_id, outcome, input.actor_id, `voting closed: ${outcome}`);
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `close voting on proposal ${input.proposal_id}`,
        output_summary: `proposal ${outcome} (yes=${yes} no=${no} rule=${proposal.quorum_rule})`,
        confidence_score: 1, risk_level: 'high', human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return { outcome, tally };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Activate an approved proposal. For `policy_change` proposals this creates
   * a runtime_policy that the protected-action path consults, so behaviour
   * changes immediately. Returns the runtime policy id when one was created.
   */
  async activateProposal(input: { proposal_id: string; actor_id: string }): Promise<{ runtime_policy_id: string | null }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const proposal = await this.lockProposal(client, input.proposal_id);
      if (proposal.status !== 'approved' && proposal.status !== 'activation_pending') {
        throw new PublicHttpError(409, `proposal must be approved to activate (is ${proposal.status})`);
      }
      if (proposal.status === 'approved') {
        await this.setStatus(client, input.proposal_id, 'activation_pending', input.actor_id, 'activation pending');
      }
      let runtimePolicyId: string | null = null;
      if (proposal.proposal_type === 'policy_change' || proposal.proposal_type === 'budget_policy_change') {
        runtimePolicyId = await this.createRuntimePolicyWithClient(client, proposal, input.actor_id);
      }
      await this.setStatus(client, input.proposal_id, 'active', input.actor_id, 'proposal activated');
      await client.query('COMMIT');
      return { runtime_policy_id: runtimePolicyId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async createRuntimePolicyWithClient(client: PoolClient, proposal: ProposalRecord, actorId: string): Promise<string> {
    const body = proposal.body_json ?? {};
    const policyKey = (body.policy_key as string) ?? `policy-${proposal.id.slice(0, 8)}`;
    const effect = (body.effect as string) ?? 'block';
    if (!['block', 'require_review', 'allow'].includes(effect)) {
      throw new PublicHttpError(400, 'policy body.effect must be block, require_review, or allow');
    }
    // Supersede any existing active policy with the same key.
    await client.query(
      `UPDATE runtime_policies SET status = 'superseded'
        WHERE civilization_id = $1 AND policy_key = $2 AND status = 'active'`,
      [proposal.civilization_id, policyKey]
    );
    const policyId = crypto.randomUUID();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'governance.policy_activated',
      actor_id: actorId,
      object_type: 'runtime_policy',
      object_id: policyId,
      correlation_id: crypto.randomUUID(),
      payload: { proposal_id: proposal.id, policy_key: policyKey, effect },
    });
    await client.query(
      `INSERT INTO runtime_policies
         (id, civilization_id, proposal_id, policy_key, effect, match_action_type, match_domain, match_min_risk, description, activated_by_actor_id, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)`,
      [policyId, proposal.civilization_id, proposal.id, policyKey, effect,
       (body.match_action_type as string) ?? null, (body.match_domain as string) ?? null,
       (body.match_min_risk as string) ?? null, (body.description as string) ?? proposal.title, actorId, event.id]
    );
    await client.query(
      `INSERT INTO policy_activations (runtime_policy_id, proposal_id, action, actor_id, event_log_id)
       VALUES ($1,$2,'activated',$3,$4)`,
      [policyId, proposal.id, actorId, event.id]
    );
    return policyId;
  }

  /** Roll back an active policy (and its proposal), restoring prior behaviour. */
  async rollbackPolicy(input: { runtime_policy_id: string; actor_id: string; reason: string }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const policy = await client.query<{ id: string; proposal_id: string | null; status: string }>(
        `SELECT id, proposal_id, status FROM runtime_policies WHERE id = $1 FOR UPDATE`,
        [input.runtime_policy_id]
      );
      if ((policy.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'runtime policy not found');
      if (policy.rows[0].status !== 'active') throw new PublicHttpError(409, `policy is ${policy.rows[0].status}`);
      const event = await eventLog.appendWithClient(client, {
        event_type: 'governance.policy_rolled_back',
        actor_id: input.actor_id,
        object_type: 'runtime_policy',
        object_id: input.runtime_policy_id,
        correlation_id: crypto.randomUUID(),
        payload: { reason: input.reason },
      });
      await client.query(
        `UPDATE runtime_policies SET status = 'rolled_back', rolled_back_at = now(), rolled_back_by_actor_id = $2 WHERE id = $1`,
        [input.runtime_policy_id, input.actor_id]
      );
      await client.query(
        `INSERT INTO policy_activations (runtime_policy_id, proposal_id, action, actor_id, event_log_id)
         VALUES ($1,$2,'rolled_back',$3,$4)`,
        [input.runtime_policy_id, policy.rows[0].proposal_id, input.actor_id, event.id]
      );
      if (policy.rows[0].proposal_id) {
        await this.setStatus(client, policy.rows[0].proposal_id, 'rolled_back', input.actor_id, `policy rolled back: ${input.reason}`);
      }
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `rollback runtime policy ${input.runtime_policy_id}: ${input.reason}`,
        output_summary: 'policy rolled back; prior behaviour restored',
        confidence_score: 1, risk_level: 'high', human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // -------------------------------------------------------------------------
  // Emergency powers (integrate kill switch, auto-expiring)
  // -------------------------------------------------------------------------

  async grantEmergencyPower(input: {
    scope: string; power: string; reason: string; authorized_decision_ref: string;
    ttl_seconds: number; engage_kill_switch?: boolean; actor_id: string; civilization_id?: string;
  }): Promise<{ id: string; kill_switch_engaged: boolean }> {
    if (!input.authorized_decision_ref) throw new PublicHttpError(400, 'authorized_decision_ref is required');
    if (!Number.isFinite(input.ttl_seconds) || input.ttl_seconds <= 0 || input.ttl_seconds > 7 * 24 * 3600) {
      throw new PublicHttpError(400, 'ttl_seconds must be between 1 and 604800');
    }
    const civilizationId = input.civilization_id ?? (await this.rootId());
    let killSwitchEngaged = false;
    let killScope: string | null = null;
    if (input.engage_kill_switch) {
      killScope = `emergency:${input.scope}`;
      await killSwitchService.activate(killScope, input.actor_id, `emergency power: ${input.reason}`, { power: input.power });
      killSwitchEngaged = true;
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const powerId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'governance.emergency_power_granted',
        actor_id: input.actor_id,
        object_type: 'governance_emergency_power',
        object_id: powerId,
        correlation_id: crypto.randomUUID(),
        payload: { scope: input.scope, power: input.power, ttl_seconds: input.ttl_seconds, kill_switch: killSwitchEngaged },
      });
      await client.query(
        `INSERT INTO governance_emergency_powers
           (id, civilization_id, scope, power, reason, authorized_decision_ref, kill_switch_scope, activated_by_actor_id, expires_at, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8, now() + make_interval(secs => $9), $10)`,
        [powerId, civilizationId, input.scope, input.power, input.reason, input.authorized_decision_ref,
         killScope, input.actor_id, input.ttl_seconds, event.id]
      );
      await client.query('COMMIT');
      return { id: powerId, kill_switch_engaged: killSwitchEngaged };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** Expire due emergency powers and release their kill switches. */
  async expireEmergencyPowers(): Promise<{ expired: number }> {
    const due = await db.query<{ id: string; kill_switch_scope: string | null }>(
      `SELECT id, kill_switch_scope FROM governance_emergency_powers WHERE status = 'active' AND expires_at <= now()`
    );
    let expired = 0;
    for (const row of due.rows) {
      const client = await db.connect();
      try {
        await client.query('BEGIN');
        const serviceActor = await this.serviceActor();
        if (row.kill_switch_scope) {
          const active = await killSwitchService.getActive(row.kill_switch_scope);
          if (active) await killSwitchService.deactivate(row.kill_switch_scope, serviceActor, 'emergency power expired');
        }
        const event = await eventLog.appendWithClient(client, {
          event_type: 'governance.emergency_power_expired',
          actor_id: serviceActor,
          object_type: 'governance_emergency_power',
          object_id: row.id,
          correlation_id: crypto.randomUUID(),
          payload: {},
        });
        await client.query(
          `UPDATE governance_emergency_powers SET status = 'expired', ended_at = now(), ended_by_actor_id = $2 WHERE id = $1`,
          [row.id, serviceActor]
        );
        void event;
        await client.query('COMMIT');
        expired++;
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      } finally {
        client.release();
      }
    }
    return { expired };
  }

  async getProposal(proposalId: string): Promise<ProposalRecord | null> {
    const result = await db.query<ProposalRecord>(`SELECT ${PROPOSAL_COLUMNS} FROM governance_proposals WHERE id = $1`, [proposalId]);
    return result.rows[0] ?? null;
  }

  // -------------------------------------------------------------------------

  private async simpleAdvance(proposalId: string, from: ProposalStatus, to: ProposalStatus, actorId: string, reason: string): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const proposal = await this.lockProposal(client, proposalId);
      if (proposal.status !== from) throw new PublicHttpError(409, `proposal must be ${from} (is ${proposal.status})`);
      await this.setStatus(client, proposalId, to, actorId, reason);
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async setStatus(client: PoolClient, proposalId: string, to: ProposalStatus, actorId: string, reason: string): Promise<void> {
    const current = await client.query<{ status: ProposalStatus }>(`SELECT status FROM governance_proposals WHERE id = $1`, [proposalId]);
    const from = current.rows[0].status;
    if (from !== to && !PROPOSAL_TRANSITIONS[from]?.includes(to)) {
      throw new PublicHttpError(409, `illegal proposal transition ${from} -> ${to}`);
    }
    const event = await eventLog.appendWithClient(client, {
      event_type: 'governance.proposal_status_changed',
      actor_id: actorId,
      object_type: 'governance_proposal',
      object_id: proposalId,
      correlation_id: crypto.randomUUID(),
      payload: { from_status: from, to_status: to, reason },
    });
    await client.query(`SELECT set_config('civilization.governance_transition_authorized', 'true', true)`);
    await client.query(`UPDATE governance_proposals SET status = $2 WHERE id = $1`, [proposalId, to]);
    await client.query(`SELECT set_config('civilization.governance_transition_authorized', 'false', true)`);
    void event;
  }

  private async lockProposal(client: PoolClient, proposalId: string): Promise<ProposalRecord> {
    const result = await client.query<ProposalRecord>(`SELECT ${PROPOSAL_COLUMNS} FROM governance_proposals WHERE id = $1 FOR UPDATE`, [proposalId]);
    if ((result.rowCount ?? 0) !== 1) throw new PublicHttpError(404, `proposal not found: ${proposalId}`);
    return result.rows[0];
  }

  private async rootId(): Promise<string> {
    const root = await civilizationKernel.ensureCivilizationRoot();
    return root.id;
  }

  private async serviceActor(): Promise<string> {
    const result = await db.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service','agentco-governance','{}'::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at RETURNING id`
    );
    return result.rows[0].id;
  }
}

export const governanceService = new GovernanceService();
