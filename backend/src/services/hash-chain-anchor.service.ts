import crypto from 'crypto';
import { db } from '../db/client';
import { auditLog } from './audit-log.service';
import { eventLog } from './event-log.service';

export interface HashChainAnchorRecord {
  id: string;
  anchor_scope: 'internal_postgres';
  event_log_head_id: string | null;
  event_log_head_hash: string;
  decision_log_head_id: string | null;
  decision_log_head_hash: string;
  combined_root_hash: string;
  event_count: string;
  decision_count: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface AnchorVerification {
  valid: boolean;
  reason: 'anchor_valid' | 'event_chain_invalid' | 'audit_chain_invalid' | 'anchor_not_found' | 'root_mismatch' | 'event_head_moved' | 'audit_head_moved';
  anchor_id?: string;
  current_event_head_hash?: string;
  current_decision_head_hash?: string;
}

function combinedRoot(eventHeadHash: string, decisionHeadHash: string, eventCount: string, decisionCount: string): string {
  return crypto
    .createHash('sha256')
    .update(JSON.stringify({
      anchor_scope: 'internal_postgres',
      event_log_head_hash: eventHeadHash,
      decision_log_head_hash: decisionHeadHash,
      event_count: eventCount,
      decision_count: decisionCount,
    }))
    .digest('hex');
}

export class HashChainAnchorService {
  async createAnchor(metadata: Record<string, unknown> = {}): Promise<HashChainAnchorRecord> {
    const eventIntegrity = await eventLog.verifyChainIntegrity();
    if (!eventIntegrity.valid) throw new Error(`event chain invalid at ${eventIntegrity.broken_at}`);
    const auditIntegrity = await auditLog.verifyChainIntegrity();
    if (!auditIntegrity.valid) throw new Error(`audit chain invalid at ${auditIntegrity.broken_at}`);

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const eventHead = await client.query<{ id: string; event_hash: string; count: string }>(
        `SELECT head.id, head.event_hash, totals.count
           FROM (SELECT COUNT(*)::text AS count FROM event_log) totals
           LEFT JOIN LATERAL (
             SELECT id, event_hash
               FROM event_log
              ORDER BY occurred_at DESC, id DESC
              LIMIT 1
           ) head ON true`
      );
      const auditHead = await client.query<{ log_id: string; chain_hash: string; count: string }>(
        `SELECT head.log_id, head.chain_hash, totals.count
           FROM (SELECT COUNT(*)::text AS count FROM decision_log WHERE chain_hash <> '') totals
           LEFT JOIN LATERAL (
             SELECT log_id, chain_hash
               FROM decision_log
              WHERE chain_hash <> ''
              ORDER BY timestamp DESC, log_id DESC
              LIMIT 1
           ) head ON true`
      );
      const eventHeadHash = eventHead.rows[0]?.event_hash ?? '0'.repeat(64);
      const decisionHeadHash = auditHead.rows[0]?.chain_hash ?? '0'.repeat(64);
      const eventCount = eventHead.rows[0]?.count ?? '0';
      const decisionCount = auditHead.rows[0]?.count ?? '0';
      const root = combinedRoot(eventHeadHash, decisionHeadHash, eventCount, decisionCount);

      const result = await client.query<HashChainAnchorRecord>(
        `INSERT INTO hash_chain_anchors
           (anchor_scope, event_log_head_id, event_log_head_hash, decision_log_head_id,
            decision_log_head_hash, combined_root_hash, event_count, decision_count, metadata_json)
         VALUES ('internal_postgres',$1,$2,$3,$4,$5,$6,$7,$8::jsonb)
         RETURNING id, anchor_scope, event_log_head_id, event_log_head_hash,
                   decision_log_head_id, decision_log_head_hash, combined_root_hash,
                   event_count, decision_count, metadata_json, created_at`,
        [
          eventHead.rows[0]?.id ?? null,
          eventHeadHash,
          auditHead.rows[0]?.log_id ?? null,
          decisionHeadHash,
          root,
          eventCount,
          decisionCount,
          JSON.stringify(metadata),
        ]
      );
      await client.query('COMMIT');
      return result.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async verifyAnchor(anchorId: string): Promise<AnchorVerification> {
    const eventIntegrity = await eventLog.verifyChainIntegrity();
    if (!eventIntegrity.valid) return { valid: false, reason: 'event_chain_invalid', anchor_id: anchorId };
    const auditIntegrity = await auditLog.verifyChainIntegrity();
    if (!auditIntegrity.valid) return { valid: false, reason: 'audit_chain_invalid', anchor_id: anchorId };

    const anchor = await db.query<HashChainAnchorRecord>(
      `SELECT id, anchor_scope, event_log_head_id, event_log_head_hash,
              decision_log_head_id, decision_log_head_hash, combined_root_hash,
              event_count, decision_count, metadata_json, created_at
         FROM hash_chain_anchors
        WHERE id = $1`,
      [anchorId]
    );
    if (anchor.rowCount !== 1) return { valid: false, reason: 'anchor_not_found', anchor_id: anchorId };
    const row = anchor.rows[0];
    const expectedRoot = combinedRoot(row.event_log_head_hash, row.decision_log_head_hash, String(row.event_count), String(row.decision_count));
    if (expectedRoot !== row.combined_root_hash) return { valid: false, reason: 'root_mismatch', anchor_id: anchorId };

    const currentEvent = await db.query<{ event_hash: string }>(
      `SELECT event_hash FROM event_log ORDER BY occurred_at DESC, id DESC LIMIT 1`
    );
    const currentDecision = await db.query<{ chain_hash: string }>(
      `SELECT chain_hash FROM decision_log WHERE chain_hash <> '' ORDER BY timestamp DESC, log_id DESC LIMIT 1`
    );
    const currentEventHeadHash = currentEvent.rows[0]?.event_hash ?? '0'.repeat(64);
    const currentDecisionHeadHash = currentDecision.rows[0]?.chain_hash ?? '0'.repeat(64);
    if (currentEventHeadHash !== row.event_log_head_hash) {
      return {
        valid: false,
        reason: 'event_head_moved',
        anchor_id: anchorId,
        current_event_head_hash: currentEventHeadHash,
        current_decision_head_hash: currentDecisionHeadHash,
      };
    }
    if (currentDecisionHeadHash !== row.decision_log_head_hash) {
      return {
        valid: false,
        reason: 'audit_head_moved',
        anchor_id: anchorId,
        current_event_head_hash: currentEventHeadHash,
        current_decision_head_hash: currentDecisionHeadHash,
      };
    }
    return {
      valid: true,
      reason: 'anchor_valid',
      anchor_id: anchorId,
      current_event_head_hash: currentEventHeadHash,
      current_decision_head_hash: currentDecisionHeadHash,
    };
  }
}

export const hashChainAnchor = new HashChainAnchorService();
