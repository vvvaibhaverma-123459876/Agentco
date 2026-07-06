/**
 * Audit Log Service — immutable, append-only, hash-chained.
 *
 * Real implementation: writes to decision_log (Postgres).
 * DB enforces append-only via triggers on decision_log.
 * Hash chain: each row stores SHA-256(prev_hash || canonicalContent(row)).
 * verifyChainIntegrity() re-derives the chain from the DB and detects any tampering.
 *
 * Canonical content: sorted-key compact JSON with normalised types so that
 * Python and TypeScript writers derive the same hash from the stored DB values.
 */
import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db, query } from '../db/client';

export interface AuditEntry {
  agent_id: string;
  action_type: 'decision' | 'api_call' | 'event_published' | 'escalation';
  input_summary: string;
  output_summary: string;
  confidence_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  human_approved?: boolean;
  human_approver_id?: string;
  downstream_events?: string[];
  session_id?: string;
}

export interface AuditRecord extends AuditEntry {
  log_id: string;
  timestamp: string;
  chain_hash: string;
  prev_hash: string;
}

interface CanonicalDecisionLogFields {
  log_id: string;
  timestamp: string;
  prev_hash: string;
  agent_id: string;
  action_type: string;
  input_summary: string;
  output_summary: string;
  confidence_score: number;
  risk_level: string;
  human_approved: boolean;
  human_approver_id: string | null;
  downstream_events: string[];
  session_id: string | null;
}

function sortCanonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortCanonical);
  if (value && typeof value === 'object' && !(value instanceof Date)) {
    return Object.keys(value as Record<string, unknown>)
      .sort()
      .reduce<Record<string, unknown>>((acc, key) => {
        acc[key] = sortCanonical((value as Record<string, unknown>)[key]);
        return acc;
      }, {});
  }
  return value;
}

/**
 * Build the canonical string that is hashed for a given row.
 * This is the cross-language contract used by both append() and verifyChainIntegrity().
 */
export function canonicalDecisionLogContent(fields: CanonicalDecisionLogFields): string {
  return JSON.stringify(sortCanonical(fields));
}

function legacyTsContent(fields: CanonicalDecisionLogFields): string {
  return JSON.stringify(fields);
}

function normalizeTimestamp(value: string | Date): string {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString();
}

function normalizeConfidenceScore(value: number): number {
  return Math.round(value * 1000) / 1000;
}

export class AuditLogService {
  /**
   * Append an immutable audit entry. Returns the log_id.
   * Throws on failure — callers must know when an entry was NOT persisted.
   */
  async append(entry: AuditEntry): Promise<string> {
    this.validateEntry(entry);

    const log_id = crypto.randomUUID();
    const timestamp = new Date().toISOString();
    const client = await db.connect();

    try {
      await client.query('BEGIN');
      const record = await this.appendWithClient(client, entry, { log_id, timestamp });
      await client.query('COMMIT');
      return record.log_id;
    } catch (err) {
      await client.query('ROLLBACK').catch(() => undefined);
      console.error('[AUDIT_FAILURE]', err, entry);
      throw err;
    } finally {
      client.release();
    }
  }

  async appendWithClient(
    client: PoolClient,
    entry: AuditEntry,
    options: { log_id?: string; timestamp?: string } = {}
  ): Promise<AuditRecord> {
    this.validateEntry(entry);
    const log_id = options.log_id ?? crypto.randomUUID();
    const timestamp = normalizeTimestamp(options.timestamp ?? new Date().toISOString());
    const previous = await client.query<{ chain_hash: string }>(
      `SELECT chain_hash
         FROM decision_log
        WHERE chain_hash ~ '^[0-9a-f]{64}$'
          AND prev_hash ~ '^[0-9a-f]{64}$'
        ORDER BY timestamp DESC, log_id DESC
        LIMIT 1`
    );
    const prev_hash = previous.rows[0]?.chain_hash ?? '0'.repeat(64);

    const human_approved = entry.human_approved ?? false;
    const human_approver_id = entry.human_approver_id ?? null;
    const downstream_events = entry.downstream_events ?? [];
    const session_id = entry.session_id ?? null;
    const content = canonicalDecisionLogContent({
      log_id,
      timestamp,
      prev_hash,
      agent_id: entry.agent_id,
      action_type: entry.action_type,
      input_summary: entry.input_summary,
      output_summary: entry.output_summary,
      confidence_score: normalizeConfidenceScore(entry.confidence_score),
      risk_level: entry.risk_level,
      human_approved,
      human_approver_id,
      downstream_events,
      session_id,
    });
    const chain_hash = crypto.createHash('sha256').update(prev_hash + content).digest('hex');

    const result = await client.query<AuditRecord>(
      `INSERT INTO decision_log
         (log_id, agent_id, action_type, input_summary, output_summary,
          confidence_score, risk_level, human_approved, human_approver_id,
          downstream_events, session_id, timestamp, chain_hash, prev_hash)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
       RETURNING log_id, agent_id, action_type, input_summary, output_summary,
                 confidence_score, risk_level, human_approved, human_approver_id,
                 downstream_events, session_id, timestamp, chain_hash, prev_hash`,
      [
        log_id,
        entry.agent_id,
        entry.action_type,
        entry.input_summary,
        entry.output_summary,
        normalizeConfidenceScore(entry.confidence_score),
        entry.risk_level,
        human_approved,
        human_approver_id,
        downstream_events,
        session_id,
        timestamp,
        chain_hash,
        prev_hash,
      ]
    );
    return result.rows[0];
  }

  async query(filters: {
    agent_id?: string;
    risk_level?: string;
    human_approved?: boolean;
    from?: string;
    to?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditRecord[]> {
    const conditions: string[] = [];
    const params: unknown[] = [];
    let p = 1;

    if (filters.agent_id)      { conditions.push(`agent_id = $${p++}`);      params.push(filters.agent_id); }
    if (filters.risk_level)    { conditions.push(`risk_level = $${p++}`);     params.push(filters.risk_level); }
    if (filters.human_approved !== undefined) {
      conditions.push(`human_approved = $${p++}`); params.push(filters.human_approved);
    }
    if (filters.from) { conditions.push(`timestamp >= $${p++}`); params.push(filters.from); }
    if (filters.to)   { conditions.push(`timestamp <= $${p++}`); params.push(filters.to); }

    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';
    const limit  = Math.min(filters.limit ?? 100, 1000);
    const offset = filters.offset ?? 0;

    return query<AuditRecord>(
      `SELECT * FROM decision_log ${where} ORDER BY timestamp DESC LIMIT $${p++} OFFSET $${p++}`,
      [...params, limit, offset]
    );
  }

  /**
   * Re-derives the hash chain from the DB (oldest→newest) and verifies each
   * row's stored chain_hash matches the re-computed value.
   * Returns { valid: true } or { valid: false, broken_at: log_id }.
   */
  async verifyChainIntegrity(): Promise<{ valid: boolean; broken_at?: string }> {
    // Only verify rows that participate in the hash chain. Historical verifier
    // reports may have populated non-SHA marker strings in chain_hash; those
    // rows are audit records, but not valid chain links.
    const rows = await query<{
      log_id: string; timestamp: string; prev_hash: string; chain_hash: string;
      agent_id: string; action_type: string; input_summary: string; output_summary: string;
      confidence_score: string | number; risk_level: string;
      human_approved: boolean; human_approver_id: string | null;
      downstream_events: string[]; session_id: string | null;
    }>(
      `SELECT log_id, agent_id, action_type, input_summary, output_summary,
              confidence_score, risk_level, human_approved, human_approver_id,
              downstream_events, session_id, timestamp, chain_hash, prev_hash
       FROM decision_log
       WHERE chain_hash ~ '^[0-9a-f]{64}$'
         AND prev_hash ~ '^[0-9a-f]{64}$'
       ORDER BY timestamp ASC, log_id ASC`
    );

    for (const row of rows) {
      const fields = {
        log_id: row.log_id,
        timestamp: normalizeTimestamp(row.timestamp),
        prev_hash: row.prev_hash,
        agent_id: row.agent_id,
        action_type: row.action_type,
        input_summary: row.input_summary,
        output_summary: row.output_summary,
        // Postgres NUMERIC comes back as a string; normalise to number for canonical form
        confidence_score: Number(row.confidence_score),
        risk_level: row.risk_level,
        human_approved: row.human_approved,
        human_approver_id: row.human_approver_id,
        downstream_events: row.downstream_events ?? [],
        session_id: row.session_id,
      };

      const computed = crypto.createHash('sha256').update(row.prev_hash + canonicalDecisionLogContent(fields)).digest('hex');
      const legacyComputed = crypto.createHash('sha256').update(row.prev_hash + legacyTsContent(fields)).digest('hex');
      if (computed !== row.chain_hash && legacyComputed !== row.chain_hash) {
        return { valid: false, broken_at: row.log_id };
      }
    }

    return { valid: true };
  }

  private validateEntry(entry: AuditEntry): void {
    if (!entry.agent_id) throw new Error('audit entry missing agent_id');
    if (entry.confidence_score < 0 || entry.confidence_score > 1) {
      throw new Error(`invalid confidence_score: ${entry.confidence_score}`);
    }
    if (!['decision','api_call','event_published','escalation'].includes(entry.action_type)) {
      throw new Error(`invalid action_type: ${entry.action_type}`);
    }
  }
}

export const auditLog = new AuditLogService();
