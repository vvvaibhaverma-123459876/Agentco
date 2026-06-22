/**
 * Prometheus metrics service for backend monitoring.
 * Exposes metrics on GET /metrics for Prometheus scraping.
 */

interface Counter {
  name: string;
  help: string;
  value: number;
  labels?: Record<string, string>;
}

interface Gauge {
  name: string;
  help: string;
  value: number;
  labels?: Record<string, string>;
}

interface Histogram {
  name: string;
  help: string;
  buckets: Record<string, number>;
  sum: number;
  count: number;
  labels?: Record<string, string>;
}

const metrics = {
  http_requests_total: new Map<string, number>(),
  http_request_duration_seconds: new Map<string, { sum: number; count: number; buckets: number[] }>(),
  db_queries_total: new Map<string, number>(),
  db_query_duration_seconds: new Map<string, { sum: number; count: number }>(),
  kafka_messages_produced_total: new Map<string, number>(),
  errors_total: new Map<string, number>(),
};

const LATENCY_BUCKETS = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5];

function getKey(name: string, labels?: Record<string, string>): string {
  if (!labels) return name;
  const parts = Object.entries(labels)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}="${v}"`)
    .join(",");
  return `${name}{${parts}}`;
}

export const metricsService = {
  recordHttpRequest(method: string, path: string, statusCode: number, duration: number) {
    const key = `method="${method}",path="${path}",status="${statusCode}"`;
    metrics.http_requests_total.set(key, (metrics.http_requests_total.get(key) || 0) + 1);

    const histKey = `method="${method}",path="${path}"`;
    const hist = metrics.http_request_duration_seconds.get(histKey) || {
      sum: 0,
      count: 0,
      buckets: LATENCY_BUCKETS.map(() => 0),
    };
    hist.sum += duration;
    hist.count += 1;
    for (let i = 0; i < LATENCY_BUCKETS.length; i++) {
      if (duration <= LATENCY_BUCKETS[i]) hist.buckets[i]++;
    }
    metrics.http_request_duration_seconds.set(histKey, hist);
  },

  recordDbQuery(query: string, duration: number, error?: boolean) {
    if (!error) {
      const key = `query="${query.slice(0, 50)}"`;
      metrics.db_queries_total.set(key, (metrics.db_queries_total.get(key) || 0) + 1);

      const histKey = key;
      const hist = metrics.db_query_duration_seconds.get(histKey) || { sum: 0, count: 0 };
      hist.sum += duration;
      hist.count += 1;
      metrics.db_query_duration_seconds.set(histKey, hist);
    }

    if (error) {
      const key = 'type="database"';
      metrics.errors_total.set(key, (metrics.errors_total.get(key) || 0) + 1);
    }
  },

  recordKafkaMessage(topic: string) {
    const key = `topic="${topic}"`;
    metrics.kafka_messages_produced_total.set(key, (metrics.kafka_messages_produced_total.get(key) || 0) + 1);
  },

  recordError(errorType: string) {
    const key = `type="${errorType}"`;
    metrics.errors_total.set(key, (metrics.errors_total.get(key) || 0) + 1);
  },

  /**
   * Render metrics in Prometheus text format (OpenMetrics).
   */
  render(): string {
    const lines: string[] = [];

    lines.push("# HELP http_requests_total Total HTTP requests");
    lines.push("# TYPE http_requests_total counter");
    for (const [key, value] of metrics.http_requests_total) {
      lines.push(`http_requests_total{${key}} ${value}`);
    }

    lines.push("# HELP http_request_duration_seconds HTTP request latency in seconds");
    lines.push("# TYPE http_request_duration_seconds histogram");
    for (const [key, hist] of metrics.http_request_duration_seconds) {
      for (let i = 0; i < LATENCY_BUCKETS.length; i++) {
        lines.push(`http_request_duration_seconds_bucket{${key},le="${LATENCY_BUCKETS[i]}"} ${hist.buckets[i]}`);
      }
      lines.push(`http_request_duration_seconds_bucket{${key},le="+Inf"} ${hist.count}`);
      lines.push(`http_request_duration_seconds_sum{${key}} ${hist.sum}`);
      lines.push(`http_request_duration_seconds_count{${key}} ${hist.count}`);
    }

    lines.push("# HELP db_queries_total Total database queries");
    lines.push("# TYPE db_queries_total counter");
    for (const [key, value] of metrics.db_queries_total) {
      lines.push(`db_queries_total{${key}} ${value}`);
    }

    lines.push("# HELP kafka_messages_produced_total Total Kafka messages produced");
    lines.push("# TYPE kafka_messages_produced_total counter");
    for (const [key, value] of metrics.kafka_messages_produced_total) {
      lines.push(`kafka_messages_produced_total{${key}} ${value}`);
    }

    lines.push("# HELP errors_total Total errors");
    lines.push("# TYPE errors_total counter");
    for (const [key, value] of metrics.errors_total) {
      lines.push(`errors_total{${key}} ${value}`);
    }

    lines.push("");
    return lines.join("\n");
  },
};
