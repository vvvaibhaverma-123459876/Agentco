import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { auditLog } from './audit-log.service';
import { eventLog } from './event-log.service';

export interface RegisterEvidenceInput {
  action_id?: string | null;
  actor_id?: string | null;
  source_id?: string;
  url: string;
  title?: string | null;
  snippet?: string | null;
  content_hash: string;
  source_type: 'web' | 'web_search' | 'document' | 'analysis' | 'agent_output';
  is_public_access?: boolean;
  metadata?: Record<string, unknown>;
  correlation_id?: string;
}

export interface EvidenceRecord {
  id: string;
  source_id: string;
  action_id: string | null;
  url: string;
  title: string | null;
  snippet: string | null;
  content_hash: string;
  source_type: string;
  is_public_access: boolean;
  event_log_id: string | null;
  registered_by_actor_id: string | null;
  metadata_json: Record<string, unknown>;
}

function requireNonEmpty(value: string | undefined | null, field: string): string {
  const normalized = value?.trim();
  if (!normalized) throw new Error(`${field} is required`);
  return normalized;
}

function requireHttpUrl(value: string): void {
  const parsed = new URL(value);
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('evidence url must be http(s)');
  }
}

function isUuid(value?: string | null): boolean {
  return Boolean(value && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value));
}

export class EvidenceRegistryService {
  async register(input: RegisterEvidenceInput): Promise<EvidenceRecord> {
    this.validate(input);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.registerWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async registerWithClient(client: PoolClient, input: RegisterEvidenceInput): Promise<EvidenceRecord> {
    this.validate(input);
    const actorId = await this.resolveActor(client, input.actor_id);
    const sourceId = input.source_id ?? crypto.randomUUID();
    const timestamp = new Date().toISOString();
    const correlationId = input.correlation_id ?? crypto.randomUUID();

    const existing = await client.query<EvidenceRecord>(
      `SELECT id, source_id, action_id, url, title, snippet, content_hash,
              source_type, is_public_access, event_log_id, registered_by_actor_id, metadata_json
         FROM autonomy_evidence
        WHERE source_id = $1
        LIMIT 1`,
      [sourceId]
    );
    if ((existing.rowCount ?? 0) > 0) {
      return existing.rows[0];
    }

    const canonicalEvent = await eventLog.appendWithClient(client, {
      event_type: 'evidence.registered',
      actor_id: actorId,
      object_type: 'evidence',
      payload: {
        source_id: sourceId,
        action_id: input.action_id ?? null,
        url: input.url,
        title: input.title ?? null,
        content_hash: input.content_hash,
        source_type: input.source_type,
        is_public_access: input.is_public_access ?? true,
      },
      correlation_id: correlationId,
      occurred_at: timestamp,
    });

    const inserted = await client.query<EvidenceRecord>(
      `INSERT INTO autonomy_evidence
         (id, source_id, action_id, url, title, snippet, retrieved_at, content_hash,
          source_type, is_public_access, event_log_id, registered_by_actor_id, metadata_json, created_at)
       VALUES ($1,$2,$3,$4,$5,$6,NOW(),$7,$8,$9,$10,$11,$12::jsonb,NOW())
       RETURNING id, source_id, action_id, url, title, snippet, content_hash,
                 source_type, is_public_access, event_log_id, registered_by_actor_id, metadata_json`,
      [
        crypto.randomUUID(),
        sourceId,
        input.action_id ?? null,
        input.url,
        input.title ?? null,
        input.snippet ?? null,
        input.content_hash,
        input.source_type,
        input.is_public_access ?? true,
        canonicalEvent.id,
        actorId,
        JSON.stringify(input.metadata ?? {}),
      ]
    );

    await auditLog.appendWithClient(client, {
      agent_id: actorId,
      action_type: 'event_published',
      input_summary: `register evidence source_type=${input.source_type}`,
      output_summary: `source_id=${inserted.rows[0].source_id}`,
      confidence_score: 1,
      risk_level: 'low',
      downstream_events: [canonicalEvent.id],
      session_id: correlationId,
    }, { timestamp });

    return inserted.rows[0];
  }

  async getBySourceIds(sourceIds: string[]): Promise<EvidenceRecord[]> {
    if (!Array.isArray(sourceIds) || sourceIds.length === 0) return [];
    const result = await db.query<EvidenceRecord>(
      `SELECT id, source_id, action_id, url, title, snippet, content_hash,
              source_type, is_public_access, event_log_id, registered_by_actor_id, metadata_json
         FROM autonomy_evidence
        WHERE source_id = ANY($1::text[])
        ORDER BY created_at ASC`,
      [sourceIds]
    );
    return result.rows;
  }

  private validate(input: RegisterEvidenceInput): void {
    requireNonEmpty(input.url, 'url');
    requireHttpUrl(input.url);
    requireNonEmpty(input.content_hash, 'content_hash');
    requireNonEmpty(input.source_type, 'source_type');
    if (input.action_id && !isUuid(input.action_id)) throw new Error('action_id must be a UUID when provided');
    if (input.actor_id && !isUuid(input.actor_id)) throw new Error('actor_id must be a UUID when provided');
  }

  private async resolveActor(client: PoolClient, actorId?: string | null): Promise<string> {
    if (actorId && isUuid(actorId)) {
      const existing = await client.query('SELECT 1 FROM actors WHERE id = $1 AND status = $2', [actorId, 'active']);
      if (existing.rowCount === 1) return actorId;
    }

    const name = 'agentco-evidence-service';
    const current = await client.query<{ id: string }>(
      `SELECT id FROM actors
        WHERE actor_type = 'service'
          AND name = $1
          AND status = 'active'
        LIMIT 1`,
      [name]
    );
    if ((current.rowCount ?? 0) > 0) return current.rows[0].id;

    const created = await client.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ created_by: 'EvidenceRegistryService' })]
    );
    await client.query(
      `INSERT INTO service_identities (actor_id, service_name, scopes)
       VALUES ($1,$2,$3::jsonb)
       ON CONFLICT (actor_id) DO NOTHING`,
      [created.rows[0].id, name, JSON.stringify(['evidence.register'])]
    );
    return created.rows[0].id;
  }
}

export const evidenceRegistry = new EvidenceRegistryService();
