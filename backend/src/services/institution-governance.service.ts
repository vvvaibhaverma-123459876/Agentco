import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { institutionsService } from './institutions.service';
import { societyService } from './society.service';
import { civilizationKernel } from './civilization-kernel.service';
import { PublicHttpError } from '../http-errors';

/**
 * Institution governance completion (build phase C3): charters (append-only,
 * versioned), mandates/powers/limits (grant rows), inter-institution
 * contracts with lifecycle + settlement, and the mandatory civilization-level
 * institution seed.
 *
 * Separation of powers: an institution cannot grant itself new powers — the
 * granting actor must differ from the institution's own actor and must carry
 * an authorized decision reference.
 */

export const MANDATORY_INSTITUTIONS: Array<{
  name: string;
  domain: string;
  purpose: string;
  mandate: string;
  powers: string[];
  limits: string[];
}> = [
  { name: 'Evidence Court', domain: 'evidence_governance', purpose: 'Adjudicates evidence admissibility and memory promotion', mandate: 'Review evidence and gate memory promotion', powers: ['adjudicate_evidence', 'gate_memory_promotion'], limits: ['cannot_change_constitution', 'cannot_resolve_own_claims'] },
  { name: 'Calibration Office', domain: 'calibration', purpose: 'Owns calibration scoring and trust windows', mandate: 'Score resolved predictions and maintain trust', powers: ['issue_trust_windows'], limits: ['cannot_mutate_prediction_ledger'] },
  { name: 'Safety Council', domain: 'safety', purpose: 'Owns risk tiers, kill switches, and emergency review', mandate: 'Classify risk and control emergency powers', powers: ['activate_kill_switch', 'review_high_risk'], limits: ['cannot_execute_missions'] },
  { name: 'Memory Bureau', domain: 'memory', purpose: 'Operates promoted memory and retraction propagation', mandate: 'Curate promoted memory with provenance', powers: ['retract_memory'], limits: ['cannot_promote_unverified_memory'] },
  { name: 'Treasury', domain: 'economy', purpose: 'Owns resource accounts, budgets, and settlement', mandate: 'Allocate and reconcile civilization resources', powers: ['allocate_budgets', 'impose_budget_penalties'], limits: ['cannot_create_resources_from_nothing'] },
  { name: 'Evaluation Lab', domain: 'evaluation', purpose: 'Runs independent evaluations and benchmarks', mandate: 'Evaluate candidates independently of proposers', powers: ['run_evaluations', 'mint_competence_proofs'], limits: ['cannot_evaluate_own_proposals'] },
  { name: 'Judiciary', domain: 'justice', purpose: 'Resolves disputes, appeals, and enforcement', mandate: 'Rule on disputes and enforce rulings', powers: ['issue_rulings', 'issue_enforcement_orders'], limits: ['cannot_rule_on_own_disputes'] },
  { name: 'Expansion Board', domain: 'expansion', purpose: 'Owns domain onboarding and capability grants', mandate: 'Gate domain and capability expansion', powers: ['approve_domain_expansion', 'revoke_capabilities'], limits: ['cannot_bypass_competence_proofs'] },
  { name: 'Identity Registry', domain: 'identity', purpose: 'Owns actor identity, keys, and citizenship records', mandate: 'Register identities and maintain key lifecycle', powers: ['register_actors', 'rotate_keys'], limits: ['cannot_delete_identity_history'] },
  { name: 'Observability Office', domain: 'observability', purpose: 'Owns projections, SLOs, and operational visibility', mandate: 'Maintain projections and operational truth', powers: ['publish_projections'], limits: ['cannot_alter_source_events'] },
];

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`);
  return `{${entries.join(',')}}`;
}

export class InstitutionGovernanceService {
  // -------------------------------------------------------------------------
  // Charters
  // -------------------------------------------------------------------------

  async proposeCharter(input: {
    institution_id: string;
    charter: Record<string, unknown>;
    actor_id: string;
  }): Promise<{ id: string; version_number: number; status: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireInstitution(client, input.institution_id);
      const next = await client.query<{ next: number }>(
        `SELECT COALESCE(MAX(version_number), 0) + 1 AS next FROM institution_charters WHERE institution_id = $1`,
        [input.institution_id]
      );
      const charterId = crypto.randomUUID();
      const charterHash = crypto.createHash('sha256').update(stableStringify(input.charter)).digest('hex');
      const event = await eventLog.appendWithClient(client, {
        event_type: 'institution.charter_proposed',
        actor_id: input.actor_id,
        object_type: 'institution_charter',
        object_id: charterId,
        correlation_id: crypto.randomUUID(),
        payload: {
          institution_id: input.institution_id,
          version_number: Number(next.rows[0].next),
          charter_hash: charterHash,
        },
      });
      const inserted = await client.query<{ id: string; version_number: number; status: string }>(
        `INSERT INTO institution_charters
           (id, institution_id, version_number, charter_json, charter_hash, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7)
         RETURNING id, version_number, status`,
        [charterId, input.institution_id, Number(next.rows[0].next),
         JSON.stringify(input.charter), charterHash, input.actor_id, event.id]
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

  async activateCharter(charterId: string, actorId: string): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const charter = await client.query<{ id: string; institution_id: string; status: string; version_number: number }>(
        `SELECT id, institution_id, status, version_number FROM institution_charters WHERE id = $1 FOR UPDATE`,
        [charterId]
      );
      if ((charter.rowCount ?? 0) !== 1) throw new PublicHttpError(404, `charter not found: ${charterId}`);
      if (charter.rows[0].status !== 'draft') {
        throw new PublicHttpError(409, `charter ${charterId} is ${charter.rows[0].status}, not draft`);
      }
      await client.query(
        `UPDATE institution_charters SET status = 'superseded'
          WHERE institution_id = $1 AND status = 'active'`,
        [charter.rows[0].institution_id]
      );
      await client.query(
        `UPDATE institution_charters
            SET status = 'active', activated_at = now(), activated_by_actor_id = $2
          WHERE id = $1`,
        [charterId, actorId]
      );
      const event = await eventLog.appendWithClient(client, {
        event_type: 'institution.charter_activated',
        actor_id: actorId,
        object_type: 'institution_charter',
        object_id: charterId,
        correlation_id: crypto.randomUUID(),
        payload: {
          institution_id: charter.rows[0].institution_id,
          version_number: charter.rows[0].version_number,
        },
      });
      await auditLog.appendWithClient(client, {
        agent_id: actorId,
        action_type: 'decision',
        input_summary: `activate institution charter v${charter.rows[0].version_number} (${charter.rows[0].institution_id})`,
        output_summary: `charter ${charterId} active`,
        confidence_score: 1,
        risk_level: 'high',
        human_approved: false,
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

  async getActiveCharter(institutionId: string): Promise<{ id: string; version_number: number; charter_json: Record<string, unknown> } | null> {
    const result = await db.query(
      `SELECT id, version_number, charter_json FROM institution_charters
        WHERE institution_id = $1 AND status = 'active' LIMIT 1`,
      [institutionId]
    );
    return (result.rows[0] as any) ?? null;
  }

  // -------------------------------------------------------------------------
  // Mandates / powers / limits (grant rows)
  // -------------------------------------------------------------------------

  async addMandate(input: {
    institution_id: string;
    mandate_key: string;
    description: string;
    department_name?: string;
    granted_by_actor_id: string;
  }): Promise<{ id: string }> {
    return this.insertGrant('institution_mandates', 'institution.mandate_granted', input.institution_id, input.granted_by_actor_id, {
      mandate_key: input.mandate_key,
      description: input.description,
      department_name: input.department_name ?? null,
    });
  }

  /**
   * Power grants require an authorized decision reference and must not be
   * self-granted by the institution's own actor.
   */
  async grantPower(input: {
    institution_id: string;
    power_key: string;
    scope?: Record<string, unknown>;
    authorized_decision_ref: string;
    granted_by_actor_id: string;
  }): Promise<{ id: string }> {
    if (!input.authorized_decision_ref || input.authorized_decision_ref.trim().length === 0) {
      throw new PublicHttpError(400, 'authorized_decision_ref is required for power grants');
    }
    const institutionActor = await this.institutionActorId(input.institution_id);
    if (institutionActor && institutionActor === input.granted_by_actor_id) {
      throw new PublicHttpError(409, 'an institution cannot unilaterally expand its own powers');
    }
    return this.insertGrant('institution_powers', 'institution.power_granted', input.institution_id, input.granted_by_actor_id, {
      power_key: input.power_key,
      scope_json: input.scope ?? {},
      authorized_decision_ref: input.authorized_decision_ref,
    });
  }

  async setLimit(input: {
    institution_id: string;
    limit_key: string;
    limit_value?: Record<string, unknown>;
    granted_by_actor_id: string;
  }): Promise<{ id: string }> {
    return this.insertGrant('institution_limits', 'institution.limit_set', input.institution_id, input.granted_by_actor_id, {
      limit_key: input.limit_key,
      limit_json: input.limit_value ?? {},
    });
  }

  async listGovernance(institutionId: string): Promise<{
    charter: { version_number: number } | null;
    mandates: Array<{ mandate_key: string; description: string }>;
    powers: Array<{ power_key: string; authorized_decision_ref: string }>;
    limits: Array<{ limit_key: string }>;
  }> {
    const [charter, mandates, powers, limits] = await Promise.all([
      this.getActiveCharter(institutionId),
      db.query(`SELECT mandate_key, description FROM institution_mandates WHERE institution_id = $1 AND status = 'active' ORDER BY mandate_key`, [institutionId]),
      db.query(`SELECT power_key, authorized_decision_ref FROM institution_powers WHERE institution_id = $1 AND status = 'active' ORDER BY power_key`, [institutionId]),
      db.query(`SELECT limit_key FROM institution_limits WHERE institution_id = $1 AND status = 'active' ORDER BY limit_key`, [institutionId]),
    ]);
    return {
      charter: charter ? { version_number: charter.version_number } : null,
      mandates: mandates.rows as any,
      powers: powers.rows as any,
      limits: limits.rows as any,
    };
  }

  private async insertGrant(
    table: 'institution_mandates' | 'institution_powers' | 'institution_limits',
    eventType: string,
    institutionId: string,
    grantedBy: string,
    fields: Record<string, unknown>
  ): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireInstitution(client, institutionId);
      const keyColumn = table === 'institution_mandates' ? 'mandate_key' : table === 'institution_powers' ? 'power_key' : 'limit_key';
      const keyValue = fields[keyColumn] as string;
      const existing = await client.query<{ id: string }>(
        `SELECT id FROM ${table} WHERE institution_id = $1 AND ${keyColumn} = $2 AND status = 'active' LIMIT 1`,
        [institutionId, keyValue]
      );
      if ((existing.rowCount ?? 0) > 0) {
        await client.query('COMMIT');
        return existing.rows[0];
      }
      const grantId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: eventType,
        actor_id: grantedBy,
        object_type: table,
        object_id: grantId,
        correlation_id: crypto.randomUUID(),
        payload: { institution_id: institutionId, ...fields },
      });
      const columns = Object.keys(fields);
      const placeholders = columns.map((_, i) => {
        const value = fields[columns[i]];
        return value !== null && typeof value === 'object' ? `$${i + 4}::jsonb` : `$${i + 4}`;
      });
      const values = columns.map(c => {
        const value = fields[c];
        return value !== null && typeof value === 'object' ? JSON.stringify(value) : value;
      });
      const inserted = await client.query<{ id: string }>(
        `INSERT INTO ${table} (id, institution_id, granted_by_actor_id, ${columns.join(', ')}, event_log_id)
         VALUES ($1,$2,$3,${placeholders.join(',')},$${columns.length + 4})
         RETURNING id`,
        [grantId, institutionId, grantedBy, ...values, event.id]
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

  // -------------------------------------------------------------------------
  // Inter-institution contracts
  // -------------------------------------------------------------------------

  async proposeContract(input: {
    from_institution_id: string;
    to_institution_id: string;
    title: string;
    terms?: Record<string, unknown>;
    commitments?: Array<Record<string, unknown>>;
    proposed_by_actor_id: string;
  }): Promise<{ id: string; status: string }> {
    if (!input.title || input.title.trim().length === 0) {
      throw new PublicHttpError(400, 'title is required');
    }
    if (input.from_institution_id === input.to_institution_id) {
      throw new PublicHttpError(400, 'a contract requires two distinct institutions');
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireInstitution(client, input.from_institution_id);
      await this.requireInstitution(client, input.to_institution_id);
      const contractId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'institution.contract_proposed',
        actor_id: input.proposed_by_actor_id,
        object_type: 'inter_institution_contract',
        object_id: contractId,
        correlation_id: crypto.randomUUID(),
        payload: {
          from_institution_id: input.from_institution_id,
          to_institution_id: input.to_institution_id,
          title: input.title.trim(),
        },
      });
      const inserted = await client.query<{ id: string; status: string }>(
        `INSERT INTO inter_institution_contracts
           (id, from_institution_id, to_institution_id, title, terms_json, commitments_json, proposed_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7,$8)
         RETURNING id, status`,
        [contractId, input.from_institution_id, input.to_institution_id, input.title.trim(),
         JSON.stringify(input.terms ?? {}), JSON.stringify(input.commitments ?? []),
         input.proposed_by_actor_id, event.id]
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

  async transitionContract(input: {
    contract_id: string;
    to_status: 'accepted' | 'active' | 'fulfilled' | 'breached' | 'terminated';
    actor_id: string;
    reason?: string;
    settlement?: Record<string, unknown>;
  }): Promise<{ id: string; status: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const current = await client.query<{
        id: string; status: string; proposed_by_actor_id: string;
        from_institution_id: string; to_institution_id: string;
      }>(
        `SELECT id, status, proposed_by_actor_id, from_institution_id, to_institution_id
           FROM inter_institution_contracts WHERE id = $1 FOR UPDATE`,
        [input.contract_id]
      );
      if ((current.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(404, `contract not found: ${input.contract_id}`);
      }
      if (input.to_status === 'accepted' && current.rows[0].proposed_by_actor_id === input.actor_id) {
        throw new PublicHttpError(409, 'a contract cannot be accepted by its own proposer');
      }
      if (input.to_status === 'breached' && (!input.reason || input.reason.trim().length === 0)) {
        throw new PublicHttpError(400, 'breach requires a reason');
      }
      const terminal = ['fulfilled', 'breached', 'terminated'].includes(input.to_status);
      const event = await eventLog.appendWithClient(client, {
        event_type: `institution.contract_${input.to_status}`,
        actor_id: input.actor_id,
        object_type: 'inter_institution_contract',
        object_id: input.contract_id,
        correlation_id: crypto.randomUUID(),
        payload: {
          from_status: current.rows[0].status,
          to_status: input.to_status,
          reason: input.reason ?? '',
          from_institution_id: current.rows[0].from_institution_id,
          to_institution_id: current.rows[0].to_institution_id,
        },
      });
      const updated = await client.query<{ id: string; status: string }>(
        `UPDATE inter_institution_contracts
            SET status = $2,
                accepted_by_actor_id = CASE WHEN $2 = 'accepted' THEN $3 ELSE accepted_by_actor_id END,
                settlement_json = COALESCE($4::jsonb, settlement_json),
                breach_reason = CASE WHEN $2 = 'breached' THEN $5 ELSE breach_reason END,
                closed_by_actor_id = CASE WHEN $6 THEN $3 ELSE closed_by_actor_id END,
                closed_at = CASE WHEN $6 THEN now() ELSE closed_at END
          WHERE id = $1
          RETURNING id, status`,
        [input.contract_id, input.to_status, input.actor_id,
         input.settlement ? JSON.stringify(input.settlement) : null,
         input.reason ?? null, terminal]
      );
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `contract ${input.contract_id} ${current.rows[0].status} -> ${input.to_status}${input.reason ? `: ${input.reason}` : ''}`,
        output_summary: `contract is now ${input.to_status}`,
        confidence_score: 1,
        risk_level: input.to_status === 'breached' ? 'high' : 'medium',
        human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // -------------------------------------------------------------------------
  // Mandatory civilization-level institutions
  // -------------------------------------------------------------------------

  /** Idempotent seed: 10 mandatory institutions, each with 5 departments,
   * a chartered mandate/powers/limits set, and civilization-wide jurisdiction. */
  async ensureMandatoryInstitutions(actorId?: string): Promise<Array<{ institution_id: string; name: string }>> {
    await civilizationKernel.ensureCivilizationRoot();
    const seedActor = actorId ?? (await this.ensureSeedActor());
    const results: Array<{ institution_id: string; name: string }> = [];
    for (const spec of MANDATORY_INSTITUTIONS) {
      const existing = await db.query<{ id: string }>(
        `SELECT id FROM institutions WHERE name = $1 AND entity_type = 'institution' AND status = 'active' LIMIT 1`,
        [spec.name]
      );
      let institutionId: string;
      if ((existing.rowCount ?? 0) > 0) {
        institutionId = existing.rows[0].id;
      } else {
        const created = await institutionsService.createCanonicalInstitution({
          name: spec.name,
          domain: spec.domain,
          purpose: spec.purpose,
          metadata: { mandatory: true, seeded_by: 'institution-governance-service' },
        });
        institutionId = created.institutionId;
      }

      await societyService.grantInstitutionCivilizationJurisdiction({
        institution_id: institutionId,
        jurisdiction_key: 'global',
        granted_by_actor_id: seedActor,
      });

      const charter = await this.getActiveCharter(institutionId);
      if (!charter) {
        const draft = await this.proposeCharter({
          institution_id: institutionId,
          charter: { name: spec.name, mandate: spec.mandate, powers: spec.powers, limits: spec.limits },
          actor_id: seedActor,
        });
        await this.activateCharter(draft.id, seedActor);
      }
      await this.addMandate({
        institution_id: institutionId,
        mandate_key: 'core',
        description: spec.mandate,
        granted_by_actor_id: seedActor,
      });
      for (const power of spec.powers) {
        await this.grantPower({
          institution_id: institutionId,
          power_key: power,
          authorized_decision_ref: 'decision:mandatory-institution-seed',
          granted_by_actor_id: seedActor,
        });
      }
      for (const limit of spec.limits) {
        await this.setLimit({
          institution_id: institutionId,
          limit_key: limit,
          granted_by_actor_id: seedActor,
        });
      }
      results.push({ institution_id: institutionId, name: spec.name });
    }
    return results;
  }

  async institutionActorId(institutionId: string): Promise<string | null> {
    const result = await db.query<{ actor_id: string | null }>(
      `SELECT metadata->>'actor_id' AS actor_id FROM institutions WHERE id = $1 LIMIT 1`,
      [institutionId]
    );
    return result.rows[0]?.actor_id ?? null;
  }

  private async requireInstitution(client: PoolClient, institutionId: string): Promise<void> {
    const institution = await client.query(
      `SELECT id FROM institutions WHERE id = $1 AND entity_type = 'institution' AND status = 'active' LIMIT 1`,
      [institutionId]
    );
    if ((institution.rowCount ?? 0) !== 1) {
      throw new PublicHttpError(404, `active institution not found: ${institutionId}`);
    }
  }

  private async ensureSeedActor(): Promise<string> {
    const result = await db.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service','agentco-institution-governance','{}'::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`
    );
    return result.rows[0].id;
  }
}

export const institutionGovernance = new InstitutionGovernanceService();
