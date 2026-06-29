import { spawn } from 'child_process';
import { randomUUID } from 'crypto';
import { durableExecution, WorkflowTask } from '../services/durable-execution.service';

export interface TaskWorkerOptions {
  pollIntervalMs: number;
  subprocessTimeoutMs: number;
  maxOutputBytes: number;
  workerId: string;
  pythonExecutable: string;
  executorScript: string;
}

export interface WorkerExecutionResult {
  ok: boolean;
  exitCode: number | null;
  stdout: string;
  stderr: string;
  parsed?: unknown;
  error?: string;
  correlationId: string;
}

const DEFAULT_OPTIONS: TaskWorkerOptions = {
  pollIntervalMs: Number(process.env.AGENTCO_WORKER_POLL_MS || 1000),
  subprocessTimeoutMs: Number(process.env.AGENTCO_WORKER_TIMEOUT_MS || 30000),
  maxOutputBytes: Number(process.env.AGENTCO_WORKER_MAX_OUTPUT_BYTES || 32768),
  workerId: process.env.AGENTCO_WORKER_ID || `task-worker-${process.pid}`,
  pythonExecutable: process.env.AGENTCO_PYTHON || 'python3.13',
  executorScript: process.env.AGENTCO_DURABLE_EXECUTOR || 'scripts/execute_durable_task.py',
};

export class SupervisedTaskWorker {
  private stopping = false;

  constructor(private options: TaskWorkerOptions = DEFAULT_OPTIONS) {}

  stop(): void {
    this.stopping = true;
  }

  async runOnce(): Promise<WorkerExecutionResult | null> {
    const task = await this.nextQueuedTask();
    if (!task) return null;
    return this.executeTask(task);
  }

  async loop(): Promise<void> {
    process.on('SIGTERM', () => this.stop());
    process.on('SIGINT', () => this.stop());
    while (!this.stopping) {
      await this.runOnce();
      await sleep(this.options.pollIntervalMs);
    }
  }

  async executeTask(task: WorkflowTask): Promise<WorkerExecutionResult> {
    const correlationId = task.task_id || randomUUID();
    const result = await runSubprocess(
      this.options.pythonExecutable,
      [this.options.executorScript, task.task_id],
      this.options.subprocessTimeoutMs,
      this.options.maxOutputBytes,
      correlationId,
    );
    return result;
  }

  private async nextQueuedTask(): Promise<WorkflowTask | null> {
    const queued = (await durableExecution.list()).find(task => task.status === 'queued');
    return queued ?? null;
  }
}

export function runSubprocess(
  command: string,
  args: string[],
  timeoutMs: number,
  maxOutputBytes: number,
  correlationId: string,
): Promise<WorkerExecutionResult> {
  return new Promise(resolve => {
    const child = spawn(command, args, {
      cwd: process.cwd().endsWith('/backend') ? '..' : process.cwd(),
      env: { ...process.env, AGENTCO_CORRELATION_ID: correlationId },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let settled = false;
    const append = (current: string, chunk: Buffer) => (current + chunk.toString('utf8')).slice(-maxOutputBytes);
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill('SIGTERM');
      resolve({
        ok: false,
        exitCode: null,
        stdout,
        stderr,
        error: `task executor timed out after ${timeoutMs}ms`,
        correlationId,
      });
    }, timeoutMs);

    child.stdout?.on('data', chunk => {
      stdout = append(stdout, chunk);
    });
    child.stderr?.on('data', chunk => {
      stderr = append(stderr, chunk);
    });
    child.on('error', error => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ ok: false, exitCode: null, stdout, stderr, error: error.message, correlationId });
    });
    child.on('close', code => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      let parsed: unknown;
      let parseError: string | undefined;
      if (stdout.trim()) {
        try {
          parsed = JSON.parse(stdout.trim().split(/\n/).at(-1) || '{}');
        } catch (error) {
          parseError = `malformed executor JSON output: ${error instanceof Error ? error.message : String(error)}`;
        }
      }
      resolve({
        ok: code === 0 && !parseError,
        exitCode: code,
        stdout,
        stderr,
        parsed,
        error: parseError,
        correlationId,
      });
    });
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

if (require.main === module) {
  new SupervisedTaskWorker().loop().catch(error => {
    console.error('[task-worker] fatal error', error);
    process.exit(1);
  });
}
