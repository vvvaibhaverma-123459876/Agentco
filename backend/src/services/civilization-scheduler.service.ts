import {
  CivilizationReachabilityTick,
  civilizationRuntimeService,
} from './civilization-runtime.service';

export interface CivilizationSchedulerStatus {
  running: boolean;
  intervalMs: number;
  tickCount: number;
  lastTickAt: string | null;
  lastStatus: 'passed' | 'failed' | null;
  lastError: string | null;
}

export class CivilizationSchedulerService {
  private timer: NodeJS.Timeout | null = null;
  private intervalMs = 60_000;
  private tickCount = 0;
  private lastTickAt: string | null = null;
  private lastStatus: 'passed' | 'failed' | null = null;
  private lastError: string | null = null;

  status(): CivilizationSchedulerStatus {
    return {
      running: this.timer !== null,
      intervalMs: this.intervalMs,
      tickCount: this.tickCount,
      lastTickAt: this.lastTickAt,
      lastStatus: this.lastStatus,
      lastError: this.lastError,
    };
  }

  async runOnce(runtimeMode = 'scheduler_l14_runtime'): Promise<CivilizationReachabilityTick> {
    try {
      const tick = await civilizationRuntimeService.runReachabilityTick(runtimeMode);
      this.tickCount += 1;
      this.lastTickAt = new Date().toISOString();
      this.lastStatus = tick.status;
      this.lastError = null;
      return tick;
    } catch (error) {
      this.tickCount += 1;
      this.lastTickAt = new Date().toISOString();
      this.lastStatus = 'failed';
      this.lastError = error instanceof Error ? error.message : String(error);
      throw error;
    }
  }

  start(intervalMs = 60_000): CivilizationSchedulerStatus {
    if (!Number.isFinite(intervalMs) || intervalMs < 1_000) {
      throw new Error('civilization scheduler interval must be at least 1000ms');
    }
    this.intervalMs = intervalMs;
    if (this.timer) return this.status();

    this.timer = setInterval(() => {
      void this.runOnce('scheduled_l14_runtime').catch(() => {
        // lastError is recorded in runOnce; keep the scheduler alive.
      });
    }, this.intervalMs);
    this.timer.unref?.();
    return this.status();
  }

  stop(): CivilizationSchedulerStatus {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    return this.status();
  }
}

export const civilizationSchedulerService = new CivilizationSchedulerService();
