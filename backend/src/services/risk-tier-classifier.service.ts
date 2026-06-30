import { calibrationConstitutionService } from './calibration-constitution.service';

export type GovernanceRiskTier = 'low' | 'medium' | 'high' | 'critical';

export interface RiskTierInput {
  changeType: string;
  affectedTables?: string[];
  affectedColumns?: string[];
  affectedPaths?: string[];
  operation?: string;
  touchesProductionRuntime?: boolean;
  requiresEval?: boolean;
}

export interface RiskTierClassification {
  riskTier: GovernanceRiskTier;
  requiresHumanReview: boolean;
  requiresConstitutionOverride: boolean;
  reasons: string[];
}

const RANK: Record<GovernanceRiskTier, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

function maxTier(current: GovernanceRiskTier, candidate: GovernanceRiskTier): GovernanceRiskTier {
  return RANK[candidate] > RANK[current] ? candidate : current;
}

export class RiskTierClassifierService {
  async classify(input: RiskTierInput): Promise<RiskTierClassification> {
    let riskTier: GovernanceRiskTier = 'low';
    const reasons: string[] = [];

    const operation = (input.operation || '').toLowerCase();
    if (operation.includes('delete') || operation.includes('drop')) {
      riskTier = maxTier(riskTier, 'high');
      reasons.push('destructive operation');
    }
    if (operation.includes('bypass') || operation.includes('override')) {
      riskTier = maxTier(riskTier, 'critical');
      reasons.push('bypass or override operation');
    }

    const paths = (input.affectedPaths || []).join('\n').toLowerCase();
    if (/secret|rbac|auth|permission|migration|schema|audit|resolver/.test(paths)) {
      riskTier = maxTier(riskTier, 'high');
      reasons.push('sensitive path touched');
    }

    if (input.touchesProductionRuntime) {
      riskTier = maxTier(riskTier, 'high');
      reasons.push('production runtime touched');
    }

    if (input.requiresEval) {
      riskTier = maxTier(riskTier, 'medium');
      reasons.push('evaluation required');
    }

    const constitution = await calibrationConstitutionService.validateChange(
      input.changeType,
      input.affectedTables || [],
      input.affectedColumns || []
    );
    if (!constitution.is_compliant) {
      riskTier = maxTier(riskTier, constitution.requires_override ? 'critical' : 'high');
      reasons.push(...constitution.violations);
    }

    return {
      riskTier,
      requiresHumanReview: riskTier === 'high' || riskTier === 'critical',
      requiresConstitutionOverride: constitution.requires_override || riskTier === 'critical',
      reasons,
    };
  }
}

export const riskTierClassifier = new RiskTierClassifierService();
