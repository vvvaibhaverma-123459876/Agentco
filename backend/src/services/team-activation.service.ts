/**
 * Team Activation Service
 * ======================
 * Manages specialist agent instantiation, budget enforcement, and lifecycle.
 * Spawns bounded agents with resource limits and aggregates results back to parent.
 */

import { v4 as uuidv4 } from 'uuid';
import { spawn, ChildProcess } from 'child_process';
import { db } from '../db/client';
import { getSpecialistRole, isValidSpecialistRole } from '../types/specialist-roles';
import { ActionSpec, ActionResult } from '../types/action.types';

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
    const portNumber = this.findAvailablePort();
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
      return null;
    }

    specialist.processId = childProcess.pid;

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
      console.log(`[TeamActivation] Specialist process ${specialistId} exited with code ${code}`);
      this.activeProcesses.delete(specialistId);
    });

    console.log(`[TeamActivation] Spawned specialist ${specialistId} (role: ${request.role}, pid: ${childProcess.pid}, port: ${portNumber})`);
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
      childProcess.kill('SIGTERM');
      // Wait up to 2 seconds for graceful shutdown, then force kill
      setTimeout(() => {
        if (!childProcess.killed) {
          childProcess.kill('SIGKILL');
        }
      }, 2000);
    }

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
   * Execute action via specialist HTTP endpoint
   */
  async executeActionViaSpecialist(
    specialistId: string,
    actionSpec: ActionSpec
  ): Promise<ActionResult | null> {
    const specialist = this.activeSpecialists.get(specialistId);
    if (!specialist || !specialist.httpEndpoint) {
      console.error(`Specialist not found or HTTP endpoint not available: ${specialistId}`);
      return null;
    }

    try {
      // Create abort controller for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), specialist.secondsBudget * 1000);

      // Call specialist HTTP endpoint
      const response = await fetch(`${specialist.httpEndpoint}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(actionSpec),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.error(`Specialist HTTP error: ${response.status}`);
        return null;
      }

      const result = (await response.json()) as any;

      // Record token usage
      await this.recordTokenUsage(specialistId, result.tokens_used || 0);
      await this.recordIterationUsage(specialistId);

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
      console.error(`Specialist HTTP execution failed: ${error.message}`);
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
   * Spawn a Python specialist subprocess
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

      const childProcess = spawn('python3', args, {
        detached: false,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: {
          ...process.env,
          SPECIALIST_ID: specialistId,
          SPECIALIST_ROLE: role,
        },
      });

      // Log subprocess output for debugging
      childProcess.stdout?.on('data', (data) => {
        console.log(`[Specialist ${specialistId}] ${data.toString().trim()}`);
      });

      childProcess.stderr?.on('data', (data) => {
        console.error(`[Specialist ${specialistId}] ERROR: ${data.toString().trim()}`);
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
   * Find available port by assigning random port in safe range
   */
  private findAvailablePort(): number {
    // Simple port assignment: use random port in 54321-55000 range
    return 54321 + Math.floor(Math.random() * 679);
  }
}
