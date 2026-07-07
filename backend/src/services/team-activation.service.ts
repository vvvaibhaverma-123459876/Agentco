/**
 * Team Activation Service
 * ======================
 * Manages specialist agent instantiation, budget enforcement, and lifecycle.
 * Spawns bounded agents with resource limits and aggregates results back to parent.
 */

import { v4 as uuidv4 } from 'uuid';
import { spawn, ChildProcess } from 'child_process';
import { createWriteStream } from 'fs';
import path from 'path';
import net from 'net';
import { createHmac } from 'crypto';
import { isProductionEnv } from '../security';
import { db } from '../db/client';
import { getSpecialistRole, isValidSpecialistRole } from '../types/specialist-roles';
import { ActionSpec, ActionResult } from '../types/action.types';
import { metricsService } from './autonomy-metrics.service';
import { structuredLogger } from './structured-logger.service';

export interface SpecialistBudget {
  tokens: number;
  iterations: number;
  seconds: number;
}

export interface SpecialistActivationRequest {
  parentGoalId: string;
  role: string;
  objective: string;
  customBudget?: SpecialistBudget;
}

export interface SpecialistInstance {
  specialistId: string;
  role: string;
  parentGoalId: string;
  objective: string;
  budget: SpecialistBudget;
  startedAt: Date;
  tokensBudget: number;
  tokensUsed: number;
  iterationsBudget: number;
  iterationsUsed: number;
  secondsBudget: number;
  httpEndpoint?: string;
  processId?: number;
  portNumber?: number;
}

export interface ActivationResult {
  activationId: string;
  specialistId: string;
  role: string;
  status: string;
  artifacts: string[];
  evidence: string[];
  claims: string[];
  completedAt?: Date;
  error?: string;
}

export class TeamActivationService {
  private activeSpecialists = new Map<string, SpecialistInstance>();
  private activeProcesses = new Map<string, ChildProcess>();

  constructor() {
    // Graceful shutdown handlers to prevent orphaned processes
    process.on('SIGTERM', () => {
      structuredLogger.logProcessEvent('signal', 'SIGTERM received, initiating graceful shutdown');
      this.gracefulShutdown().catch((err) => {
        structuredLogger.logProcessEvent('error', `Error during SIGTERM shutdown: ${err.message}`);
        process.exit(1);
      });
    });

    process.on('SIGINT', () => {
      structuredLogger.logProcessEvent('signal', 'SIGINT received, initiating graceful shutdown');
      this.gracefulShutdown().catch((err) => {
        structuredLogger.logProcessEvent('error', `Error during SIGINT shutdown: ${err.message}`);
        process.exit(1);
      });
    });
  }

  /**
   * Graceful shutdown: terminate all specialists and their processes
   */
  private async gracefulShutdown(): Promise<void> {
    const timeout = 10000; // 10 seconds total timeout
    const startTime = Date.now();

    structuredLogger.logProcessEvent('signal', `Starting graceful shutdown of ${this.activeProcesses.size} active specialists`);

    // Step 1: Signal all specialists to terminate gracefully (SIGTERM)
    for (const [specialistId, childProcess] of this.activeProcesses) {
      try {
        if (!childProcess.killed) {
          childProcess.kill('SIGTERM');
          structuredLogger.log('info', 'Sent SIGTERM to specialist', {
            specialistId,
            pid: childProcess.pid,
          });
        }
      } catch (err: any) {
        structuredLogger.log('warn', 'Failed to send SIGTERM to specialist', {
          specialistId,
          error: err.message,
        });
      }
    }

    // Step 2: Wait for graceful termination
    while (this.activeProcesses.size > 0 && Date.now() - startTime < timeout) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    // Step 3: Force kill any remaining processes (SIGKILL)
    for (const [specialistId, childProcess] of this.activeProcesses) {
      if (!childProcess.killed) {
        try {
          childProcess.kill('SIGKILL');
          structuredLogger.log('warn', 'Force-killed specialist', {
            specialistId,
            pid: childProcess.pid,
          });
        } catch (err: any) {
          structuredLogger.log('error', 'Failed to SIGKILL specialist', {
            specialistId,
            error: err.message,
          });
        }
      }
    }

    // Step 4: Update database records for any remaining specialists
    for (const [specialistId] of this.activeSpecialists) {
      try {
        await this.terminateSpecialist(specialistId, {
          artifacts: [],
          evidence: [],
          claims: [],
          error: 'Process killed during server shutdown',
        });
      } catch (err: any) {
        structuredLogger.log('error', 'Error terminating specialist in shutdown', {
          specialistId,
          error: err.message,
        });
      }
    }

    structuredLogger.logProcessEvent('stopped', 'Graceful shutdown complete');
  }

  async shutdown(): Promise<void> {
    await this.gracefulShutdown();
  }

  /**
   * Activate a specialist agent with bounded resources
   */
  async activateSpecialist(
    request: SpecialistActivationRequest
  ): Promise<SpecialistInstance | null> {
    // Validate role
    if (!isValidSpecialistRole(request.role)) {
      console.error(`Invalid specialist role: ${request.role}`);
      return null;
    }

    const roleSpec = getSpecialistRole(request.role);
    if (!roleSpec) {
      return null;
    }

    // Check parent goal depth limit (max depth 2)
    const parentDepth = await this.getGoalDepth(request.parentGoalId);
    if (parentDepth >= 2) {
      console.warn(`Cannot activate specialist: parent goal depth ${parentDepth} exceeds limit 2`);
      return null;
    }

    // Check concurrent specialist limit (max 3 per parent)
    const activeCount = await this.getActiveSpecialistCount(request.parentGoalId);
    if (activeCount >= 3) {
      console.warn(`Cannot activate specialist: parent already has ${activeCount} active specialists (limit 3)`);
      return null;
    }

    // Create specialist instance
    const specialistId = uuidv4();
    const budget = request.customBudget || roleSpec.defaultBudgets;
    const portNumber = await this.findAvailablePort();
    const httpEndpoint = `http://127.0.0.1:${portNumber}`;

    const specialist: SpecialistInstance = {
      specialistId,
      role: request.role,
      parentGoalId: request.parentGoalId,
      objective: request.objective,
      budget,
      startedAt: new Date(),
      tokensBudget: budget.tokens,
      tokensUsed: 0,
      iterationsBudget: budget.iterations,
      iterationsUsed: 0,
      secondsBudget: budget.seconds,
      httpEndpoint,
      portNumber,
    };

    // Spawn Python subprocess
    const childProcess = this.spawnSpecialistProcess(specialistId, request.role, portNumber, budget);
    if (!childProcess) {
      console.error(`[TeamActivation] Failed to spawn subprocess for specialist ${specialistId}`);
      return null;
    }

    // Wait for HTTP server to be ready (max 5 seconds)
    const ready = await this.waitForSpecialistReady(httpEndpoint, 5000);
    if (!ready) {
      console.error(`[TeamActivation] Specialist HTTP server not ready at ${httpEndpoint}`);
      childProcess.kill();
      metricsService.recordSpecialistSpawn(request.role, false);
      return null;
    }

    specialist.processId = childProcess.pid;
    metricsService.recordSpecialistSpawn(request.role, true);

    // Store in database
    await db.query(
      `INSERT INTO autonomy_team_activations (
        id, parent_goal_id, specialist_id, specialist_role, objective,
        budget_tokens, budget_iterations, budget_seconds, status,
        http_endpoint, process_pid, port_number
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
      [
        uuidv4(),
        request.parentGoalId,
        specialistId,
        request.role,
        request.objective,
        budget.tokens,
        budget.iterations,
        budget.seconds,
        'active',
        httpEndpoint,
        childProcess.pid,
        portNumber,
      ]
    );

    // Track in memory
    this.activeSpecialists.set(specialistId, specialist);
    this.activeProcesses.set(specialistId, childProcess);

    // Handle process termination
    childProcess.on('exit', (code) => {
      structuredLogger.log('info', 'Specialist process exited', {
        specialistId,
        role: request.role,
        exitCode: code,
      });
      this.activeProcesses.delete(specialistId);
    });

    // Log specialist spawn
    structuredLogger.logSpecialistSpawn(specialistId, request.role, {
      goalId: request.parentGoalId,
      pid: childProcess.pid,
      port: portNumber,
      httpEndpoint,
    });

    return specialist;
  }

  /**
   * Record token usage for a specialist
   */
  async recordTokenUsage(specialistId: string, tokensUsed: number): Promise<void> {
    const specialist = this.activeSpecialists.get(specialistId);
    if (!specialist) {
      return;
    }

    specialist.tokensUsed += tokensUsed;

    await db.query(
      `UPDATE autonomy_team_activations SET tokens_used = $1 WHERE specialist_id = $2`,
      [specialist.tokensUsed, specialistId]
    );
  }

  /**
   * Record iteration usage for a specialist
   */
  async recordIterationUsage(specialistId: string): Promise<void> {
    const specialist = this.activeSpecialists.get(specialistId);
    if (!specialist) {
      return;
    }

    specialist.iterationsUsed += 1;

    await db.query(
      `UPDATE autonomy_team_activations SET iterations_used = $1 WHERE specialist_id = $2`,
      [specialist.iterationsUsed, specialistId]
    );
  }

  /**
   * Check if specialist has exceeded budget
   */
  isBudgetExceeded(specialistId: string): {
    exceeded: boolean;
    reason?: string;
  } {
    const specialist = this.activeSpecialists.get(specialistId);
    if (!specialist) {
      return { exceeded: false };
    }

    if (specialist.tokensUsed > specialist.tokensBudget) {
      return { exceeded: true, reason: `Token budget exceeded: ${specialist.tokensUsed}/${specialist.tokensBudget}` };
    }

    if (specialist.iterationsUsed > specialist.iterationsBudget) {
      return { exceeded: true, reason: `Iteration budget exceeded: ${specialist.iterationsUsed}/${specialist.iterationsBudget}` };
    }

    const elapsedSeconds = (Date.now() - specialist.startedAt.getTime()) / 1000;
    if (elapsedSeconds > specialist.secondsBudget) {
      return { exceeded: true, reason: `Time budget exceeded: ${elapsedSeconds.toFixed(1)}s/${specialist.secondsBudget}s` };
    }

    return { exceeded: false };
  }

  /**
   * Terminate a specialist and record results
   */
  async terminateSpecialist(
    specialistId: string,
    results: {
      artifacts: string[];
      evidence: string[];
      claims: string[];
      error?: string;
    }
  ): Promise<void> {
    const specialist = this.activeSpecialists.get(specialistId);
    if (!specialist) {
      return;
    }

    const completedAt = new Date();
    const status = results.error ? 'failed' : 'completed';

    // Kill subprocess if still running
    const childProcess = this.activeProcesses.get(specialistId);
    if (childProcess && !childProcess.killed) {
      try {
        childProcess.kill('SIGTERM');
        console.log(`[TeamActivation] Sent SIGTERM to specialist ${specialistId} (PID: ${childProcess.pid})`);

        // Wait up to 2 seconds for graceful shutdown
        await new Promise((resolve) => {
          setTimeout(() => {
            // If still running, force kill with SIGKILL
            if (!childProcess.killed) {
              try {
                childProcess.kill('SIGKILL');
                console.warn(`[TeamActivation] Force-killed specialist ${specialistId} (PID: ${childProcess.pid})`);
              } catch (err) {
                console.warn(`[TeamActivation] Error force-killing specialist ${specialistId}:`, err);
              }
            }
            resolve(undefined);
          }, 2000);
        });
      } catch (err) {
        console.error(`[TeamActivation] Error killing process for specialist ${specialistId}:`, err);
      }
    }

    // Update database
    try {
      await db.query(
        `UPDATE autonomy_team_activations SET
          status = $1, completed_at = $2, results = $3
         WHERE specialist_id = $4`,
        [
          status,
          completedAt,
          JSON.stringify(results),
          specialistId,
        ]
      );
    } catch (err) {
      console.error(`[TeamActivation] Error updating database for specialist ${specialistId}:`, err);
    }

    // Cleanup in-memory tracking
    this.activeSpecialists.delete(specialistId);
    this.activeProcesses.delete(specialistId);
    console.log(`[TeamActivation] Terminated specialist ${specialistId} (status: ${status})`);
  }

  /**
   * Get active specialist count for a parent goal
   */
  private async getActiveSpecialistCount(parentGoalId: string): Promise<number> {
    const result = await db.query(
      `SELECT COUNT(*) as count FROM autonomy_team_activations
       WHERE parent_goal_id = $1 AND status = 'active'`,
      [parentGoalId]
    );
    return parseInt(result.rows[0]?.count || 0);
  }

  /**
   * Get goal depth (how many parent goals up the chain)
   * Depth 0 = root goal, Depth 1 = spawned by root, Depth 2 = spawned by level-1
   */
  private async getGoalDepth(goalId: string): Promise<number> {
    const result = await db.query(
      `SELECT depth FROM autonomy_goals WHERE id = $1`,
      [goalId]
    );
    const depth = parseInt(result.rows[0]?.depth || 0);
    return depth;
  }

  /**
   * Get a specialist instance
   */
  getSpecialist(specialistId: string): SpecialistInstance | undefined {
    return this.activeSpecialists.get(specialistId);
  }

  /**
   * Get all active specialists for a parent goal
   */
  async getActiveSpecialists(parentGoalId: string): Promise<SpecialistInstance[]> {
    const result = await db.query(
      `SELECT specialist_id FROM autonomy_team_activations
       WHERE parent_goal_id = $1 AND status = 'active'`,
      [parentGoalId]
    );

    const specialists: SpecialistInstance[] = [];
    for (const row of result.rows) {
      const specialist = this.activeSpecialists.get(row.specialist_id);
      if (specialist) {
        specialists.push(specialist);
      }
    }
    return specialists;
  }

  /**
   * Sign request with HMAC-SHA256
   */
  private signRequest(payload: object): {
    signature: string;
    timestamp: string;
  } {
    const secret = process.env.SPECIALIST_SHARED_SECRET;
    if (!secret || secret === 'default-insecure-secret') {
      if (isProductionEnv()) {
        throw new Error('SPECIALIST_SHARED_SECRET must be configured with a non-default value in staging/production');
      }
    }
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const payloadStr = JSON.stringify(payload);
    const message = payloadStr + ':' + timestamp;

    const signature = createHmac('sha256', secret || 'development-only-specialist-secret')
      .update(message)
      .digest('hex');

    return { signature, timestamp };
  }

  /**
   * Execute action via specialist HTTP endpoint with HMAC signature and metrics
   */
  async executeActionViaSpecialist(
    specialistId: string,
    actionSpec: ActionSpec
  ): Promise<ActionResult | null> {
    const specialist = this.activeSpecialists.get(specialistId);
    if (!specialist || !specialist.httpEndpoint) {
      structuredLogger.logSpecialistError(
        specialistId,
        'not_found',
        'Specialist not found or HTTP endpoint not available'
      );
      metricsService.recordSpecialistError(specialist?.role || 'unknown', 'not_found');
      return null;
    }

    const startTime = Date.now();

    try {
      // Log action start
      structuredLogger.logSpecialistAction(specialistId, actionSpec.actionType, 'started', {
        goalId: actionSpec.goalId,
        objective: actionSpec.objective,
      });

      // Create abort controller for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), specialist.secondsBudget * 1000);

      // Sign the request
      const { signature, timestamp } = this.signRequest(actionSpec);
      const payload = JSON.stringify(actionSpec);

      // Call specialist HTTP endpoint with HMAC signature
      const response = await fetch(`${specialist.httpEndpoint}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Signature': signature,
          'X-Timestamp': timestamp,
        },
        body: payload,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Record response time
      const responseTime = (Date.now() - startTime) / 1000;
      metricsService.recordResponseTime(specialist.role, '/execute', responseTime);

      if (!response.ok) {
        if (response.status === 401) {
          structuredLogger.logAuthenticationEvent('signature_invalid', {
            specialistId,
            role: specialist.role,
          });
          metricsService.recordSpecialistError(specialist.role, 'auth_failed');
        } else if (response.status === 429) {
          structuredLogger.logBudgetExceeded(
            specialistId,
            'tokens',
            specialist.tokensUsed,
            specialist.tokensBudget,
            { role: specialist.role }
          );
          metricsService.recordSpecialistError(specialist.role, 'budget_exceeded');
        } else {
          structuredLogger.logSpecialistError(
            specialistId,
            `http_${response.status}`,
            `Specialist HTTP error: ${response.status}`
          );
          metricsService.recordSpecialistError(specialist.role, `http_${response.status}`);
        }
        return null;
      }

      const result = (await response.json()) as any;

      // Record token usage
      await this.recordTokenUsage(specialistId, result.tokens_used || 0);
      metricsService.updateTokenUsage(specialistId, specialist.role, specialist.tokensUsed);

      await this.recordIterationUsage(specialistId);

      // Record action metrics
      const executionTime = (Date.now() - startTime) / 1000;
      metricsService.recordSpecialistAction(
        specialist.role,
        actionSpec.actionType,
        'success',
        executionTime
      );

      // Log action completion
      structuredLogger.logSpecialistAction(specialistId, actionSpec.actionType, 'completed', {
        durationSeconds: executionTime,
        tokensUsed: result.tokens_used || 0,
        observations: result.observations,
      });

      return {
        actionId: actionSpec.actionId,
        status: result.status || 'completed',
        startedAt: new Date(),
        completedAt: new Date(),
        observations: result.observations || {},
        createdArtifacts: result.artifacts || [],
        toolCalls: [],
      };
    } catch (error: any) {
      const duration = (Date.now() - startTime) / 1000;

      if (error.name === 'AbortError') {
        structuredLogger.logSpecialistAction(specialistId, actionSpec.actionType, 'timeout', {
          durationSeconds: duration,
          budgetSeconds: specialist.secondsBudget,
        });
        metricsService.recordSpecialistAction(
          specialist.role,
          actionSpec.actionType,
          'timeout',
          duration
        );
      } else {
        structuredLogger.logSpecialistError(
          specialistId,
          error.name || 'unknown',
          `Specialist HTTP execution failed: ${error.message}`
        );
        metricsService.recordSpecialistError(specialist.role, error.name || 'unknown');
      }

      return null;
    }
  }

  /**
   * Aggregate results from specialist back to parent goal
   */
  async aggregateResults(
    parentGoalId: string,
    specialistResults: ActivationResult
  ): Promise<void> {
    // Store artifacts as evidence in parent goal context
    for (const artifactId of specialistResults.artifacts) {
      // Link artifact to parent goal
      await db.query(
        `UPDATE autonomy_evidence SET goal_id = $1 WHERE id = $2`,
        [parentGoalId, artifactId]
      );
    }

    // Link claims to parent goal
    for (const claimId of specialistResults.claims) {
      await db.query(
        `UPDATE autonomy_claims SET goal_id = $1 WHERE id = $2`,
        [parentGoalId, claimId]
      );
    }

    console.log(`[TeamActivation] Aggregated ${specialistResults.artifacts.length} artifacts and ${specialistResults.claims.length} claims to parent goal ${parentGoalId}`);
  }

  /**
   * Spawn a Python specialist subprocess with file logging
   */
  private spawnSpecialistProcess(
    specialistId: string,
    role: string,
    port: number,
    budget: SpecialistBudget
  ): ChildProcess | null {
    try {
      const args = [
        '-m', `agents.autonomy.${role}`,
        '--specialist-id', specialistId,
        '--port', port.toString(),
        '--role', role,
        '--budget', JSON.stringify(budget),
      ];

      const repoRoot = path.resolve(__dirname, '../../..');
      const pythonExecutable = process.env.AGENTCO_PYTHON || 'python3.13';
      const pythonPath = process.env.PYTHONPATH
        ? `${repoRoot}:${process.env.PYTHONPATH}`
        : repoRoot;

      const childProcess = spawn(pythonExecutable, args, {
        cwd: repoRoot,
        detached: false,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: {
          ...process.env,
          PYTHONPATH: pythonPath,
          SPECIALIST_ID: specialistId,
          SPECIALIST_ROLE: role,
        },
      });

      // Create log file stream for this specialist
      const logFilePath = `/tmp/specialist_${specialistId}.log`;
      const logStream = createWriteStream(logFilePath, { flags: 'a' });

      const getTimestamp = () => new Date().toISOString();

      // Capture and log stdout
      childProcess.stdout?.on('data', (data) => {
        const message = data.toString().trim();
        const logLine = `[${getTimestamp()}] [INFO] ${message}\n`;
        logStream.write(logLine);
        console.log(`[Specialist ${specialistId}] ${message}`);
      });

      // Capture and log stderr with alert detection
      childProcess.stderr?.on('data', (data) => {
        const message = data.toString().trim();
        const logLine = `[${getTimestamp()}] [ERROR] ${message}\n`;
        logStream.write(logLine);
        console.error(`[Specialist ${specialistId}] ERROR: ${message}`);

        // Alert on critical errors
        if (message.toLowerCase().includes('exception') ||
            message.toLowerCase().includes('failed') ||
            message.toLowerCase().includes('error')) {
          console.error(`[ALERT] Specialist error detected in ${specialistId}: ${message}`);
          logStream.write(`[${getTimestamp()}] [ALERT] Critical error: ${message}\n`);
        }
      });

      // Log process exit
      childProcess.on('exit', (code, signal) => {
        const exitLine = `[${getTimestamp()}] [INFO] Process exited with code ${code}${signal ? ` (signal: ${signal})` : ''}\n`;
        logStream.write(exitLine);
        logStream.end();

        if (code !== 0 && code !== null) {
          console.error(`[ALERT] Specialist ${specialistId} exited with error code ${code}`);
        }
      });

      // Store log file path in database metadata
      db.query(
        `UPDATE autonomy_team_activations SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{log_file}', to_jsonb($1::text))
         WHERE specialist_id = $2`,
        [logFilePath, specialistId]
      ).catch((err) => {
        console.warn(`[TeamActivation] Failed to store log path for ${specialistId}: ${err.message}`);
      });

      return childProcess;
    } catch (error: any) {
      console.error(`[TeamActivation] Failed to spawn specialist subprocess: ${error.message}`);
      return null;
    }
  }

  /**
   * Wait for specialist HTTP server to be ready
   */
  private async waitForSpecialistReady(httpEndpoint: string, timeoutMs: number): Promise<boolean> {
    const startTime = Date.now();
    const statusUrl = `${httpEndpoint}/status`;

    while (Date.now() - startTime < timeoutMs) {
      try {
        const response = await fetch(statusUrl, { method: 'GET' });
        if (response.ok) {
          console.log(`[TeamActivation] Specialist server ready at ${httpEndpoint}`);
          return true;
        }
      } catch (error) {
        // Server not ready yet, retry
      }

      // Wait 100ms before retrying
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    console.error(`[TeamActivation] Specialist server at ${httpEndpoint} did not become ready within ${timeoutMs}ms`);
    return false;
  }

  /**
   * Ask the OS for an available loopback port.
   *
   * This avoids collisions from random port selection when multiple specialists
   * spawn quickly or prior test processes are still winding down.
   */
  private async findAvailablePort(): Promise<number> {
    return new Promise((resolve, reject) => {
      const server = net.createServer();
      server.unref();
      server.once('error', reject);
      server.listen(0, '127.0.0.1', () => {
        const address = server.address();
        if (!address || typeof address === 'string') {
          server.close(() => reject(new Error('OS did not return a TCP port')));
          return;
        }
        const port = address.port;
        server.close((error) => {
          if (error) {
            reject(error);
          } else {
            resolve(port);
          }
        });
      });
    });
  }
}
