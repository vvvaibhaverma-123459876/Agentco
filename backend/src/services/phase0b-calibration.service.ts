/**
 * Phase 0b: Calibration Service
 * Pre-registers predictions before outcomes are known
 * Resolves them against actual measured values
 * Computes Brier scores and calibration metrics
 */

import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface PredictionInput {
  category: string;
  description: string;
  confidence: number;  // 0.0 to 1.0
  expectedResolutionBy: Date;
  hypothesis?: string;
}

export interface PredictionRecord {
  prediction_id: string;
  category: string;
  description: string;
  confidence: number;
  expectedResolutionBy: Date;
  createdAt: Date;
}

export interface ResolutionInput {
  predictionId: string;
  outcome: boolean;  // did the prediction come true?
  actualValue?: string;
  measurementMethod?: string;
}

/**
 * Service for Phase 0b calibration pre-registration and resolution
 */
export class Phase0bCalibrationService {
  /**
   * Register a prediction before outcome is known
   * The timestamp of this commit is the proof of pre-registration
   */
  async registerPrediction(input: PredictionInput, createdBy: string = 'system'): Promise<PredictionRecord> {
    if (input.confidence < 0 || input.confidence > 1) {
      throw new Error('Confidence must be between 0.0 and 1.0');
    }

    const predictionId = `pred_${Date.now()}_${uuidv4().slice(0, 8)}`;

    await db.query(
      `INSERT INTO predictions
       (prediction_id, category, description, confidence, expected_resolution_by, hypothesis, created_by)
       VALUES ($1, $2, $3, $4, $5, $6, $7)`,
      [
        predictionId,
        input.category,
        input.description,
        input.confidence,
        input.expectedResolutionBy,
        input.hypothesis || null,
        createdBy,
      ]
    );

    return {
      prediction_id: predictionId,
      category: input.category,
      description: input.description,
      confidence: input.confidence,
      expectedResolutionBy: input.expectedResolutionBy,
      createdAt: new Date(),
    };
  }

  /**
   * Resolve a prediction against actual measured outcome
   * Computes Brier component: (confidence - outcome)^2
   */
  async resolvePrediction(input: ResolutionInput): Promise<void> {
    // Get the prediction to retrieve confidence
    const result = await db.query(
      `SELECT confidence FROM predictions WHERE prediction_id = $1`,
      [input.predictionId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Prediction not found: ${input.predictionId}`);
    }

    const confidence = result.rows[0].confidence;
    const outcomeValue = input.outcome ? 1 : 0;
    const brierComponent = Math.pow(confidence - outcomeValue, 2);

    await db.query(
      `INSERT INTO prediction_resolutions
       (prediction_id, outcome, actual_value, measurement_method, resolved_at, brier_component)
       VALUES ($1, $2, $3, $4, NOW(), $5)`,
      [
        input.predictionId,
        input.outcome,
        input.actualValue || null,
        input.measurementMethod || null,
        brierComponent,
      ]
    );
  }

  /**
   * Get all unresolved predictions (for monitoring/resolving)
   */
  async getUnresolvedPredictions(): Promise<any[]> {
    const result = await db.query(
      `SELECT p.* FROM predictions p
       LEFT JOIN prediction_resolutions pr ON p.prediction_id = pr.prediction_id
       WHERE pr.prediction_id IS NULL
       ORDER BY p.expected_resolution_by ASC`
    );
    return result.rows;
  }

  /**
   * Get calibration statistics for all resolved predictions
   */
  async getCalibrationStats(): Promise<any> {
    const result = await db.query(
      `SELECT * FROM prediction_calibration_stats`
    );
    return result.rows[0] || {
      total_predictions: 0,
      correct: 0,
      accuracy: null,
      avg_brier_score: null,
      avg_confidence: null,
    };
  }

  /**
   * Get calibration stats by category
   */
  async getCalibrationStatsByCategory(): Promise<any[]> {
    const result = await db.query(
      `SELECT
         p.category,
         COUNT(DISTINCT pr.prediction_id) as total_predictions,
         COUNT(CASE WHEN pr.outcome = true THEN 1 END) as correct,
         ROUND(COUNT(CASE WHEN pr.outcome = true THEN 1 END)::FLOAT / COUNT(*), 3) as accuracy,
         ROUND(AVG(pr.brier_component), 4) as avg_brier_score,
         ROUND(AVG(p.confidence), 3) as avg_confidence
       FROM predictions p
       LEFT JOIN prediction_resolutions pr ON p.prediction_id = pr.prediction_id
       WHERE pr.resolved_at IS NOT NULL
       GROUP BY p.category
       ORDER BY p.category`
    );
    return result.rows;
  }

  /**
   * Get all predictions and their resolutions
   */
  async getAllPredictionsWithResolutions(): Promise<any[]> {
    const result = await db.query(
      `SELECT
         p.*,
         pr.outcome,
         pr.actual_value,
         pr.resolved_at,
         pr.brier_component
       FROM predictions p
       LEFT JOIN prediction_resolutions pr ON p.prediction_id = pr.prediction_id
       ORDER BY p.created_at DESC`
    );
    return result.rows;
  }
}
