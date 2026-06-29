/**
 * Autonomy API Client
 *
 * Frontend integration with the backend autonomy services.
 * Provides methods to fetch and manage autonomy runs, tasks, candidates, and evals.
 */

const API_ROOT = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';
const API_BASE = `${API_ROOT.replace(/\/$/, '')}/api`;

export interface AutonomyRun {
  id: string;
  runId: string;
  status: string;
  traceId: string;
  taskId?: string;
  episodeId?: string;
  trajectoryIds: string[];
  replayBatchId?: string;
  learnerRunId?: string;
  candidateId?: string;
  evalRunId?: string;
  scorecardId?: string;
  promotionEligible: boolean;
  error?: string;
  startedAt: string;
  completedAt?: string;
}

export interface AutonomyTask {
  id: string;
  goalId: string;
  status: string;
  autonomyLevel: number;
  riskLevel: string;
  createdAt: string;
}

export interface LearnerCandidate {
  id: string;
  learnerRunId: string;
  candidateType: string;
  artifactId: string;
  artifactHash: string;
  metricsBeforeJson: Record<string, number>;
  metricsAfterJson: Record<string, number>;
  improvementPercent: number;
  status: string;
  createdAt: string;
}

export interface EvalScorecard {
  id: string;
  evalRunId: string;
  autonomyScore: number;
  safetyScore: number;
  calibrationScore: number;
  planningScore: number;
  memoryScore: number;
  learnerScore: number;
  regressionScore: number;
  overallScore: number;
  promotionEligible: boolean;
  reasoning: string;
  createdAt: string;
}

/**
 * Get autonomy run details
 */
export async function getAutonomyRun(runId: string): Promise<AutonomyRun> {
  const response = await fetch(`${API_BASE}/autonomy/runs/${runId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch autonomy run: ${response.statusText}`);
  }
  return response.json();
}

/**
 * List recent autonomy runs
 */
export async function listAutonomyRuns(limit: number = 10): Promise<AutonomyRun[]> {
  const response = await fetch(`${API_BASE}/autonomy/runs?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch autonomy runs: ${response.statusText}`);
  }
  const data = await response.json();
  return data.runs || [];
}

/**
 * Get autonomy task details
 */
export async function getAutonomyTask(taskId: string): Promise<AutonomyTask> {
  const response = await fetch(`${API_BASE}/autonomy/tasks/${taskId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch autonomy task: ${response.statusText}`);
  }
  return response.json();
}

/**
 * List autonomy tasks
 */
export async function listAutonomyTasks(limit: number = 20): Promise<AutonomyTask[]> {
  const response = await fetch(`${API_BASE}/autonomy/tasks?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch autonomy tasks: ${response.statusText}`);
  }
  const data = await response.json();
  return data.tasks || [];
}

/**
 * Get learner candidate details
 */
export async function getLearnerCandidate(candidateId: string): Promise<LearnerCandidate> {
  const response = await fetch(`${API_BASE}/autonomy/candidates/${candidateId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch candidate: ${response.statusText}`);
  }
  return response.json();
}

/**
 * List learner candidates
 */
export async function listLearnerCandidates(limit: number = 20): Promise<LearnerCandidate[]> {
  const response = await fetch(`${API_BASE}/autonomy/candidates?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch candidates: ${response.statusText}`);
  }
  const data = await response.json();
  return data.candidates || [];
}

/**
 * Get eval scorecard
 */
export async function getEvalScorecard(scorecardId: string): Promise<EvalScorecard> {
  const response = await fetch(`${API_BASE}/autonomy/evals/scorecards/${scorecardId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch scorecard: ${response.statusText}`);
  }
  return response.json();
}

/**
 * List eval scorecards
 */
export async function listEvalScorecards(limit: number = 20): Promise<EvalScorecard[]> {
  const response = await fetch(`${API_BASE}/autonomy/evals/scorecards?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch scorecards: ${response.statusText}`);
  }
  const data = await response.json();
  return data.scorecards || [];
}

/**
 * Get autonomy dashboard overview
 */
export async function getAutonomyDashboard(): Promise<{
  totalRuns: number;
  completedRuns: number;
  failedRuns: number;
  totalCandidates: number;
  promotionEligibleCount: number;
  avgPromotionScore: number;
  recentRuns: AutonomyRun[];
}> {
  const response = await fetch(`${API_BASE}/autonomy/dashboard/overview`);
  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard overview: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get trace/audit trail for a run
 */
export async function getAuditTrail(runId: string): Promise<Array<{
  id: string;
  eventType: string;
  entityType: string;
  status: string;
  timestamp: string;
  details: Record<string, any>;
}>> {
  const response = await fetch(`${API_BASE}/autonomy/audit?run_id=${runId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch audit trail: ${response.statusText}`);
  }
  const data = await response.json();
  return data.events || [];
}

/**
 * Get observability traces for a run
 */
export async function getTraces(runId: string): Promise<Array<{
  id: string;
  traceId: string;
  spanId?: string;
  operation: string;
  duration: number;
  status: string;
  timestamp: string;
}>> {
  const response = await fetch(`${API_BASE}/autonomy/observability/traces?run_id=${runId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch traces: ${response.statusText}`);
  }
  const data = await response.json();
  return data.traces || [];
}

/**
 * Health check - verify API is available
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, { method: 'GET' });
    return response.ok;
  } catch {
    return false;
  }
}
