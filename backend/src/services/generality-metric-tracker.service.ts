import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';

export interface DomainMetricInput {
  domain_key: string;
  score: number;
  evidence?: Record<string, unknown>;
}

export interface RecordGeneralityRunInput {
  benchmark_name: string;
  mode: string;
  baseline_score: number;
  domains: DomainMetricInput[];
  metadata?: Record<string, unknown>;
  correlation_id?: string;
}

export interface GeneralityMetricRun {
  id: string;
  benchmark_name: string;
  mode: string;
  aggregate_score: string | number;
  baseline_score: string | number;
  domains_evaluated: number;
  domains_above_baseline: number;
  generality_score: string | number;
  event_log_id: string | null;
  metadata_json: Record<string, unknown>;
}

function normalizeDomainKey(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/\s+/g, '_');
  if (!/^[a-z0-9][a-z0-9_-]{2,80}$/.test(normalized)) {
    throw new Error('domain_key must be 3-81 chars of lowercase letters, numbers, underscores, or hyphens');
  }
  return normalized;
}

function validateScore(value: number, field: string): void {
  if (!Number.isFinite(value) || value < 0 || value > 1) {
    throw new Error(`${field} must be between 0 and 1`);
  }
}

export class GeneralityMetricTrackerService {
  async recordRun(input: RecordGeneralityRunInput): Promise<GeneralityMetricRun> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.recordRunWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async recordRunWithClient(client: PoolClient, input: RecordGeneralityRunInput): Promise<GeneralityMetricRun> {
    if (!input.benchmark_name.trim()) throw new Error('benchmark_name is required');
    if (!input.mode.trim()) throw new Error('mode is required');
    validateScore(input.baseline_score, 'baseline_score');
    if (!Array.isArray(input.domains) || input.domains.length === 0) {
      throw new Error('at least one domain score is required');
    }

    const domains = input.domains.map((domain) => {
      const domainKey = normalizeDomainKey(domain.domain_key);
      validateScore(domain.score, `score for ${domainKey}`);
      return { ...domain, domain_key: domainKey };
    });
    if (new Set(domains.map((domain) => domain.domain_key)).size !== domains.length) {
      throw new Error('domain scores must not contain duplicates');
    }

    const registeredDomains = await client.query<{ id: string; domain_key: string }>(
      `SELECT id, domain_key
         FROM domain_registry
        WHERE domain_key = ANY($1::text[])
          AND status = 'active'`,
      [domains.map((domain) => domain.domain_key)]
    );
    const domainIds = new Map(registeredDomains.rows.map((row) => [row.domain_key, row.id]));
    const missing = domains.filter((domain) => !domainIds.has(domain.domain_key)).map((domain) => domain.domain_key);
    if (missing.length > 0) {
      throw new Error(`active registered domains required: ${missing.join(', ')}`);
    }

    const aggregate = domains.reduce((sum, domain) => sum + domain.score, 0) / domains.length;
    const aboveBaseline = domains.filter((domain) => domain.score > input.baseline_score).length;
    const generalityScore = aboveBaseline / domains.length;
    const runId = crypto.randomUUID();
    const actorId = await this.ensureServiceActor(client);
    const event = await eventLog.appendWithClient(client, {
      event_type: 'generality.metric.recorded',
      actor_id: actorId,
      object_type: 'generality_metric_run',
      object_id: runId,
      correlation_id: input.correlation_id ?? crypto.randomUUID(),
      payload: {
        benchmark_name: input.benchmark_name,
        mode: input.mode,
        aggregate_score: Number(aggregate.toFixed(6)),
        baseline_score: input.baseline_score,
        domains_evaluated: domains.length,
        domains_above_baseline: aboveBaseline,
        generality_score: Number(generalityScore.toFixed(6)),
      },
    });

    const inserted = await client.query<GeneralityMetricRun>(
      `INSERT INTO generality_metric_runs
         (id, benchmark_name, mode, aggregate_score, baseline_score, domains_evaluated,
          domains_above_baseline, generality_score, event_log_id, metadata_json)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
       RETURNING id, benchmark_name, mode, aggregate_score, baseline_score,
                 domains_evaluated, domains_above_baseline, generality_score,
                 event_log_id, metadata_json`,
      [
        runId,
        input.benchmark_name,
        input.mode,
        Number(aggregate.toFixed(6)),
        input.baseline_score,
        domains.length,
        aboveBaseline,
        Number(generalityScore.toFixed(6)),
        event.id,
        JSON.stringify(input.metadata ?? {}),
      ]
    );

    for (const domain of domains) {
      await client.query(
        `INSERT INTO generality_domain_scores
           (run_id, domain_id, domain_key, score, baseline_score, beats_baseline, evidence_json)
         VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb)`,
        [
          runId,
          domainIds.get(domain.domain_key),
          domain.domain_key,
          domain.score,
          input.baseline_score,
          domain.score > input.baseline_score,
          JSON.stringify(domain.evidence ?? {}),
        ]
      );
    }

    return inserted.rows[0];
  }

  private async ensureServiceActor(client: PoolClient): Promise<string> {
    const name = 'agentco-generality-metric-tracker';
    const actor = await client.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ created_by: 'GeneralityMetricTrackerService' })]
    );
    await client.query(
      `INSERT INTO service_identities (actor_id, service_name, scopes)
       VALUES ($1,$2,$3::jsonb)
       ON CONFLICT (actor_id) DO NOTHING`,
      [actor.rows[0].id, name, JSON.stringify(['generality.record'])]
    );
    return actor.rows[0].id;
  }
}

export const generalityMetricTracker = new GeneralityMetricTrackerService();
