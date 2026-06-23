/**
 * Autonomy Prometheus Metrics Service
 * ===================================
 * Tracks specialist performance and system health with Prometheus metrics.
 */

import * as prometheus from 'prom-client';

export class AutonomyMetricsService {
  // Counters
  private specialistSpawnCounter: prometheus.Counter;
  private specialistActionCounter: prometheus.Counter;
  private specialistErrorCounter: prometheus.Counter;
  private specialistBudgetExceededCounter: prometheus.Counter;

  // Histograms
  private specialistExecutionDuration: prometheus.Histogram;
  private specialistResponseTime: prometheus.Histogram;

  // Gauges
  private activeSpecialistsGauge: prometheus.Gauge;
  private specialistTokenUsageGauge: prometheus.Gauge;

  constructor() {
    // Initialize metrics with labels
    this.specialistSpawnCounter = new prometheus.Counter({
      name: 'specialist_spawn_total',
      help: 'Total specialist agents spawned',
      labelNames: ['role', 'status'],
    });

    this.specialistActionCounter = new prometheus.Counter({
      name: 'specialist_action_total',
      help: 'Total actions executed by specialists',
      labelNames: ['role', 'action_type', 'status'],
    });

    this.specialistErrorCounter = new prometheus.Counter({
      name: 'specialist_errors_total',
      help: 'Total specialist errors',
      labelNames: ['role', 'error_type'],
    });

    this.specialistBudgetExceededCounter = new prometheus.Counter({
      name: 'specialist_budget_exceeded_total',
      help: 'Total budget exceeded errors',
      labelNames: ['role', 'budget_type'],
    });

    // Execution duration histogram (0.1s to 30s buckets)
    this.specialistExecutionDuration = new prometheus.Histogram({
      name: 'specialist_execution_duration_seconds',
      help: 'Specialist action execution time in seconds',
      labelNames: ['role', 'action_type'],
      buckets: [0.1, 0.5, 1, 2, 5, 10, 30],
    });

    // Response time histogram (0.01s to 10s buckets)
    this.specialistResponseTime = new prometheus.Histogram({
      name: 'specialist_response_time_seconds',
      help: 'Specialist HTTP response time in seconds',
      labelNames: ['role', 'endpoint'],
      buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
    });

    // Active specialists gauge
    this.activeSpecialistsGauge = new prometheus.Gauge({
      name: 'specialist_active_count',
      help: 'Current number of active specialist processes',
      labelNames: ['role'],
    });

    // Token usage gauge
    this.specialistTokenUsageGauge = new prometheus.Gauge({
      name: 'specialist_tokens_used',
      help: 'Total tokens used by specialist',
      labelNames: ['specialist_id', 'role'],
    });
  }

  /**
   * Record specialist spawn
   */
  recordSpecialistSpawn(role: string, success: boolean): void {
    this.specialistSpawnCounter.inc({
      role,
      status: success ? 'success' : 'failure',
    });
  }

  /**
   * Record specialist action execution
   */
  recordSpecialistAction(
    role: string,
    actionType: string,
    status: 'success' | 'failed' | 'timeout',
    durationSeconds: number
  ): void {
    this.specialistActionCounter.inc({
      role,
      action_type: actionType,
      status,
    });

    this.specialistExecutionDuration
      .labels(role, actionType)
      .observe(durationSeconds);
  }

  /**
   * Record specialist error
   */
  recordSpecialistError(role: string, errorType: string): void {
    this.specialistErrorCounter.inc({
      role,
      error_type: errorType,
    });
  }

  /**
   * Record budget exceeded
   */
  recordBudgetExceeded(role: string, budgetType: 'tokens' | 'iterations' | 'time'): void {
    this.specialistBudgetExceededCounter.inc({
      role,
      budget_type: budgetType,
    });
  }

  /**
   * Record HTTP response time
   */
  recordResponseTime(role: string, endpoint: string, durationSeconds: number): void {
    this.specialistResponseTime
      .labels(role, endpoint)
      .observe(durationSeconds);
  }

  /**
   * Update active specialists count
   */
  updateActiveSpecialists(role: string, count: number): void {
    this.activeSpecialistsGauge.set({ role }, count);
  }

  /**
   * Update token usage for specialist
   */
  updateTokenUsage(specialistId: string, role: string, tokensUsed: number): void {
    this.specialistTokenUsageGauge.set(
      { specialist_id: specialistId, role },
      tokensUsed
    );
  }

  /**
   * Get Prometheus metrics in text format
   */
  async getMetrics(): Promise<string> {
    return await prometheus.register.metrics();
  }

  /**
   * Get metrics content type
   */
  getContentType(): string {
    return prometheus.register.contentType;
  }
}

// Export singleton instance
export const metricsService = new AutonomyMetricsService();
