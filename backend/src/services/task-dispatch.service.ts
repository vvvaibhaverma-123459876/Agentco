/**
 * Task Dispatch Service — Phase 5 feature
 * Manages async task queuing and agent task assignment
 * Stubs for type checking; real implementation deferred to Phase 4-5
 */

export interface Task {
  task_id: string;
  agent_id: string;
  task_type: string;
  payload: unknown;
  status: 'queued' | 'leased' | 'running' | 'completed' | 'failed' | 'cancelled';
  queued_at: string;
  retry_count: number;
  max_retries: number;
  correlation_id: string;
  lease_owner?: string;
}

export async function createTask(
  agentId: string,
  taskType: string,
  payload: unknown,
  options?: { correlationId?: string }
): Promise<Task> {
  throw new Error('Task dispatch not yet implemented. Phase 5 feature.');
}

export async function getTask(taskId: string): Promise<Task | null> {
  throw new Error('Task dispatch not yet implemented. Phase 5 feature.');
}

export async function listTasks(filter?: { agentId?: string; status?: string }): Promise<Task[]> {
  throw new Error('Task dispatch not yet implemented. Phase 5 feature.');
}

export async function cancelTask(taskId: string): Promise<Task | null> {
  throw new Error('Task dispatch not yet implemented. Phase 5 feature.');
}

export async function leaseOneTask(workerId: string): Promise<Task | null> {
  throw new Error('Task dispatch not yet implemented. Phase 5 feature.');
}

export async function markTaskRunning(taskId: string): Promise<Task | null> {
  throw new Error('Task dispatch not yet implemented. Phase 5 feature.');
}

export async function completeTask(taskId: string, result: unknown, auditId?: string): Promise<Task | null> {
  throw new Error('Task dispatch not yet implemented. Phase 5 feature.');
}

export async function failTask(taskId: string, error: string): Promise<Task | null> {
  throw new Error('Task dispatch not yet implemented. Phase 5 feature.');
}
