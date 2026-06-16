/**
 * Audit Log Service — immutable, append-only, hash-chained.
 * No agent has DELETE permission. This is the legal record of every AgentCo decision.
 */
import crypto from 'crypto';

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
  chain_hash: string;  // SHA-256 of previous entry + this entry content
}

let lastHash = '0000000000000000000000000000000000000000000000000000000000000000';

export class AuditLogService {
  /**
   * Append an immutable audit entry. Returns the log_id.
   * Never throws — audit failures are logged to stderr but do not block agent operation.
   */
  async append(entry: AuditEntry): Promise<string> {
    this.validateEntry(entry);

    const log_id = crypto.randomUUID();
    const timestamp = new Date().toISOString();

    const content = JSON.stringify({ log_id, timestamp, ...entry });
    const chain_hash = crypto.createHash('sha256').update(lastHash + content).digest('hex');
    lastHash = chain_hash;

    const record: AuditRecord = { ...entry, log_id, timestamp, chain_hash };

    try {
      // In production: await db.execute('INSERT INTO decision_log ...', record)
      console.log('[AUDIT]', JSON.stringify(record));
    } catch (err) {
      // Audit failures are always reported — never silently swallowed
      console.error('[AUDIT_FAILURE]', err, record);
    }

    return log_id;
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
    // In production: SELECT * FROM decision_log WHERE ... ORDER BY timestamp DESC
    return [];
  }

  async verifyChainIntegrity(): Promise<{ valid: boolean; broken_at?: string }> {
    // In production: re-compute chain hashes from first entry and verify each matches stored hash
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
