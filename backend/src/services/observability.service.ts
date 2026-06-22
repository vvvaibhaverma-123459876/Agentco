import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface TraceContext {
  traceId: string;
  runId: string;
  taskId?: string;
  agentId?: string;
  policyVersion?: string;
  modelVersion?: string;
  artifactHash?: string;
}

export interface SpanAttribute {
  [key: string]: string | number | boolean | null;
}

export class ObservabilityService {
  /**
   * Begin a new trace
   */
  async beginTrace(context: TraceContext): Promise<string> {
    const result = await db.query(
      `SELECT begin_trace($1, $2, $3, $4, $5, $6) as trace_id`,
      [
        context.runId,
        context.taskId,
        context.agentId,
        null, // institution_id
        context.policyVersion,
        context.modelVersion,
      ]
    );

    return result.rows[0].trace_id;
  }

  /**
   * End a trace
   */
  async endTrace(traceId: string, status: 'completed' | 'failed' = 'completed'): Promise<void> {
    await db.query(`SELECT end_trace($1, $2)`, [traceId, status]);
  }

  /**
   * Record a span for an action
   */
  async recordSpan(
    traceId: string,
    spanName: string,
    spanType: string,
    durationMs: number,
    status: 'completed' | 'failed' = 'completed',
    attributes?: SpanAttribute,
    errorMessage?: string
  ): Promise<string> {
    const result = await db.query(
      `SELECT record_span($1, $2, $3, $4, $5, $6, $7) as span_id`,
      [
        traceId,
        spanName,
        spanType,
        status,
        durationMs,
        errorMessage,
        JSON.stringify(attributes ?? {}),
      ]
    );

    return result.rows[0].span_id;
  }

  /**
   * Record a metric
   */
  async recordMetric(
    traceId: string | null,
    metricName: string,
    metricValue: number,
    metricType: 'counter' | 'gauge' | 'histogram' = 'gauge',
    unit?: string,
    labels?: Record<string, string>
  ): Promise<void> {
    if (traceId) {
      await db.query(
        `SELECT record_metric($1, $2, $3, $4, $5, $6)`,
        [traceId, metricName, metricValue, metricType, unit, JSON.stringify(labels ?? {})]
      );
    } else {
      // Record without trace_id
      await db.query(
        `INSERT INTO metrics (metric_name, metric_value, metric_type, metric_unit, labels)
         VALUES ($1, $2, $3, $4, $5)`,
        [metricName, metricValue, metricType, unit, JSON.stringify(labels ?? {})]
      );
    }
  }

  /**
   * Record structured log
   */
  async log(
    traceId: string | null,
    level: 'debug' | 'info' | 'warn' | 'error',
    message: string,
    context?: Record<string, any>,
    stackTrace?: string
  ): Promise<void> {
    await db.query(
      `INSERT INTO structured_logs (trace_id, log_level, log_message, context, stack_trace)
       VALUES ($1, $2, $3, $4, $5)`,
      [
        traceId,
        level,
        message,
        JSON.stringify(context ?? {}),
        stackTrace,
      ]
    );
  }

  /**
   * Record audit event linked to trace
   */
  async auditEvent(
    traceId: string,
    eventType: string,
    actorType: string,
    actorId: string,
    subjectType: string,
    subjectId: string,
    action: string,
    reason?: string,
    severity: string = 'info'
  ): Promise<void> {
    await db.query(
      `INSERT INTO trace_audit_events (
        trace_id, event_type, actor_type, actor_id, subject_type, subject_id, action, reason, severity
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
      [
        traceId,
        eventType,
        actorType,
        actorId,
        subjectType,
        subjectId,
        action,
        reason,
        severity,
      ]
    );
  }

  /**
   * Get traces for a run
   */
  async getRunTraces(runId: string): Promise<any[]> {
    const result = await db.query(
      `SELECT trace_id, run_id, status, created_at, completed_at, metadata
       FROM trace_contexts
       WHERE run_id = $1
       ORDER BY created_at DESC`,
      [runId]
    );

    return result.rows;
  }

  /**
   * Get spans for a trace
   */
  async getTraceSpans(traceId: string): Promise<any[]> {
    const result = await db.query(
      `SELECT span_id, span_name, span_type, status, started_at, ended_at, duration_ms, error_message
       FROM spans
       WHERE trace_id = $1
       ORDER BY started_at ASC`,
      [traceId]
    );

    return result.rows;
  }

  /**
   * Compute autonomy metrics summary
   */
  async computeAutonomyMetrics(timeWindowMinutes: number = 60): Promise<Record<string, number>> {
    const cutoffTime = new Date(Date.now() - timeWindowMinutes * 60 * 1000);

    const result = await db.query(
      `SELECT
        (SELECT COUNT(*) FROM autonomy_tasks WHERE created_at > $1 AND status = 'completed') as task_success_count,
        (SELECT COUNT(*) FROM autonomy_tasks WHERE created_at > $1 AND status = 'failed') as task_failure_count,
        (SELECT COUNT(*) FROM spans WHERE created_at > $1 AND status = 'failed') as action_failure_count,
        (SELECT COUNT(*) FROM autonomy_interventions WHERE created_at > $1) as intervention_count,
        (SELECT COUNT(*) FROM rollback_events WHERE created_at > $1) as rollback_count,
        (SELECT COUNT(*) FROM eval_scorecards WHERE created_at > $1 AND promotion_eligible = true) as promotion_eligible_count
       LIMIT 1`,
      [cutoffTime]
    );

    const row = result.rows[0];
    const totalTasks = row.task_success_count + row.task_failure_count;

    return {
      task_success_rate: totalTasks > 0 ? (row.task_success_count / totalTasks) * 100 : 0,
      task_failure_rate: totalTasks > 0 ? (row.task_failure_count / totalTasks) * 100 : 0,
      tool_error_rate: row.action_failure_count,
      intervention_rate: row.intervention_count,
      rollback_rate: row.rollback_count,
      eval_promotion_rate: row.promotion_eligible_count,
    };
  }
}

export const observability = new ObservabilityService();
