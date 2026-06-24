/**
 * Autonomy Forecasting Service
 *
 * Path A: System-Generated Predictions for Phase 0b
 * Routes external event descriptions through AgentCo's model stack to generate
 * calibrated confidence scores. These are legitimately system-produced, not
 * hand-authored.
 *
 * Key constraint: NO real-time data lookup before forecast commitment.
 * Model generates probability from training priors only.
 */

import { db } from '../db/client';
import { AutonomyModelSelectionService } from './autonomy-model-selection.service';
import { v4 as uuidv4 } from 'uuid';

export interface ExternalEventDescription {
  category: string;
  description: string;
  context: string;  // additional context for the model's reasoning
  resolutionCriterion: string;  // how will this be measured
}

export interface GeneratedForecast {
  prediction_id: string;
  decision_id: string;
  confidence: number;
  reasoning: string;
  model_code: string;
  prompt: string;
  raw_response: string;
}

/**
 * System-driven forecast generation
 * Produces confidences through the same LLM infrastructure as the planner
 */
export class AutonomyForecastingService {
  private modelSelector = new AutonomyModelSelectionService();

  /**
   * Generate a system confidence for an external event
   * Routes through selectModelForAction + model call, logged to model_decision_ledger
   */
  async generateForecast(event: ExternalEventDescription): Promise<GeneratedForecast> {
    // Build the forecasting prompt
    const prompt = this.buildForecastPrompt(event);

    // Get model decision (selects model, logs to ledger)
    const modelDecision = await this.callModelForForecast(prompt, event);

    // Parse response to extract confidence and reasoning
    const { confidence, reasoning, rawResponse } = this.parseForecastResponse(
      modelDecision.response
    );

    if (confidence === null) {
      throw new Error(`Failed to extract confidence from model response: ${rawResponse}`);
    }

    // Create prediction record with decision_id for traceability
    const prediction_id = `pred_system_${Date.now()}_${uuidv4().slice(0, 8)}`;

    await db.query(
      `INSERT INTO predictions
       (prediction_id, category, description, confidence, expected_resolution_by, hypothesis, created_by)
       VALUES ($1, $2, $3, $4, NOW() + INTERVAL '7 days', $5, $6)`,
      [prediction_id, event.category, event.description, confidence, reasoning, 'autonomy_forecasting_service']
    );

    return {
      prediction_id,
      decision_id: modelDecision.decision_id,
      confidence,
      reasoning,
      model_code: modelDecision.modelCode,
      prompt,
      raw_response: rawResponse,
    };
  }

  /**
   * Call the model through selectModelForAction + same API as the planner
   * This ensures the confidence is system-generated and routed through Brick 2 infrastructure
   */
  private async callModelForForecast(
    prompt: string,
    event: ExternalEventDescription
  ): Promise<{ response: string; decision_id: string; modelCode: string }> {
    // Use the model selector to route through Brick 2 infrastructure
    const modelDecision = await this.modelSelector.selectModelForAction('FORECAST_' + event.category.toUpperCase());

    const apiKey = process.env.LLM_API_KEY || '';
    if (!apiKey) {
      throw new Error('LLM_API_KEY not set');
    }

    // Determine API URL based on provider
    let baseUrl = process.env.LLM_BASE_URL;
    if (!baseUrl) {
      baseUrl = modelDecision.provider === 'anthropic'
        ? 'https://api.anthropic.com/v1'
        : 'https://api.openai.com/v1';
    }
    const apiUrl = `${baseUrl}/chat/completions`;

    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: modelDecision.modelCode,
          messages: [
            {
              role: 'system',
              content: `You are a calibrated probabilistic forecaster. Your task is to assess the likelihood
of external events based on your training knowledge only. Do NOT look up current information or make
real-time queries. Base your forecast on your prior beliefs from training data.

For each event, provide:
1. A probability in [0.0, 1.0]
2. Brief reasoning (1-2 sentences) explaining your assessment

Format your response as:
PROBABILITY: <number>
REASONING: <text>`,
            },
            {
              role: 'user',
              content: prompt,
            },
          ],
          max_tokens: 150,
          temperature: 0.7,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data: any = await response.json();
      const content = data.choices?.[0]?.message?.content;

      if (!content) {
        throw new Error('Empty response from model');
      }

      // Update decision ledger with token usage (uses decision_id from selectModelForAction)
      const requestTokens = data.usage?.prompt_tokens;
      const responseTokens = data.usage?.completion_tokens;

      await this.modelSelector.updateDecisionOutcome(
        modelDecision.decision_id,
        requestTokens || 0,
        responseTokens || 0,
        true
      );

      return {
        response: content,
        decision_id: modelDecision.decision_id,
        modelCode: modelDecision.modelCode,
      };
    } catch (error) {
      // Log failure via model selector
      await this.modelSelector.updateDecisionOutcome(
        modelDecision.decision_id,
        0,
        0,
        false,
        String(error)
      );

      throw error;
    }
  }

  /**
   * Build the prompt for forecasting a single event
   */
  private buildForecastPrompt(event: ExternalEventDescription): string {
    return `Event Category: ${event.category}

Event Description: ${event.description}

Additional Context: ${event.context}

Resolution Criterion: ${event.resolutionCriterion}

Based on your training knowledge and prior beliefs about similar events, what is your probability
that this event will resolve TRUE by the stated resolution date?

Remember: provide ONLY your prior belief, do NOT attempt to look up current information.
Provide your response in the format specified in the system message.`;
  }

  /**
   * Parse the model's response to extract probability and reasoning
   */
  private parseForecastResponse(response: string): {
    confidence: number | null;
    reasoning: string;
    rawResponse: string;
  } {
    const rawResponse = response;

    // Extract PROBABILITY: X.XX
    const probMatch = response.match(/PROBABILITY:\s*([\d.]+)/i);
    let confidence: number | null = null;

    if (probMatch) {
      const parsed = parseFloat(probMatch[1]);
      if (!isNaN(parsed) && parsed >= 0 && parsed <= 1) {
        confidence = parsed;
      }
    }

    // Extract REASONING: ...
    const reasoningMatch = response.match(/REASONING:\s*(.+?)(?=\n|$)/i);
    const reasoning = reasoningMatch ? reasoningMatch[1].trim() : 'No reasoning provided';

    return { confidence, reasoning, rawResponse };
  }

  /**
   * Utility: get all forecasts generated by the system
   */
  async getSystemForecasts(): Promise<any[]> {
    const result = await db.query(
      `SELECT p.*, mdl.decision_id, mdl.model_code, mdl.request_tokens, mdl.response_tokens
       FROM predictions p
       LEFT JOIN model_decision_ledger mdl ON mdl.id IN (
         SELECT id FROM model_decision_ledger WHERE decision_id LIKE 'pred_system_%'
       )
       WHERE p.created_by = 'autonomy_forecasting_service'
       ORDER BY p.created_at DESC`
    );

    return result.rows;
  }
}
