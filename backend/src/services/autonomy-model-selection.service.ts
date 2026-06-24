import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface ModelSpec {
  provider: 'openai' | 'anthropic' | 'local';
  tier: 'speed' | 'reasoning' | 'emergency';
  context_window: number;
  cost_per_1k_tokens: number;
}

export interface ModelDecision {
  decision_id: string;
  modelCode: string;
  provider: string;
  reasoning: string;
}

/**
 * Centralized model selection service.
 * Logs every decision to model_decision_ledger for auditing and future calibration-based routing.
 */
export class AutonomyModelSelectionService {
  private MODEL_REGISTRY: Record<string, ModelSpec> = {
    'gpt-4o-mini': {
      provider: 'openai',
      tier: 'speed',
      context_window: 128000,
      cost_per_1k_tokens: 0.00015,
    },
    'claude-opus-4-8': {
      provider: 'anthropic',
      tier: 'reasoning',
      context_window: 200000,
      cost_per_1k_tokens: 0.003,
    },
    'claude-haiku-4-5': {
      provider: 'anthropic',
      tier: 'speed',
      context_window: 200000,
      cost_per_1k_tokens: 0.00008,
    },
  };

  private FALLBACK_ORDER = [
    'gpt-4o-mini',
    'claude-haiku-4-5',
    'claude-opus-4-8',
  ];

  /**
   * Select a model for a given action type.
   * Logs the decision to model_decision_ledger immediately.
   *
   * @param actionType - Type of action (PLAN_ACTION, EXTRACT_CLAIMS, VALIDATE_EVIDENCE, etc.)
   * @param primaryFailed - If true, use fallback model instead of primary
   * @returns Decision with decision_id, modelCode, provider, reasoning
   */
  async selectModelForAction(
    actionType: string,
    primaryFailed: boolean = false,
  ): Promise<ModelDecision> {
    const decision_id = uuidv4();
    let modelCode: string;
    let reasoning: string;

    // Simple rule-based selection (will be enhanced with Phase 0b calibration data)
    if (primaryFailed) {
      // Use fallback model
      modelCode = this.FALLBACK_ORDER[1]; // Second in fallback order
      reasoning = 'fallback_after_primary_failed';
    } else {
      // Default: use fast model for all actions for now
      // Future: Use ACTION_TYPE_TO_TIER mapping when calibration data is available
      modelCode = 'gpt-4o-mini';
      reasoning = 'default';
    }

    const spec = this.MODEL_REGISTRY[modelCode];
    if (!spec) {
      throw new Error(`Unknown model code: ${modelCode}`);
    }

    // Log decision to ledger immediately
    await this.logDecision({
      decision_id,
      modelCode,
      provider: spec.provider,
      reasoning,
    });

    return {
      decision_id,
      modelCode,
      provider: spec.provider,
      reasoning,
    };
  }

  /**
   * Update decision with token usage and success status after API call completes.
   */
  async updateDecisionOutcome(
    decision_id: string,
    requestTokens: number,
    responseTokens: number,
    success: boolean,
    errorMessage?: string,
  ): Promise<void> {
    await db.query(
      `UPDATE model_decision_ledger
       SET request_tokens = $1,
           response_tokens = $2,
           success = $3,
           error_message = $4,
           resolved_at = NOW()
       WHERE decision_id = $5`,
      [requestTokens, responseTokens, success, errorMessage || null, decision_id],
    );
  }

  /**
   * Link decision to an action or claim (optional, called after execution).
   */
  async linkDecisionToAction(
    decision_id: string,
    actionId: string,
  ): Promise<void> {
    await db.query(
      `UPDATE model_decision_ledger
       SET action_id = $1
       WHERE decision_id = $2`,
      [actionId, decision_id],
    );
  }

  async linkDecisionToClaim(
    decision_id: string,
    claimId: string,
  ): Promise<void> {
    await db.query(
      `UPDATE model_decision_ledger
       SET claim_id = $1
       WHERE decision_id = $2`,
      [claimId, decision_id],
    );
  }

  /**
   * Get recent decisions for a model (used for future calibration queries).
   */
  async getRecentDecisions(
    modelCode: string,
    limit: number = 10,
  ): Promise<any[]> {
    const result = await db.query(
      `SELECT * FROM model_decision_ledger
       WHERE model_code = $1
       ORDER BY created_at DESC
       LIMIT $2`,
      [modelCode, limit],
    );
    return result.rows;
  }

  /**
   * Get calibration statistics for a model (stub for Phase 0b integration).
   * When Phase 0b calibration data is available, this will compute:
   * - Accuracy (success / total)
   * - Brier score (confidence vs outcome)
   * - ECE (expected calibration error)
   */
  async getCalibrationStats(modelCode: string): Promise<any> {
    const result = await db.query(
      `SELECT
         COUNT(*) as total_calls,
         COUNT(CASE WHEN success = true THEN 1 END) as successful_calls,
         COUNT(CASE WHEN success = true THEN 1 END)::FLOAT / COUNT(*) as accuracy
       FROM model_decision_ledger
       WHERE model_code = $1 AND success IS NOT NULL`,
      [modelCode],
    );
    return result.rows[0] || { total_calls: 0, successful_calls: 0, accuracy: null };
  }

  // Private helper
  private async logDecision(decision: {
    decision_id: string;
    modelCode: string;
    provider: string;
    reasoning: string;
  }): Promise<void> {
    await db.query(
      `INSERT INTO model_decision_ledger
       (id, decision_id, model_code, provider, selection_reasoning, created_at)
       VALUES ($1, $2, $3, $4, $5, NOW())`,
      [
        uuidv4(), // Primary key id
        decision.decision_id,
        decision.modelCode,
        decision.provider,
        decision.reasoning,
      ],
    );
  }
}
