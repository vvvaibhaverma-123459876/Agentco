import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';

export interface RegisterDomainInput {
  domain_key: string;
  display_name?: string;
  institution_id: string;
  proof_subject_id: string;
  required_trust_threshold?: number;
  proof?: Record<string, unknown>;
  correlation_id?: string;
}

export interface DomainRegistryRecord {
  id: string;
  domain_key: string;
  display_name: string;
  status: string;
  institution_id: string;
  institution_actor_id: string | null;
  proof_subject_id: string;
  required_trust_threshold: string | number;
  latest_trust_id: string;
  latest_trust_factor: string | number;
  proof_json: Record<string, unknown>;
  event_log_id: string | null;
}

export interface QualifiedInstitutionRoute extends DomainRegistryRecord {
  match_type: 'exact' | 'parent';
  matched_domain_key: string;
}

function normalizeDomainKey(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/\s+/g, '_');
  if (!/^[a-z0-9][a-z0-9_.-]{2,80}$/.test(normalized) || normalized.includes('..')) {
    throw new Error('domain_key must be 3-81 chars of lowercase letters, numbers, dots, underscores, or hyphens');
  }
  return normalized;
}

function validateThreshold(value: number): void {
  if (!Number.isFinite(value) || value < 0 || value > 1) {
    throw new Error('required_trust_threshold must be between 0 and 1');
  }
}

export class DomainRegistryService {
  async registerDomain(input: RegisterDomainInput): Promise<DomainRegistryRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.registerDomainWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async registerDomainWithClient(client: PoolClient, input: RegisterDomainInput): Promise<DomainRegistryRecord> {
    const domainKey = normalizeDomainKey(input.domain_key);
    const threshold = input.required_trust_threshold ?? 0.7;
    validateThreshold(threshold);
    const existing = await client.query<DomainRegistryRecord>(
      `SELECT id, domain_key, display_name, status, institution_id, institution_actor_id,
              proof_subject_id, required_trust_threshold, latest_trust_id, latest_trust_factor,
              proof_json, event_log_id
         FROM domain_registry
        WHERE domain_key = $1
        LIMIT 1`,
      [domainKey]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];

    const institution = await this.requireCoreInstitution(client, input.institution_id);
    const trust = await this.requireDomainTrust(client, {
      domainKey,
      proofSubjectId: input.proof_subject_id,
      threshold,
    });

    const id = crypto.randomUUID();
    const correlationId = input.correlation_id ?? crypto.randomUUID();
    const actorId = institution.actor_id ?? await this.ensureServiceActor(client);
    const event = await eventLog.appendWithClient(client, {
      event_type: 'domain.activated',
      actor_id: actorId,
      object_type: 'domain',
      object_id: id,
      correlation_id: correlationId,
      payload: {
        domain_key: domainKey,
        institution_id: input.institution_id,
        proof_subject_id: input.proof_subject_id,
        latest_trust_id: trust.trust_id,
        latest_trust_factor: Number(trust.trust_factor),
        required_trust_threshold: threshold,
      },
    });

    const inserted = await client.query<DomainRegistryRecord>(
      `INSERT INTO domain_registry
         (id, domain_key, display_name, status, institution_id, institution_actor_id,
          proof_subject_id, required_trust_threshold, latest_trust_id, latest_trust_factor,
          proof_json, event_log_id)
       VALUES ($1,$2,$3,'active',$4,$5,$6,$7,$8,$9,$10::jsonb,$11)
       RETURNING id, domain_key, display_name, status, institution_id, institution_actor_id,
                 proof_subject_id, required_trust_threshold, latest_trust_id,
                 latest_trust_factor, proof_json, event_log_id`,
      [
        id,
        domainKey,
        input.display_name ?? domainKey.replace(/[_-]+/g, ' '),
        input.institution_id,
        institution.actor_id,
        input.proof_subject_id,
        threshold,
        trust.trust_id,
        trust.trust_factor,
        JSON.stringify(input.proof ?? {}),
        event.id,
      ]
    );
    return inserted.rows[0];
  }

  async getDomain(domainKey: string): Promise<DomainRegistryRecord | null> {
    const result = await db.query<DomainRegistryRecord>(
      `SELECT id, domain_key, display_name, status, institution_id, institution_actor_id,
              proof_subject_id, required_trust_threshold, latest_trust_id, latest_trust_factor,
              proof_json, event_log_id
         FROM domain_registry
        WHERE domain_key = $1
        LIMIT 1`,
      [normalizeDomainKey(domainKey)]
    );
    return result.rows[0] ?? null;
  }

  async qualifiedInstitutionsForDomain(
    domainKey: string,
    options: { minimumTrust?: number; includeParentDomains?: boolean; limit?: number } = {}
  ): Promise<QualifiedInstitutionRoute[]> {
    const normalized = normalizeDomainKey(domainKey);
    const candidates = options.includeParentDomains === false
      ? [normalized]
      : this.domainKeyLineage(normalized);
    const minimumTrust = options.minimumTrust ?? 0.7;
    validateThreshold(minimumTrust);
    const limit = Math.max(1, Math.min(options.limit ?? candidates.length, 50));

    const result = await db.query<QualifiedInstitutionRoute>(
      `SELECT id, domain_key, display_name, status, institution_id, institution_actor_id,
              proof_subject_id, required_trust_threshold, latest_trust_id, latest_trust_factor,
              proof_json, event_log_id,
              CASE WHEN domain_key = $1 THEN 'exact' ELSE 'parent' END AS match_type,
              domain_key AS matched_domain_key
         FROM domain_registry
        WHERE status = 'active'
          AND domain_key = ANY($2::text[])
          AND latest_trust_factor >= required_trust_threshold
          AND latest_trust_factor >= $3
        ORDER BY CASE WHEN domain_key = $1 THEN 0 ELSE 1 END,
                 length(domain_key) DESC,
                 latest_trust_factor DESC,
                 created_at ASC
        LIMIT $4`,
      [normalized, candidates, minimumTrust, limit]
    );
    return result.rows;
  }

  async bestInstitutionForDomain(
    domainKey: string,
    options: { minimumTrust?: number; includeParentDomains?: boolean } = {}
  ): Promise<QualifiedInstitutionRoute | null> {
    const routes = await this.qualifiedInstitutionsForDomain(domainKey, { ...options, limit: 1 });
    return routes[0] ?? null;
  }

  private async requireCoreInstitution(client: PoolClient, institutionId: string): Promise<{ actor_id: string | null }> {
    const institution = await client.query<{ actor_id: string | null }>(
      `SELECT metadata->>'actor_id' AS actor_id
         FROM institutions
        WHERE id = $1
          AND entity_type = 'institution'
          AND status = 'active'
        LIMIT 1`,
      [institutionId]
    );
    if ((institution.rowCount ?? 0) !== 1) {
      throw new Error(`active institution not found: ${institutionId}`);
    }

    const departments = await client.query<{ count: string }>(
      `SELECT COUNT(DISTINCT name)::int AS count
         FROM departments
        WHERE institution_id = $1
          AND status = 'active'
          AND name = ANY($2::text[])`,
      [institutionId, ['Production', 'Verification', 'Audit', 'Adversarial', 'Improvement']]
    );
    if (Number(departments.rows[0].count) !== 5) {
      throw new Error('domain onboarding requires all five core institution departments');
    }
    return institution.rows[0];
  }

  private domainKeyLineage(domainKey: string): string[] {
    const parts = domainKey.split('.');
    const lineage: string[] = [];
    while (parts.length > 0) {
      lineage.push(parts.join('.'));
      parts.pop();
    }
    return lineage;
  }

  private async requireDomainTrust(
    client: PoolClient,
    input: { domainKey: string; proofSubjectId: string; threshold: number }
  ): Promise<{ trust_id: string; trust_factor: string | number }> {
    const trust = await client.query<{ trust_id: string; trust_factor: string | number; force_downgrade: boolean }>(
      `SELECT trust_id, trust_factor, force_downgrade
         FROM trust_scores
        WHERE subject_id = $1
          AND domain = $2
        ORDER BY window_end DESC, created_at DESC
        LIMIT 1`,
      [input.proofSubjectId, input.domainKey]
    );
    if ((trust.rowCount ?? 0) !== 1) {
      throw new Error(`trust proof not found for domain=${input.domainKey} subject=${input.proofSubjectId}`);
    }
    if (trust.rows[0].force_downgrade) {
      throw new Error('domain trust proof is force-downgraded');
    }
    if (Number(trust.rows[0].trust_factor) < input.threshold) {
      throw new Error(`domain trust ${trust.rows[0].trust_factor} is below threshold ${input.threshold}`);
    }
    return trust.rows[0];
  }

  /**
   * Enforcement sweep: suspend every active domain whose latest trust factor
   * has fallen below its declared required threshold. Idempotent — a suspended
   * domain matches no row on re-run. Driven by the civilization OS tick (C12).
   */
  async suspendBelowThreshold(actorId?: string): Promise<number> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const suspended = await client.query<{ id: string; domain_key: string }>(
        `UPDATE domain_registry
            SET status = 'suspended', updated_at = now()
          WHERE status = 'active' AND latest_trust_factor < required_trust_threshold
          RETURNING id, domain_key`
      );
      const actor = actorId ?? (await this.ensureServiceActor(client));
      for (const row of suspended.rows) {
        await eventLog.appendWithClient(client, {
          event_type: 'domain.suspended_below_threshold',
          actor_id: actor,
          object_type: 'domain_registry',
          object_id: row.id,
          correlation_id: crypto.randomUUID(),
          payload: { domain_key: row.domain_key },
        });
      }
      await client.query('COMMIT');
      return suspended.rowCount ?? 0;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async ensureServiceActor(client: PoolClient): Promise<string> {
    const name = 'agentco-domain-registry';
    const actor = await client.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ created_by: 'DomainRegistryService' })]
    );
    await client.query(
      `INSERT INTO service_identities (actor_id, service_name, scopes)
       VALUES ($1,$2,$3::jsonb)
       ON CONFLICT (actor_id) DO NOTHING`,
      [actor.rows[0].id, name, JSON.stringify(['domain.register'])]
    );
    return actor.rows[0].id;
  }
}

export const domainRegistry = new DomainRegistryService();
