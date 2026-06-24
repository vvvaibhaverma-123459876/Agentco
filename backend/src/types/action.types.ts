/**
 * Autonomy Action Types
 * =====================
 * Typed contracts for autonomous decision-making and execution
 * Ensures decisions are structured and validated before execution
 */

export enum ActionType {
  // Research actions
  WEB_SEARCH = 'web_search',
  FETCH_PAGE = 'fetch_page',
  EXTRACT_EVIDENCE = 'extract_evidence',

  // Knowledge actions
  GENERATE_CLAIM = 'generate_claim',
  VALIDATE_CLAIM = 'validate_claim',
  UPDATE_MEMORY = 'update_memory',

  // Team actions
  SPAWN_SPECIALIST = 'spawn_specialist',
  COORDINATE_TEAM = 'coordinate_team',

  // Meta actions
  EVALUATE_PROGRESS = 'evaluate_progress',
  REPLAN = 'replan',
  TERMINATE = 'terminate',
}

export enum RiskLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
}

export interface ActionSpec {
  // Identity
  actionId: string;
  actionType: ActionType;
  planStepId?: string;
  goalId?: string;

  // Specification
  objective: string;                    // What this action intends to achieve
  args: Record<string, any>;           // Action-specific arguments
  expectedArtifacts?: string[];        // What this action should produce
  successCriteria: string[];           // How to verify success

  // Safety
  riskLevel: RiskLevel;
  fallback?: ActionType;               // What to do if this fails
  maxRetries?: number;
  timeoutMs?: number;

  // Traceability
  decidedBy: string;                   // 'planner', 'agent', 'human', etc.
  decidedAt: Date;
  reasoning?: string;                  // Why this action was chosen
}

export enum ActionStatus {
  PLANNED = 'planned',
  VALIDATED = 'validated',
  EXECUTING = 'executing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  BLOCKED = 'blocked',
}

export interface ActionResult {
  // Identity
  actionId: string;
  status: ActionStatus;

  // Execution
  startedAt: Date;
  completedAt?: Date;

  // Output
  observations: Record<string, any>;   // What was observed
  createdArtifacts: string[];          // IDs of created artifacts (evidence, claims, etc)

  // Error handling
  errors?: string[];
  blockedReason?: string;

  // Next steps
  nextStepHint?: string;               // Suggestion for what to do next

  // Traceability
  toolCalls: Array<{
    tool: string;
    args: Record<string, any>;
    result: any;
    error?: string;
  }>;
}

export interface Evidence {
  sourceId: string;
  url: string;
  title?: string;
  snippet?: string;
  retrievedAt: Date;
  contentHash: string;
  sourceType: 'web' | 'document' | 'analysis' | 'agent_output';
  isPublicAccess: boolean;
}

export interface Claim {
  claimId: string;
  text: string;
  status: 'draft' | 'unsupported' | 'weakly_supported' | 'supported' | 'contradicted';
  confidence: number;

  // Evidence backing
  supportSourceIds: string[];
  supportSnippets: string[];

  // Lineage
  derivedFromActionIds: string[];
  generatedAt: Date;
  generatedBy: string;

  // Contradiction tracking
  contradicts?: string[];
  contradictedBy?: string[];
}
