import * as prometheus from 'prom-client';

/**
 * Civilization observability metrics (build phase C14).
 *
 * Prometheus gauges/counters for the civilization operating system, registered
 * on prom-client's default registry so the existing `/metrics` endpoint
 * exposes them. Fed from the OS tick's status projection.
 */
class CivilizationMetricsService {
  readonly tickCounter: prometheus.Counter;
  readonly leaderTickCounter: prometheus.Counter;
  readonly heartbeatGauge: prometheus.Gauge;
  readonly missionsExecuting: prometheus.Gauge;
  readonly disputesOpen: prometheus.Gauge;
  readonly learningOpen: prometheus.Gauge;
  readonly expansionsOpen: prometheus.Gauge;
  readonly activeEmergencies: prometheus.Gauge;
  readonly reservationsExpired: prometheus.Counter;

  constructor() {
    const g = (name: string, help: string) => {
      const existing = prometheus.register.getSingleMetric(name);
      return (existing as prometheus.Gauge) ?? new prometheus.Gauge({ name, help });
    };
    const c = (name: string, help: string) => {
      const existing = prometheus.register.getSingleMetric(name);
      return (existing as prometheus.Counter) ?? new prometheus.Counter({ name, help });
    };
    this.tickCounter = c('civilization_os_ticks_total', 'Total civilization OS ticks recorded');
    this.leaderTickCounter = c('civilization_os_leader_ticks_total', 'Civilization OS ticks executed as leader');
    this.reservationsExpired = c('civilization_os_reservations_expired_total', 'Resource reservations expired by the OS sweep');
    this.heartbeatGauge = g('civilization_os_heartbeat_seconds', 'Unix time of the last civilization OS heartbeat');
    this.missionsExecuting = g('civilization_missions_executing', 'Missions currently executing');
    this.disputesOpen = g('civilization_disputes_open', 'Open judiciary cases');
    this.learningOpen = g('civilization_learning_candidates_open', 'Open learning candidates');
    this.expansionsOpen = g('civilization_expansion_proposals_open', 'Open expansion proposals');
    this.activeEmergencies = g('civilization_active_emergencies', 'Active emergency states');
  }

  recordTick(input: { was_leader: boolean; reservations_expired: number; heartbeat_epoch: number; status: Record<string, unknown> }): void {
    try {
      this.tickCounter.inc();
      if (input.was_leader) this.leaderTickCounter.inc();
      this.reservationsExpired.inc(input.reservations_expired);
      this.heartbeatGauge.set(input.heartbeat_epoch);
      const n = (k: string) => Number(input.status[k] ?? 0);
      this.missionsExecuting.set(n('missions_executing'));
      this.disputesOpen.set(n('disputes_open'));
      this.learningOpen.set(n('learning_candidates_open'));
      this.expansionsOpen.set(n('expansion_proposals_open'));
      this.activeEmergencies.set(n('active_emergencies'));
    } catch {
      // Metrics are best-effort; never fail a tick on a metrics error.
    }
  }
}

export const civilizationMetrics = new CivilizationMetricsService();
