import crypto from 'crypto';
import { execFile } from 'child_process';
import path from 'path';
import { auditLog } from '../services/audit-log.service';
import { eventBus } from '../services/event-bus.service';
import {
  completeTask,
  failTask,
  leaseOneTask,
  markTaskRunning,
} from '../services/task-dispatch.service';

function repoRoot(): string {
  return path.resolve(__dirname, '..', '..', '..');
}

async function executeTaskPython(taskId: string): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const root = repoRoot();
    execFile('python3', ['scripts/execute_durable_task.py', taskId], { cwd: root, env: process.env }, (error, stdout, stderr) => {
      if (error) {
        const message = stderr?.trim() || error.message;
        reject(new Error(message));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (parseError) {
        reject(new Error(`task execution returned non-JSON output: ${String(parseError)}`));
      }
    });
  });
}

export async function processOneTask(workerId = `worker-${process.pid}`): Promise<string | null> {
  const task = await leaseOneTask(workerId);
  if (!task) return null;
  await markTaskRunning(task.task_id);

  try {
    const executionResult = await executeTaskPython(task.task_id);
    const result = {
      task_id: task.task_id,
      agent_id: task.agent_id,
      task_type: task.task_type,
      executor_mode: 'python_runtime',
      execution_result: executionResult,
      executed_at: new Date().toISOString(),
    };
    const auditId = await auditLog.append({
      agent_id: task.agent_id,
      action_type: 'decision',
      input_summary: JSON.stringify({ task_type: task.task_type, payload: task.payload }).slice(0, 500),
      output_summary: JSON.stringify(executionResult).slice(0, 500),
      confidence_score: 0.6,
      risk_level: 'medium',
      session_id: task.task_id,
    });
    await eventBus.publish({
      event_id: crypto.randomUUID(),
      event_type: `${task.agent_id}.task_completed`,
      producer_agent_id: task.agent_id,
      timestamp: new Date().toISOString(),
      confidence_score: 0.6,
      payload: { task_id: task.task_id, task_type: task.task_type, executor_mode: 'python_runtime', status: executionResult.status, audit_id: auditId },
      correlation_id: task.correlation_id ?? task.task_id,
      risk_level: 'medium',
      requires_ack: false,
    });
    await completeTask(task.task_id, result, auditId);
    return task.task_id;
  } catch (error) {
    await failTask(task.task_id, error instanceof Error ? error.message : String(error));
    return task.task_id;
  }
}

if (require.main === module) {
  processOneTask()
    .then((taskId) => {
      console.log(JSON.stringify({ processed_task_id: taskId }));
      process.exit(0);
    })
    .catch((error) => {
      console.error(error);
      process.exit(1);
    });
}
