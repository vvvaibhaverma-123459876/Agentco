import crypto from 'crypto';
import { Pool, PoolClient } from 'pg';
import { db } from '../db/client';
import { auditLog } from './audit-log.service';
import { eventLog } from './event-log.service';

export interface RegisterPredictionInput {
  prediction_id?: string;
  claim: string;
  probability: number;
  confidence_basis: Record<string, unknown>;
  producing_agent_id: string;
  producing_prompt_version: string;
  resolution_criterion: string;
  resolution_date: Date;
  ground_truth_source: string;
  horizon_class: 'short' | 'medium' | 'long';
  domain: string;
  claim_type?: string;
  correlation_id?: string;
}

export interface ResolvePredictionInput {
  prediction_id: string;
  resolved_outcome: boolean;
  resolved_by_service?: string;
  correlation_id?: string;
}

export interface PredictionResolutionRecord {
  prediction_id: string;
  probability: string | number;
  producing_agent_id: string;
  domain: string;
  claim_type: string;
  horizon_class: string;
  resolved: boolean;
  resolved_outcome: boolean;
  brier_score: string | number;
  log_score: string | number;
}

function requireText(value: string | undefined, field: string): string {
  const normalized = value?.trim();
  if (!normalized) throw new Error(`${field} is required`);
  return normalized;
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

function clampProbability(value: number): number {
  if (!Number.isFinite(value) || value < 0 || value > 1) throw new Error('probability must be between 0 and 1');
  return value;
}

function brier(probability: number, outcome: boolean): number {
  const actual = outcome ? 1 : 0;
  return Math.pow(probability - actual, 2);
}

function logScore(probability: number, outcome: boolean): number {
  const bounded = Math.min(0.999999, Math.max(0.000001, probability));
  return outcome ? -Math.log(bounded) : -Math.log(1 - bounded);
}

export class LedgerResolutionService {
  private servicePool?: Pool;

  async registerPrediction(input: RegisterPredictionInput): Promise<string> {
    this.validateRegistration(input);
    const predictionId = input.prediction_id ?? crypto.randomUUID();
    await db.query(
      `INSERT INTO prediction_ledger
         (prediction_id, claim, probability, confidence_basis, producing_agent_id,
          producing_prompt_version, resolution_criterion, resolution_date, ground_truth_source,
          horizon_class, domain, claim_type, correlation_id)
       VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7,$8,$9,$10,$11,$12,$13)`,
      [
        predictionId,
        input.claim,
        input.probability,
        JSON.stringify(input.confidence_basis ?? {}),
        input.producing_agent_id,
        input.producing_prompt_version,
        input.resolution_criterion,
        input.resolution_date,
        input.ground_truth_source,
        input.horizon_class,
        input.domain,
        input.claim_type ?? 'general',
        input.correlation_id ?? null,
      ]
    );
    return predictionId;
  }

  async resolvePrediction(input: ResolvePredictionInput): Promise<PredictionResolutionRecord> {
    const serviceUrl = process.env.RESOLUTION_SERVICE_DATABASE_URL;
    if (!serviceUrl) {
      throw new Error('RESOLUTION_SERVICE_DATABASE_URL is required for ledger resolution');
    }
    if (!this.servicePool) {
      this.servicePool = new Pool({ connectionString: serviceUrl, max: 2, connectionTimeoutMillis: 2000 });
    }
    const client = await this.servicePool.connect();
    try {
      return await this.resolveWithClient(client, input);
    } finally {
      client.release();
    }
  }

  async resolveWithClient(client: PoolClient, input: ResolvePredictionInput): Promise<PredictionResolutionRecord> {
    if (!isUuid(input.prediction_id)) throw new Error('prediction_id must be a UUID');
    const existing = await client.query<{ probability: string | number }>(
      `SELECT probability FROM prediction_ledger WHERE prediction_id = $1 AND resolved = false`,
      [input.prediction_id]
    );
    if ((existing.rowCount ?? 0) !== 1) throw new Error(`unresolved prediction not found: ${input.prediction_id}`);
    const probability = Number(existing.rows[0].probability);
    const brierScore = brier(probability, input.resolved_outcome);
    const log = logScore(probability, input.resolved_outcome);
    const resolved = await client.query<PredictionResolutionRecord>(
      `UPDATE prediction_ledger
          SET resolved = true,
              resolved_outcome = $2,
              resolved_at = NOW(),
              resolved_by_service = $3,
              brier_score = $4,
              log_score = $5,
              was_surprise = $6
        WHERE prediction_id = $1
        RETURNING prediction_id, probability, producing_agent_id, domain, claim_type,
                  horizon_class, resolved, resolved_outcome, brier_score, log_score`,
      [
        input.prediction_id,
        input.resolved_outcome,
        input.resolved_by_service ?? 'resolution_service',
        brierScore,
        log,
        brierScore > 0.25,
      ]
    );
    return resolved.rows[0];
  }

  async recordResolutionEvent(record: PredictionResolutionRecord, correlationId: string = crypto.randomUUID()): Promise<void> {
    const actorId = await this.ensureServiceActor('agentco-resolution-service', ['prediction.resolve']);
    const event = await eventLog.append({
      event_type: 'prediction.resolved',
      actor_id: actorId,
      object_type: 'prediction',
      object_id: record.prediction_id,
      correlation_id: correlationId,
      payload: {
        prediction_id: record.prediction_id,
        resolved_outcome: record.resolved_outcome,
        brier_score: Number(record.brier_score),
        log_score: Number(record.log_score),
      },
    });
    await auditLog.append({
      agent_id: actorId,
      action_type: 'event_published',
      input_summary: `resolve prediction ${record.prediction_id}`,
      output_summary: `brier=${Number(record.brier_score).toFixed(6)}`,
      confidence_score: 1,
      risk_level: 'low',
      downstream_events: [event.id],
      session_id: correlationId,
    });
  }

  async assertOrdinaryUserCannotResolve(predictionId: string): Promise<boolean> {
    try {
      await db.query(
        `UPDATE prediction_ledger
            SET resolved = true,
                resolved_outcome = true,
                resolved_at = NOW(),
                resolved_by_service = 'ordinary-user-should-fail'
          WHERE prediction_id = $1`,
        [predictionId]
      );
      return false;
    } catch (error) {
      return String(error).includes('only resolution_service may resolve predictions');
    }
  }

  async ensureServiceActor(name: string, scopes: string[]): Promise<string> {
    const existing = await db.query<{ id: string }>(
      `SELECT id FROM actors WHERE actor_type = 'service' AND name = $1 AND status = 'active' LIMIT 1`,
      [name]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0].id;
    const created = await db.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ created_by: 'LedgerResolutionService' })]
    );
    await db.query(
      `INSERT INTO service_identities (actor_id, service_name, scopes)
       VALUES ($1,$2,$3::jsonb)
       ON CONFLICT (actor_id) DO NOTHING`,
      [created.rows[0].id, name, JSON.stringify(scopes)]
    );
    return created.rows[0].id;
  }

  private validateRegistration(input: RegisterPredictionInput): void {
    if (input.prediction_id && !isUuid(input.prediction_id)) throw new Error('prediction_id must be a UUID');
    requireText(input.claim, 'claim');
    clampProbability(input.probability);
    requireText(input.producing_agent_id, 'producing_agent_id');
    requireText(input.producing_prompt_version, 'producing_prompt_version');
    requireText(input.resolution_criterion, 'resolution_criterion');
    requireText(input.ground_truth_source, 'ground_truth_source');
    requireText(input.domain, 'domain');
    if (!['short', 'medium', 'long'].includes(input.horizon_class)) throw new Error('invalid horizon_class');
  }
}

export const ledgerResolutionService = new LedgerResolutionService();
