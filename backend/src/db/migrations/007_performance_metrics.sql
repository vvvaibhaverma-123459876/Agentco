-- Per-agent performance metrics: accuracy, latency, cost-per-task over time
CREATE TABLE IF NOT EXISTS performance_metrics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id            VARCHAR(64) NOT NULL REFERENCES agent_state(agent_id),
    period_start        TIMESTAMPTZ NOT NULL,
    period_end          TIMESTAMPTZ NOT NULL,
    task_count          INTEGER NOT NULL DEFAULT 0,
    error_count         INTEGER NOT NULL DEFAULT 0,
    error_rate          DECIMAL(6,4) GENERATED ALWAYS AS (
                            CASE WHEN task_count > 0
                            THEN error_count::DECIMAL / task_count
                            ELSE 0 END
                        ) STORED,
    avg_latency_ms      INTEGER,
    p50_latency_ms      INTEGER,
    p95_latency_ms      INTEGER,
    p99_latency_ms      INTEGER,
    avg_confidence      DECIMAL(4,3),
    cost_per_task_usd   DECIMAL(10,6),
    total_cost_usd      DECIMAL(10,4),
    escalation_count    INTEGER NOT NULL DEFAULT 0,
    false_escalations   INTEGER NOT NULL DEFAULT 0,
    missed_escalations  INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_perf_metrics_agent ON performance_metrics(agent_id);
CREATE INDEX idx_perf_metrics_period ON performance_metrics(period_start DESC);
CREATE INDEX idx_perf_metrics_error_rate ON performance_metrics(error_rate);
