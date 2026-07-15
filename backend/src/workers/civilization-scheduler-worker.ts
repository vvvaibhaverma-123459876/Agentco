import { civilizationOs, TickResult } from '../services/civilization-os.service';
import { shutdownRuntimeResources } from '../runtime/shutdown';

/**
 * Civilization scheduler worker (build phase C14).
 *
 * Runs the civilization operating-system coordinator as a standalone,
 * deployable daemon. Leader election lives in `civilizationOs.tick()` (a
 * Postgres advisory lock), so multiple replicas of this worker are safe: only
 * one ticks at a time. The loop is bounded per-tick, records structured
 * heartbeats, and shuts down gracefully on SIGTERM/SIGINT.
 */

export interface SchedulerWorkerOptions {
  pollIntervalMs: number;
  workerId: string;
}

const DEFAULT_OPTIONS: SchedulerWorkerOptions = {
  pollIntervalMs: Number(process.env.CIVILIZATION_OS_POLL_MS || 5000),
  workerId: process.env.CIVILIZATION_OS_WORKER_ID || `civ-os-${process.pid}`,
};

export class CivilizationSchedulerWorker {
  private stopping = false;

  constructor(private options: SchedulerWorkerOptions = DEFAULT_OPTIONS) {}

  stop(): void { this.stopping = true; }

  async runOnce(): Promise<TickResult> {
    return civilizationOs.tick();
  }

  async loop(): Promise<void> {
    process.on('SIGTERM', () => this.stop());
    process.on('SIGINT', () => this.stop());
    console.log(`[civ-os] scheduler worker ${this.options.workerId} started (poll ${this.options.pollIntervalMs}ms)`);
    while (!this.stopping) {
      try {
        const tick = await this.runOnce();
        console.log(JSON.stringify({
          worker: this.options.workerId, tick: tick.tick_number, leader: tick.was_leader,
          mode: tick.mode, routed: tick.work_routed, expired: tick.emergencies_expired,
          skipped: tick.skipped_reason ?? null,
        }));
      } catch (error) {
        console.error(`[civ-os] tick error: ${error instanceof Error ? error.message : String(error)}`);
      }
      await sleep(this.options.pollIntervalMs);
    }
    console.log(`[civ-os] scheduler worker ${this.options.workerId} stopping`);
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

if (require.main === module) {
  const worker = new CivilizationSchedulerWorker();
  worker.loop()
    .catch(error => { console.error('[civ-os] fatal error', error); process.exit(1); })
    .finally(() => shutdownRuntimeResources({ closeDb: true }).catch(() => undefined));
}
