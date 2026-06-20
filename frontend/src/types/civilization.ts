export type CapabilityLabel = 'Shipped' | 'Partially Implemented' | 'Experimental' | 'Future';
export type CivilizationStatus = 'active' | 'trial' | 'probation' | 'suspended' | 'retired';
export type AuthorityRisk = 'low' | 'medium' | 'high' | 'critical';

export interface CivilizationAgentNode {
  id: string;
  role: string;
  reputation: number;
  status: CivilizationStatus;
}

export interface CivilizationDepartmentNode {
  id: string;
  name: string;
  reputation: number;
  activeOutputs: number;
  agents: CivilizationAgentNode[];
}

export interface CivilizationInstitutionNode {
  id: string;
  name: string;
  status: CivilizationStatus;
  reputation: number;
  unresolvedDisputes: number;
  authorityScope: string[];
  riskLevel: AuthorityRisk;
  departments: CivilizationDepartmentNode[];
}

export interface CivilizationSocietyNode {
  id: string;
  name: string;
  status: CivilizationStatus;
  reputation: number;
  unresolvedDisputes: number;
  authorityScope: string[];
  institutions: CivilizationInstitutionNode[];
}

export interface CivilizationMap {
  id: string;
  name: string;
  status: CivilizationStatus;
  constitutionVersion: string;
  societies: CivilizationSocietyNode[];
}

export interface InstitutionDashboard {
  id: string;
  name: string;
  contract: string;
  status: CivilizationStatus;
  reputation: number;
  reputationHistory: Array<{ period: string; score: number }>;
  authorityScope: string[];
  restrictions: string[];
  departments: CivilizationDepartmentNode[];
  outputs: Array<{ id: string; title: string; status: string; risk: AuthorityRisk }>;
  reviews: Array<{ id: string; reviewerInstitution: string; finalDecision: string; challengeStatus: string }>;
  failures: Array<{ id: string; summary: string; status: string }>;
}

export interface ReviewDashboardItem {
  id: string;
  output: string;
  proposingInstitution: string;
  reviewerInstitution: string;
  challengeStatus: string;
  evidence: string[];
  finalDecision: string;
  linkedCalibrationClaims: string[];
}

export interface GovernanceDecisionItem {
  id: string;
  proposal: string;
  approver: string;
  affectedEntity: string;
  selfAuthorityCheck: 'passed' | 'blocked';
  auditTrail: string[];
  rollbackAvailable: boolean;
}

export interface MemoryDashboardItem {
  id: string;
  type: 'event' | 'lesson' | 'failure' | 'precedent' | 'pattern' | 'history';
  title: string;
  sourceEvent: string;
  affectedEntity: string;
}

export interface CalibrationDashboardItem {
  id: string;
  claim: string;
  claimSource: string;
  resolutionSource: string;
  independenceStatus: 'accepted' | 'rejected' | 'pending';
  trustScore: number;
  credentialStatus: string;
  auditPackage: string;
}
