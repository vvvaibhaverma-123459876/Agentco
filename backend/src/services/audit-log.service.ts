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

export const CURRENT_DECISION_LOG_SERIALIZATION_VERSION = 'v3.sorted-json-versioned';

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
  serialization_version?: string | null;
}

interface CanonicalDecisionLogFields {
  serialization_version?: string;
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

interface DecisionLogChainRow {
  log_id: string;
  timestamp: string | Date;
  timestamp_text?: string;
  prev_hash: string;
  chain_hash: string;
  serialization_version?: string | null;
  agent_id: string;
  action_type: string;
  input_summary: string;
  output_summary: string;
  confidence_score: string | number;
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

function legacyPythonContent(fields: CanonicalDecisionLogFields): string {
  return JSON.stringify(fields);
}

function normalizeTimestamp(value: string | Date): string {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString();
}

function timestampTextToLegacyPythonUtc(value: string): string | null {
  const match = value.match(
    /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})(\.(\d+))?([+-])(\d{2})(?::?(\d{2}))?$/
  );
  if (!match) return null;
  const [, year, month, day, hour, minute, second, , fractional = '', sign, offsetHour, offsetMinute = '00'] = match;
  const micros = BigInt((fractional + '000000').slice(0, 6));
  const offsetMinutes = BigInt(Number(offsetHour) * 60 + Number(offsetMinute)) * (sign === '+' ? 1n : -1n);
  const localMillis = Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    Number(second)
  );
  const utcMicros = BigInt(localMillis) * 1000n + micros - offsetMinutes * 60n * 1000000n;
  const microsRemainder = Number(utcMicros % 1000000n);
  const baseMillis = (utcMicros - BigInt(microsRemainder)) / 1000n;
  const base = new Date(Number(baseMillis)).toISOString().replace(/\.\d{3}Z$/, '');
  return `${base}.${String(microsRemainder).padStart(6, '0')}+00:00`;
}

function pythonJsonDumps(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(pythonJsonDumps).join(', ')}]`;
  }
  if (value && typeof value === 'object' && !(value instanceof Date)) {
    const sorted = sortCanonical(value) as Record<string, unknown>;
    return `{${Object.keys(sorted).map(key => `${JSON.stringify(key)}: ${pythonJsonDumps(sorted[key])}`).join(', ')}}`;
  }
  return JSON.stringify(value);
}

function normalizeConfidenceScore(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function fieldsForRow(row: DecisionLogChainRow, timestamp: string): CanonicalDecisionLogFields {
  return {
    log_id: row.log_id,
    timestamp,
    prev_hash: row.prev_hash,
    agent_id: row.agent_id,
    action_type: row.action_type,
    input_summary: row.input_summary,
    output_summary: row.output_summary,
    // Postgres NUMERIC comes back as a string; normalise to number for canonical form.
    confidence_score: Number(row.confidence_score),
    risk_level: row.risk_level,
    human_approved: row.human_approved,
    human_approver_id: row.human_approver_id,
    downstream_events: row.downstream_events ?? [],
    session_id: row.session_id,
  };
}

function versionedFieldsForRow(row: DecisionLogChainRow, timestamp: string): CanonicalDecisionLogFields {
  if (!row.serialization_version) {
    throw new Error('versioned decision_log row missing serialization_version');
  }
  return {
    serialization_version: row.serialization_version,
    ...fieldsForRow(row, timestamp),
  };
}

function hashDecisionLogContent(prevHash: string, content: string): string {
  return crypto.createHash('sha256').update(prevHash + content).digest('hex');
}

export function decisionLogChainHashForVersion(
  row: DecisionLogChainRow,
  version: string
): { version: string; hash: string } | null {
  if (version !== CURRENT_DECISION_LOG_SERIALIZATION_VERSION) return null;
  const fields = versionedFieldsForRow(row, normalizeTimestamp(row.timestamp));
  return {
    version,
    hash: hashDecisionLogContent(row.prev_hash, canonicalDecisionLogContent(fields)),
  };
}

export function acceptedDecisionLogChainHashes(row: DecisionLogChainRow): Array<{ version: string; hash: string }> {
  if (row.serialization_version) {
    const versioned = decisionLogChainHashForVersion(row, row.serialization_version);
    return versioned ? [versioned] : [];
  }

  const normalizedFields = fieldsForRow(row, normalizeTimestamp(row.timestamp));
  const candidates = [
    {
      version: 'v2.sorted-json',
      hash: hashDecisionLogContent(row.prev_hash, canonicalDecisionLogContent(normalizedFields)),
    },
    {
      version: 'v1.ts-insertion-json',
      hash: hashDecisionLogContent(row.prev_hash, legacyTsContent(normalizedFields)),
    },
  ];

  if (row.timestamp_text) {
    const legacyPythonTimestamp = timestampTextToLegacyPythonUtc(row.timestamp_text);
    if (legacyPythonTimestamp) {
      const legacyPythonFields = fieldsForRow(row, legacyPythonTimestamp);
      candidates.push({
        version: 'v1.python-insertion-json',
        hash: hashDecisionLogContent(row.prev_hash, legacyPythonContent(legacyPythonFields)),
      });
      candidates.push({
        version: 'v1.python-sorted-json-spaced',
        hash: hashDecisionLogContent(row.prev_hash, pythonJsonDumps(legacyPythonFields)),
      });
    }
  }

  return candidates;
}

function isAfterDecisionLogCutoff(
  row: DecisionLogChainRow,
  cutoff: { cutoff_timestamp: string | Date | null; cutoff_log_id: string | null } | null
): boolean {
  if (!cutoff?.cutoff_timestamp || !cutoff.cutoff_log_id) {
    return true;
  }
  const rowTime = normalizeTimestamp(row.timestamp);
  const cutoffTime = normalizeTimestamp(cutoff.cutoff_timestamp);
  if (rowTime > cutoffTime) return true;
  if (rowTime < cutoffTime) return false;
  return row.log_id > cutoff.cutoff_log_id;
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
    const serialization_version = CURRENT_DECISION_LOG_SERIALIZATION_VERSION;
    const content = canonicalDecisionLogContent({
      serialization_version,
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
          downstream_events, session_id, timestamp, chain_hash, prev_hash,
          serialization_version)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
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
        serialization_version,
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
    const rows = await query<DecisionLogChainRow>(
      `SELECT log_id, agent_id, action_type, input_summary, output_summary,
              confidence_score, risk_level, human_approved, human_approver_id,
              downstream_events, session_id, timestamp, timestamp::text AS timestamp_text,
              chain_hash, prev_hash, serialization_version
       FROM decision_log
       WHERE chain_hash ~ '^[0-9a-f]{64}$'
         AND prev_hash ~ '^[0-9a-f]{64}$'
       ORDER BY timestamp ASC, log_id ASC`
    );
    const cutoffRows = await query<{ cutoff_timestamp: string | Date | null; cutoff_log_id: string | null }>(
      `SELECT cutoff_timestamp, cutoff_log_id
         FROM decision_log_protocol_cutoff
        WHERE id = 'serialization_version_v3'`
    );
    const cutoff = cutoffRows[0] ?? null;

    for (const row of rows) {
      if (!row.serialization_version && isAfterDecisionLogCutoff(row, cutoff)) {
        return { valid: false, broken_at: row.log_id };
      }
      const accepted = acceptedDecisionLogChainHashes(row);
      if (!accepted.some(candidate => candidate.hash === row.chain_hash)) {
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
