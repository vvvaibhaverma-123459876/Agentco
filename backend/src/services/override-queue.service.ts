/**
 * Human Override Queue Service — real Postgres persistence.
 *
 * Real implementation:
 *   enqueue()      → INSERT into override_queue; action is BLOCKED until approved.
 *   resolve()      → UPDATE status (approved/rejected); DB trigger enforces write-once.
 *   listPending()  → SELECT WHERE status='pending'.
 *   getOverdueSla() → SELECT WHERE status='pending' AND expires_at < NOW().
 *
 * BLOCKING INVARIANT: approved=false means the action does NOT run. Period.
 * No timeout-auto-approve path. SLA expiry changes status to 'expired', which
 * is a REJECTION — the action still does not execute.
 */
import crypto from 'crypto';
import { query } from '../db/client';

export type OverrideStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface OverrideRequest {
  request_id: string;
  agent_id: string;
  action: string;
  risk_score: number;
  risk_level: 'high' | 'critical';
  context: Record<string, unknown>;
  created_at: string;
  sla_hours: number;
  expires_at: string;
  status: OverrideStatus;
  resolved_by?: string;
  resolved_at?: string;
  resolution_notes?: string;
}

const SLA_HOURS: Record<string, number> = {
  config_change:    4,
  spend_approval:   2,
  strategic_pivot:  8,
  contract_flagged: 4,
  breach_suspected: 0.5,   // 30 minutes
  agent_upgrade:    8,
  rollback_failure: 0.25,  // 15 minutes
  novel_incident:   1,
  runway_alert:     2,
  critical_risk:    1,
  default:          4,
};

export class OverrideQueueService {
  async enqueue(
    agentId: string,
    action: string,
    riskLevel: 'high' | 'critical',
    context: Record<string, unknown>
  ): Promise<OverrideRequest> {
    const sla_hours = SLA_HOURS[action] ?? SLA_HOURS['default'];
    const expires_at = new Date(Date.now() + sla_hours * 3_600_000).toISOString();

    const rows = await query<OverrideRequest>(
      `INSERT INTO override_queue
         (agent_id, action, risk_score, risk_level, context, sla_hours, expires_at)
       VALUES ($1,$2,$3,$4,$5,$6,$7)
       RETURNING *`,
      [
        agentId,
        action,
        (context['risk_score'] as number) ?? 0,
        riskLevel,
        JSON.stringify(context),
        sla_hours,
        expires_at,
      ]
    );

    const request = rows[0];
    // Fire-and-forget alert (log for now; wire PagerDuty/Slack via webhook env var)
    this._sendAlert(request).catch(err =>
      console.error('[OVERRIDE_ALERT_FAILURE]', err)
    );
    return request;
  }

  async resolve(
    requestId: string,
    resolution: 'approved' | 'rejected',
    resolvedBy: string,
    notes?: string
  ): Promise<OverrideRequest & { approval_token?: string }> {
    const approval_token = resolution === 'approved'
      ? crypto.randomUUID()
      : undefined;

    // First expire any SLA-breached pending requests
    await this._expireOverdue();

    const rows = await query<OverrideRequest & { approval_token?: string }>(
      `UPDATE override_queue
         SET status=$1, resolved_by=$2, resolved_at=NOW(),
             resolution_notes=$3, approval_token=$4
       WHERE request_id=$5 AND status='pending'
       RETURNING *`,
      [resolution, resolvedBy, notes ?? null, approval_token ?? null, requestId]
    );

    if (rows.length === 0) {
      // Either not found or already resolved — check which
      const existing = await query<OverrideRequest>(
        `SELECT status FROM override_queue WHERE request_id=$1`, [requestId]
      );
      if (existing.length === 0) throw new Error(`Override ${requestId} not found`);
      throw new Error(`Override ${requestId} is already ${existing[0].status}`);
    }

    return rows[0];
  }

  async listPending(filters?: { agent_id?: string; risk_level?: string }): Promise<OverrideRequest[]> {
    await this._expireOverdue();

    const conditions = [`status='pending'`];
    const params: unknown[] = [];
    let p = 1;
    if (filters?.agent_id)   { conditions.push(`agent_id=$${p++}`);   params.push(filters.agent_id); }
    if (filters?.risk_level) { conditions.push(`risk_level=$${p++}`); params.push(filters.risk_level); }

    return query<OverrideRequest>(
      `SELECT * FROM override_queue WHERE ${conditions.join(' AND ')} ORDER BY created_at ASC`,
      params
    );
  }

  async getOverdueSla(): Promise<OverrideRequest[]> {
    await this._expireOverdue();
    return query<OverrideRequest>(
      `SELECT * FROM override_queue WHERE status='expired' ORDER BY expires_at ASC`
    );
  }

  /** Mark SLA-breached pending requests as 'expired' (= rejected; action stays blocked). */
  private async _expireOverdue(): Promise<void> {
    await query(
      `UPDATE override_queue
         SET status='expired', resolved_at=NOW(), resolution_notes='SLA breached — auto-expired'
       WHERE status='pending' AND expires_at < NOW()`
    );
  }

  private async _sendAlert(request: OverrideRequest): Promise<void> {
    const webhookUrl = process.env.OVERRIDE_WEBHOOK_URL;
    if (!webhookUrl) return;

    const body = JSON.stringify({
      text: `🚨 Override Required\nAgent: ${request.agent_id}\nAction: ${request.action}\n` +
            `Risk: ${request.risk_level}\nSLA: ${request.sla_hours}h\nID: ${request.request_id}`,
    });

    // Fire HTTP POST to webhook (Slack / PagerDuty compatible)
    await new Promise<void>((resolve, reject) => {
      const url = new URL(webhookUrl);
      const opts = {
        hostname: url.hostname,
        path: url.pathname + url.search,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
      };
      const mod = url.protocol === 'https:' ? require('https') : require('http');
      const req = mod.request(opts, (res: any) => {
        res.on('data', () => {});
        res.on('end', () => resolve());
      });
      req.on('error', reject);
      req.write(body);
      req.end();
    });
  }
}

export const overrideQueue = new OverrideQueueService();
