import { describe, expect, test } from '@jest/globals';
import { civilizationSchedulerService } from '../src/services/civilization-scheduler.service';

describe('CivilizationSchedulerService', () => {
  test('runs a bounded scheduler tick and can start/stop without leaving timers active', async () => {
    civilizationSchedulerService.stop();

    const tick = await civilizationSchedulerService.runOnce('jest_scheduler_l14_runtime');
    expect(tick.status).toBe('passed');
    expect(civilizationSchedulerService.status().tickCount).toBeGreaterThanOrEqual(1);
    expect(civilizationSchedulerService.status().lastStatus).toBe('passed');

    const started = civilizationSchedulerService.start(1_000);
    expect(started.running).toBe(true);
    expect(started.intervalMs).toBe(1_000);

    const stopped = civilizationSchedulerService.stop();
    expect(stopped.running).toBe(false);
  });
});
