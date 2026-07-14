import { db } from '../db/client';
import { PublicHttpError } from '../http-errors';

/**
 * Policy enforcement (build phase C7).
 *
 * The single point the protected-action path consults for active governance
 * policies. Active runtime_policies match on action_type, domain, and a
 * minimum risk threshold; the most restrictive matching effect wins
 * (block > require_review > allow). This is what makes a governance policy
 * activation change real runtime behaviour and a rollback restore it.
 */

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
const RISK_RANK: Record<RiskLevel, number> = { low: 0, medium: 1, high: 2, critical: 3 };

export interface ActionContext {
  action_type: string;
  domain?: string | null;
  risk_level?: RiskLevel;
}

export interface PolicyDecision {
  decision: 'allow' | 'block' | 'require_review';
  matched_policy_id: string | null;
  policy_key: string | null;
  reason: string;
}

export class PolicyEnforcementService {
  async evaluate(ctx: ActionContext): Promise<PolicyDecision> {
    const risk = ctx.risk_level ?? 'low';
    const policies = await db.query<{
      id: string; policy_key: string; effect: 'block' | 'require_review' | 'allow';
      match_action_type: string | null; match_domain: string | null; match_min_risk: RiskLevel | null;
    }>(
      `SELECT id, policy_key, effect, match_action_type, match_domain, match_min_risk
         FROM runtime_policies
        WHERE status = 'active'
          AND (match_action_type IS NULL OR match_action_type = $1)
          AND (match_domain IS NULL OR match_domain = $2)`,
      [ctx.action_type, ctx.domain ?? null]
    );

    let decision: PolicyDecision = { decision: 'allow', matched_policy_id: null, policy_key: null, reason: 'no matching policy' };
    const rank = { allow: 0, require_review: 1, block: 2 };
    for (const p of policies.rows) {
      if (p.match_min_risk && RISK_RANK[risk] < RISK_RANK[p.match_min_risk]) continue;
      if (p.effect === 'allow') continue;
      if (decision.matched_policy_id === null || rank[p.effect] > rank[decision.decision]) {
        decision = {
          decision: p.effect,
          matched_policy_id: p.id,
          policy_key: p.policy_key,
          reason: `policy '${p.policy_key}' ${p.effect}s ${ctx.action_type}${ctx.domain ? ` in ${ctx.domain}` : ''} at risk >= ${p.match_min_risk ?? 'low'}`,
        };
      }
    }
    return decision;
  }

  /**
   * Fail-closed assertion for the protected-action path: throws when an active
   * policy blocks the action. `require_review` is surfaced to the caller (who
   * routes it to a human queue) rather than throwing.
   */
  async assertAllowed(ctx: ActionContext): Promise<PolicyDecision> {
    const decision = await this.evaluate(ctx);
    if (decision.decision === 'block') {
      throw new PublicHttpError(403, `blocked by governance policy: ${decision.reason}`);
    }
    return decision;
  }
}

export const policyEnforcement = new PolicyEnforcementService();
