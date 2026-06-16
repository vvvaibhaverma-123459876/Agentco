/**
 * Human Override Queue Service
 * Single authorised point of human intervention in AgentCo.
 * All high/critical risk actions pause here until a human approves or rejects.
 */

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
  config_change: 4,
  spend_approval: 2,
  strategic_pivot: 8,
  contract_flagged: 4,
  breach_suspected: 0.5,   // 30 minutes
  agent_upgrade: 8,
  rollback_failure: 0.25,  // 15 minutes
  novel_incident: 1,
  runway_alert: 2,
  critical_risk: 1,
  default: 4,
};

export class OverrideQueueService {
  async enqueue(
    agentId: string,
    action: string,
    riskLevel: 'high' | 'critical',
    context: Record<string, unknown>
  ): Promise<OverrideRequest> {
    const request_id = crypto.randomUUID();
    const created_at = new Date().toISOString();
    const sla_hours = SLA_HOURS[action] ?? SLA_HOURS['default'];
    const expires_at = new Date(Date.now() + sla_hours * 3600000).toISOString();

    const request: OverrideRequest = {
      request_id, agent_id: agentId, action, risk_score: context['risk_score'] as number ?? 0,
      risk_level: riskLevel, context, created_at, sla_hours, expires_at,
      status: 'pending',
    };

    // In production: await db.execute('INSERT INTO override_queue ...', request)
    // await sendAlert(request) — PagerDuty / Slack notification
    console.log(`[OVERRIDE] Queued: ${request_id} | Agent: ${agentId} | Action: ${action} | SLA: ${sla_hours}h`);

    return request;
  }

  async resolve(
    requestId: string,
    resolution: 'approved' | 'rejected',
    resolvedBy: string,
    notes?: string
  ): Promise<OverrideRequest & { approval_token?: string }> {
    // In production: await db.execute('UPDATE override_queue SET status=$1 ...', resolution, requestId)
    const approval_token = resolution === 'approved' ? crypto.randomUUID() : undefined;
    console.log(`[OVERRIDE] Resolved: ${requestId} | ${resolution} by ${resolvedBy}`);
    return { request_id: requestId } as any;
  }

  async listPending(filters?: { agent_id?: string; risk_level?: string }): Promise<OverrideRequest[]> {
    // In production: SELECT * FROM override_queue WHERE status='pending' ...
    return [];
  }

  async getOverdueSla(): Promise<OverrideRequest[]> {
    // In production: SELECT * FROM override_queue WHERE status='pending' AND expires_at < NOW()
    return [];
  }
}

export const overrideQueue = new OverrideQueueService();
