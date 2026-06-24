import { pool } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

/**
 * PHASE 10: Controlled Simulation Environments
 *
 * Deterministic simulators for sandbox training:
 * - BusinessDecisionSim: Budget/resource/timeline decisions
 * - ResearchClaimSim: Evidence, uncertainty, contradiction handling
 *
 * CRITICAL RULES:
 * - Same seed = same trajectory
 * - Simulation-derived trajectories marked in trajectory_store
 * - Simulation claims cannot become real-world truth
 * - Simulators must produce real outcomes (not fake success)
 */

interface SimulatorConfig {
  simulatorName: string;
  seed: number;
  configJson: Record<string, any>;
}

class SimulatorService {
  /**
   * Create simulator configuration
   */
  async createSimulatorConfig(input: SimulatorConfig): Promise<string> {
    const client = await pool.connect();
    try {
      const configId = uuidv4();

      await client.query(
        `INSERT INTO simulator_configs
         (id, simulator_name, config_json, seed)
         VALUES ($1, $2, $3, $4)`,
        [configId, input.simulatorName, JSON.stringify(input.configJson), input.seed]
      );

      return configId;
    } finally {
      client.release();
    }
  }

  /**
   * Run simulator with given config
   * 
   * Rule: Same seed → same trajectory
   * Rule: Must produce deterministic outcomes
   * Rule: Must write simulator_steps AND simulator_outcomes
   */
  async runSimulator(simulatorName: string, configId: string, traceId?: string): Promise<{ runId: string }> {
    const client = await pool.connect();
    try {
      // Fetch config
      const configResult = await client.query(
        `SELECT seed, config_json FROM simulator_configs WHERE id = $1`,
        [configId]
      );

      if (!configResult.rows.length) {
        throw new Error(`Config ${configId} not found`);
      }

      const { seed, config_json } = configResult.rows[0];
      const runId = uuidv4();

      // Create run record
      await client.query(
        `INSERT INTO simulator_runs
         (id, simulator_name, config_id, seed, status, started_at, trace_id)
         VALUES ($1, $2, $3, $4, $5, NOW(), $6)`,
        [runId, simulatorName, configId, seed, 'running', traceId || null]
      );

      // Execute simulator (deterministic based on seed)
      const trajectory = this.executeSimulator(simulatorName, seed, config_json);

      // Store each step
      for (const step of trajectory.steps) {
        await client.query(
          `INSERT INTO simulator_steps
           (id, simulator_run_id, step_index, observation_json, action_json, reward, done, info_json)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
          [
            uuidv4(),
            runId,
            step.stepIndex,
            JSON.stringify(step.observation),
            JSON.stringify(step.action),
            step.reward,
            step.done,
            JSON.stringify(step.info || {}),
          ]
        );
      }

      // Store outcome
      await client.query(
        `INSERT INTO simulator_outcomes
         (id, simulator_run_id, outcome_json, total_reward, success)
         VALUES ($1, $2, $3, $4, $5)`,
        [
          uuidv4(),
          runId,
          JSON.stringify(trajectory.outcome),
          trajectory.totalReward,
          trajectory.success,
        ]
      );

      // Mark as completed
      await client.query(
        `UPDATE simulator_runs SET status = $1, completed_at = NOW()
         WHERE id = $2`,
        ['completed', runId]
      );

      // Persist trajectory to trajectory_store with simulation label
      const trajId = uuidv4();
      await client.query(
        `INSERT INTO trajectory_store
         (id, trajectory_json, is_successful, is_simulation, source, created_at)
         VALUES ($1, $2, $3, $4, $5, NOW())`,
        [
          trajId,
          JSON.stringify(trajectory),
          trajectory.success,
          true, // simulation_derived
          `simulator:${simulatorName}`,
        ]
      );

      return { runId };
    } finally {
      client.release();
    }
  }

  /**
   * Get simulator run with all steps
   */
  async getSimulatorRun(runId: string): Promise<any> {
    const client = await pool.connect();
    try {
      const runResult = await client.query(
        `SELECT * FROM simulator_runs WHERE id = $1`,
        [runId]
      );

      if (!runResult.rows.length) return null;

      const run = runResult.rows[0];

      // Fetch steps
      const stepsResult = await client.query(
        `SELECT * FROM simulator_steps WHERE simulator_run_id = $1 ORDER BY step_index`,
        [runId]
      );

      // Fetch outcome
      const outcomeResult = await client.query(
        `SELECT * FROM simulator_outcomes WHERE simulator_run_id = $1`,
        [runId]
      );

      return {
        ...run,
        steps: stepsResult.rows,
        outcome: outcomeResult.rows.length ? outcomeResult.rows[0] : null,
      };
    } finally {
      client.release();
    }
  }

  /**
   * List simulator runs
   */
  async listSimulatorRuns(filters?: { simulatorName?: string; status?: string }): Promise<any[]> {
    const client = await pool.connect();
    try {
      let query = 'SELECT * FROM simulator_runs WHERE 1=1';
      const params: any[] = [];

      if (filters?.simulatorName) {
        params.push(filters.simulatorName);
        query += ` AND simulator_name = $${params.length}`;
      }
      if (filters?.status) {
        params.push(filters.status);
        query += ` AND status = $${params.length}`;
      }

      query += ' ORDER BY created_at DESC';

      const result = await client.query(query, params);
      return result.rows;
    } finally {
      client.release();
    }
  }

  // ============================================================
  // SIMULATORS (Real deterministic logic)
  // ============================================================

  /**
   * Execute simulator based on type
   * 
   * Returns deterministic trajectory with REAL outcomes
   * (not fake success)
   */
  private executeSimulator(
    simulatorName: string,
    seed: number,
    config: Record<string, any>
  ): {
    steps: any[];
    outcome: any;
    totalReward: number;
    success: boolean;
  } {
    if (simulatorName === 'BusinessDecisionSim') {
      return this.runBusinessDecisionSim(seed, config);
    } else if (simulatorName === 'ResearchClaimSim') {
      return this.runResearchClaimSim(seed, config);
    } else {
      throw new Error(`Unknown simulator: ${simulatorName}`);
    }
  }

  /**
   * Business Decision Simulator
   * 
   * Tests: Budget allocation, timeline, resource decisions
   * Returns: Real outcomes based on decision quality
   */
  private runBusinessDecisionSim(seed: number, config: Record<string, any>): any {
    const steps = [];
    let totalReward = 0;
    let budget = config.initialBudget || 100000;
    let timeline = config.timeline || 12; // months
    let quality = 50; // 0-100 scale

    const seededRandom = this.seededRng(seed);

    // Step 1: Decision phase
    const decisions = {
      allocateTech: config.allocateTech !== false,
      allocateMarketing: config.allocateMarketing !== false,
      hireSenior: config.hireSenior !== false,
    };

    steps.push({
      stepIndex: 1,
      observation: { budget, timeline, availableResources: decisions },
      action: decisions,
      reward: 0,
      done: false,
      info: { phase: 'allocation' },
    });

    // Step 2: Tech quality improvement (if allocated)
    if (decisions.allocateTech) {
      budget -= 30000;
      quality += seededRandom() * 20; // 0-20 point improvement
      totalReward += 15;
    }

    steps.push({
      stepIndex: 2,
      observation: { budget, quality, timeRemaining: timeline - 3 },
      action: { implemented: 'tech', quality },
      reward: decisions.allocateTech ? 15 : 0,
      done: false,
      info: { phase: 'tech_phase' },
    });

    // Step 3: Marketing (if allocated)
    if (decisions.allocateMarketing) {
      budget -= 20000;
      quality += seededRandom() * 15; // 0-15 point improvement
      totalReward += 10;
    }

    steps.push({
      stepIndex: 3,
      observation: { budget, quality, timeRemaining: timeline - 6 },
      action: { implemented: 'marketing', quality },
      reward: decisions.allocateMarketing ? 10 : 0,
      done: false,
      info: { phase: 'marketing_phase' },
    });

    // Step 4: Senior hiring impact
    if (decisions.hireSenior && budget > 50000) {
      budget -= 80000;
      quality += seededRandom() * 25; // 0-25 point improvement
      totalReward += 20;
    }

    quality = Math.min(100, quality);

    steps.push({
      stepIndex: 4,
      observation: { budget, quality, remaining: budget },
      action: { finalQuality: quality, budgetRemaining: budget },
      reward: decisions.hireSenior ? 20 : 5,
      done: true,
      info: { phase: 'completion' },
    });

    totalReward += quality / 10; // Quality bonus

    const success = quality > 70 && budget > 0;

    return {
      steps,
      outcome: {
        finalQuality: Math.round(quality),
        budgetUsed: config.initialBudget - budget,
        budgetRemaining: budget,
        success,
      },
      totalReward: Math.round(totalReward),
      success,
    };
  }

  /**
   * Research Claim Simulator
   * 
   * Tests: Evidence gathering, uncertainty labeling, contradiction handling
   * Returns: Real outcomes with calibration penalties for overclaiming
   */
  private runResearchClaimSim(seed: number, config: Record<string, any>): any {
    const steps = [];
    let totalReward = 0;
    let claimsProposed = 0;
    let claimsSupported = 0;
    let overclaims = 0;

    const seededRandom = this.seededRng(seed);

    // Step 1: Evidence gathering
    const evidenceQuality = Math.round(seededRandom() * 100);

    steps.push({
      stepIndex: 1,
      observation: { phase: 'evidence_gathering' },
      action: { gatherEvidence: true },
      reward: evidenceQuality / 10,
      done: false,
      info: { evidenceQuality },
    });

    totalReward += evidenceQuality / 10;

    // Step 2: Claim proposal
    const proposedClaimConfidence = config.claimConfidence || 0.8;
    claimsProposed = 3;

    steps.push({
      stepIndex: 2,
      observation: { evidenceQuality, proposedClaims: claimsProposed },
      action: { proposeClaims: claimsProposed, confidence: proposedClaimConfidence },
      reward: 5,
      done: false,
      info: { phase: 'claim_proposal' },
    });

    totalReward += 5;

    // Step 3: Calibration check
    const actualSupported = Math.round((evidenceQuality / 100) * claimsProposed);
    claimsSupported = actualSupported;
    overclaims = claimsProposed - actualSupported;

    // Penalty for overclaiming
    const calibrationPenalty = overclaims * 10;
    const calibrationReward = Math.max(0, 20 - calibrationPenalty);

    steps.push({
      stepIndex: 3,
      observation: {
        evidenceQuality,
        claimsProposed,
        claimsSupported,
        overclaims,
      },
      action: { reviewClaims: true, supportedCount: claimsSupported },
      reward: calibrationReward,
      done: false,
      info: { phase: 'calibration_check', penalty: calibrationPenalty },
    });

    totalReward += calibrationReward;

    // Step 4: Uncertainty labeling
    const uncertaintyHandled = overclaims === 0; // Perfect if no overclaims
    const uncertaintyReward = uncertaintyHandled ? 15 : Math.max(0, 15 - overclaims * 5);

    steps.push({
      stepIndex: 4,
      observation: {
        claimsSupported,
        uncertaintyHandled,
        finalScore: Math.round(totalReward),
      },
      action: { labelUncertainty: true },
      reward: uncertaintyReward,
      done: true,
      info: { phase: 'completion' },
    });

    totalReward += uncertaintyReward;

    // Simulation cannot become reality - mark explicitly
    const success = overclaims === 0;

    return {
      steps,
      outcome: {
        claimsProposed,
        claimsSupported,
        overclaims,
        calibrationScore: Math.round(((claimsSupported / claimsProposed) * 100) || 0),
        success,
        labeledAsSimulation: true, // CRITICAL: Mark as simulation
      },
      totalReward: Math.round(totalReward),
      success,
    };
  }

  // ============================================================
  // UTILITIES
  // ============================================================

  /**
   * Seeded pseudo-random number generator
   * 
   * Ensures: Same seed → same sequence
   */
  private seededRng(seed: number): () => number {
    // Simple seeded PRNG (xorshift64*)
    let state = seed || 12345;

    return () => {
      state ^= state << 13;
      state ^= state >> 7;
      state ^= state << 17;
      return Math.abs(state % 1000) / 1000; // Return 0-1
    };
  }
}

export const simulator = new SimulatorService();
