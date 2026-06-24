import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';
import * as crypto from 'crypto';

/**
 * Perception Event Service
 *
 * Handles persistence, deduplication, and audit of perception events.
 * All external environment data goes through this service.
 */

export interface PerceptionEventInput {
  sourceId: string;
  eventType: string;
  sourceUri: string;
  sourceFingerprint: string;
  observedAt: Date;
  payloadJson: Record<string, any>;
  confidence: number;
  provenanceJson: Record<string, any>;
  traceId?: string;
  taskId?: string;
}

export interface PerceptionArtifactInput {
  eventId: string;
  artifactType: string;
  storageUri: string;
  contentSizeBytes?: number;
  mimeType?: string;
}

export class PerceptionService {
  /**
   * Check if event fingerprint already exists (deduplication)
   */
  async checkDuplicate(fingerprint: string): Promise<{exists: boolean; eventId?: string}> {
    const result = await db.query(
      `SELECT id FROM perception_events WHERE source_fingerprint = $1 LIMIT 1`,
      [fingerprint]
    );

    if (result.rows.length > 0) {
      return {
        exists: true,
        eventId: result.rows[0].id,
      };
    }

    return {
      exists: false,
    };
  }

  /**
   * Persist perception event to database
   */
  async persistEvent(input: PerceptionEventInput): Promise<{eventId: string; isDuplicate: boolean}> {
    // Check for duplicate first
    const dup = await this.checkDuplicate(input.sourceFingerprint);
    if (dup.exists) {
      console.log(`[PERCEPTION] Duplicate fingerprint detected: ${input.sourceFingerprint}`);
      return {
        eventId: dup.eventId!,
        isDuplicate: true,
      };
    }

    // Insert new event
    const eventId = uuidv4();
    const result = await db.query(
      `INSERT INTO perception_events (
        id, source_id, event_type, source_uri, source_fingerprint,
        observed_at, fetched_at, payload_json, confidence,
        provenance_json, trace_id, task_id, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, $8, $9, $10, $11, NOW())
       RETURNING id`,
      [
        eventId,
        input.sourceId,
        input.eventType,
        input.sourceUri,
        input.sourceFingerprint,
        input.observedAt.toISOString(),
        JSON.stringify(input.payloadJson),
        input.confidence,
        JSON.stringify(input.provenanceJson),
        input.traceId,
        input.taskId,
      ]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to insert perception event');
    }

    console.log(`[PERCEPTION] Event persisted: ${eventId} (fingerprint: ${input.sourceFingerprint.substring(0, 8)}...)`);

    return {
      eventId: result.rows[0].id,
      isDuplicate: false,
    };
  }

  /**
   * Create artifact hash and persist artifact record
   */
  async createArtifact(input: PerceptionArtifactInput): Promise<{artifactId: string; artifactHash: string}> {
    const artifactId = uuidv4();

    // Create deterministic hash from storage URI + type (simulating content hash)
    const contentHash = crypto
      .createHash('sha256')
      .update(`${input.storageUri}:${input.artifactType}`)
      .digest('hex');

    const result = await db.query(
      `INSERT INTO perception_artifacts (
        id, event_id, artifact_type, artifact_hash, storage_uri,
        content_size_bytes, mime_type, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
       RETURNING id`,
      [
        artifactId,
        input.eventId,
        input.artifactType,
        contentHash,
        input.storageUri,
        input.contentSizeBytes,
        input.mimeType,
      ]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to insert perception artifact');
    }

    console.log(`[PERCEPTION] Artifact created: ${artifactId} (hash: ${contentHash.substring(0, 8)}...)`);

    return {
      artifactId: result.rows[0].id,
      artifactHash: contentHash,
    };
  }

  /**
   * Record adapter run for audit trail
   */
  async recordAdapterRun(params: {
    sourceId: string;
    adapterVersion?: string;
    status: 'success' | 'partial_success' | 'failure';
    eventsFetched: number;
    artifactsStored: number;
    errorMessage?: string;
    durationMs: number;
    traceId?: string;
  }): Promise<string> {
    const runId = uuidv4();

    const result = await db.query(
      `INSERT INTO perception_adapter_runs (
        id, source_id, adapter_version, status,
        events_fetched, artifacts_stored, error_message,
        duration_ms, trace_id, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
       RETURNING id`,
      [
        runId,
        params.sourceId,
        params.adapterVersion,
        params.status,
        params.eventsFetched,
        params.artifactsStored,
        params.errorMessage,
        params.durationMs,
        params.traceId,
      ]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to record adapter run');
    }

    console.log(`[PERCEPTION] Adapter run recorded: ${params.status} (${params.eventsFetched} events, ${params.artifactsStored} artifacts)`);

    return result.rows[0].id;
  }

  /**
   * Get perception event by ID
   */
  async getEvent(eventId: string): Promise<any> {
    const result = await db.query(
      `SELECT * FROM perception_events WHERE id = $1`,
      [eventId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    return result.rows[0];
  }

  /**
   * Get artifact by event ID
   */
  async getArtifact(eventId: string): Promise<any> {
    const result = await db.query(
      `SELECT * FROM perception_artifacts WHERE event_id = $1 LIMIT 1`,
      [eventId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    return result.rows[0];
  }

  /**
   * List perception sources
   */
  async listSources(filters: {active?: boolean; sourceType?: string} = {}): Promise<any[]> {
    let query = 'SELECT * FROM perception_sources WHERE 1=1';
    const params: any[] = [];
    let paramIdx = 1;

    if (filters.active !== undefined) {
      query += ` AND active = $${paramIdx}`;
      params.push(filters.active);
      paramIdx++;
    }

    if (filters.sourceType) {
      query += ` AND source_type = $${paramIdx}`;
      params.push(filters.sourceType);
      paramIdx++;
    }

    query += ' ORDER BY created_at DESC';

    const result = await db.query(query, params);
    return result.rows;
  }
}

export const perception = new PerceptionService();
