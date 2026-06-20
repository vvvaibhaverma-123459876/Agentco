import type {
  CalibrationDashboardItem,
  CapabilityLabel,
  CivilizationMap,
  GovernanceDecisionItem,
  InstitutionDashboard,
  MemoryDashboardItem,
  ReviewDashboardItem,
} from '@/types/civilization';

const engineeringInstitution: InstitutionDashboard = {
  id: 'inst-software-engineering',
  name: 'Software Engineering Institution',
  contract: 'Build and review software artifacts inside delegated engineering jurisdiction.',
  status: 'active',
  reputation: 0.81,
  reputationHistory: [
    { period: 'Q1', score: 0.72 },
    { period: 'Q2', score: 0.78 },
    { period: 'Q3', score: 0.81 },
  ],
  authorityScope: ['software_artifact:create', 'engineering_review:request'],
  restrictions: ['Security approval requires Security Institution review', 'High-risk release blocked by critical disputes'],
  departments: [
    {
      id: 'dept-platform',
      name: 'Platform Department',
      reputation: 0.84,
      activeOutputs: 3,
      agents: [
        { id: 'agent-platform-01', role: 'engineer', reputation: 0.82, status: 'active' },
        { id: 'agent-platform-02', role: 'reviewer', reputation: 0.79, status: 'trial' },
      ],
    },
    {
      id: 'dept-verification',
      name: 'Verification Department',
      reputation: 0.88,
      activeOutputs: 2,
      agents: [
        { id: 'agent-verify-01', role: 'calibration liaison', reputation: 0.91, status: 'active' },
      ],
    },
  ],
  outputs: [
    { id: 'out-api-001', title: 'Governed institution API', status: 'approved', risk: 'medium' },
    { id: 'out-jur-004', title: 'Jurisdiction guard integration', status: 'under_review', risk: 'high' },
  ],
  reviews: [
    {
      id: 'rev-sec-018',
      reviewerInstitution: 'Security Institution',
      finalDecision: 'approved_with_constraints',
      challengeStatus: 'resolved',
    },
  ],
  failures: [
    { id: 'fail-012', summary: 'Late evidence snapshot on release candidate review', status: 'lesson_extracted' },
  ],
};

const civilizationMap: CivilizationMap = {
  id: 'civ-agentco',
  name: 'Agentco Civilization',
  status: 'active',
  constitutionVersion: 'v0.1-draft',
  societies: [
    {
      id: 'soc-engineering',
      name: 'Engineering Society',
      status: 'active',
      reputation: 0.8,
      unresolvedDisputes: 1,
      authorityScope: ['software standards', 'inter-institution engineering review'],
      institutions: [
        {
          ...engineeringInstitution,
          unresolvedDisputes: 1,
          riskLevel: 'medium',
        },
        {
          id: 'inst-security',
          name: 'Security Institution',
          status: 'active',
          reputation: 0.86,
          unresolvedDisputes: 0,
          authorityScope: ['security_review:approve', 'vulnerability_response:coordinate'],
          riskLevel: 'high',
          departments: [
            {
              id: 'dept-appsec',
              name: 'Application Security Department',
              reputation: 0.87,
              activeOutputs: 1,
              agents: [{ id: 'agent-security-01', role: 'human_reviewer', reputation: 0.89, status: 'active' }],
            },
          ],
        },
      ],
    },
    {
      id: 'soc-governance',
      name: 'Governance Society',
      status: 'trial',
      reputation: 0.74,
      unresolvedDisputes: 0,
      authorityScope: ['constitutional process', 'cross-society coordination'],
      institutions: [],
    },
  ],
};

const reviews: ReviewDashboardItem[] = [
  {
    id: 'rev-sec-018',
    output: 'Governed institution API',
    proposingInstitution: 'Software Engineering Institution',
    reviewerInstitution: 'Security Institution',
    challengeStatus: 'resolved',
    evidence: ['independent-source-lineage', 'audit-mutation-log', 'rbac-route-test'],
    finalDecision: 'approved_with_constraints',
    linkedCalibrationClaims: ['claim-api-auth-001', 'claim-idempotency-002'],
  },
  {
    id: 'rev-rel-021',
    output: 'Civilization memory lineage',
    proposingInstitution: 'Memory Institution',
    reviewerInstitution: 'Reliability Institution',
    challengeStatus: 'open',
    evidence: ['migration-012', 'memory-summary-source-link'],
    finalDecision: 'pending',
    linkedCalibrationClaims: ['claim-memory-trace-004'],
  },
];

const governance: GovernanceDecisionItem[] = [
  {
    id: 'gov-admit-eng-001',
    proposal: 'Admit Software Engineering Institution to Engineering Society',
    approver: 'Engineering Society Governance Council',
    affectedEntity: 'Software Engineering Institution',
    selfAuthorityCheck: 'passed',
    auditTrail: ['governance_decision', 'institution_admitted', 'society_memory_recorded'],
    rollbackAvailable: true,
  },
  {
    id: 'gov-self-expand-002',
    proposal: 'Security Institution expands own release authority',
    approver: 'Security Institution',
    affectedEntity: 'Security Institution',
    selfAuthorityCheck: 'blocked',
    auditTrail: ['governance_decision_rejected', 'self_authority_blocked'],
    rollbackAvailable: false,
  },
];

const memory: MemoryDashboardItem[] = [
  {
    id: 'mem-precedent-001',
    type: 'precedent',
    title: 'Same-source resolution cannot update trust',
    sourceEvent: 'ruling-claim-independence-001',
    affectedEntity: 'Calibration Reserve',
  },
  {
    id: 'mem-lesson-004',
    type: 'lesson',
    title: 'Repeated missing lineage requires release hold',
    sourceEvent: 'pattern-missing-lineage-q3',
    affectedEntity: 'Software Engineering Institution',
  },
  {
    id: 'mem-history-007',
    type: 'history',
    title: 'Platform Department trial authority activated',
    sourceEvent: 'lifecycle-trial-activation-003',
    affectedEntity: 'Platform Department',
  },
];

const calibration: CalibrationDashboardItem[] = [
  {
    id: 'claim-api-auth-001',
    claim: 'Governed API rejects unauthenticated institution mutation',
    claimSource: 'agentco-ledger://prediction/claim-api-auth-001',
    resolutionSource: 'https://independent.example.org/audit/api-auth',
    independenceStatus: 'accepted',
    trustScore: 0.82,
    credentialStatus: 'Proof-of-Calibration issued',
    auditPackage: 'audit://calibration/claim-api-auth-001',
  },
  {
    id: 'claim-same-source-003',
    claim: 'Tracking-param URL is independent evidence',
    claimSource: 'https://producer.example.org/post?id=7&utm=agent',
    resolutionSource: 'https://producer.example.org/post?id=7',
    independenceStatus: 'rejected',
    trustScore: 0,
    credentialStatus: 'blocked',
    auditPackage: 'audit://calibration/claim-same-source-003',
  },
];

export const capabilityLabels: Array<{ label: CapabilityLabel; description: string }> = [
  { label: 'Shipped', description: 'Backed by executable code, tests, documentation, and current branch implementation.' },
  { label: 'Partially Implemented', description: 'Core path exists but integrations or durability are incomplete.' },
  { label: 'Experimental', description: 'Dashboard-visible prototype or deterministic mock surface.' },
  { label: 'Future', description: 'Roadmap item that must not be marketed as shipped.' },
];

export const civilizationApi = {
  getMap: async () => civilizationMap,
  getInstitution: async () => engineeringInstitution,
  getReviews: async () => reviews,
  getGovernance: async () => governance,
  getMemory: async () => memory,
  getCalibration: async () => calibration,
};
