import { OutboxWorker, OutboxWorkerDependencies, OutboxWorkerOptions } from '../src/workers/outbox-worker';

function options(overrides: Partial<OutboxWorkerOptions> = {}): OutboxWorkerOptions {
  return {
    pollIntervalMs: 1,
    batchSize: 7,
    maxAttempts: 3,
    workerId: 'test-outbox-worker',
    once: true,
    ...overrides,
  };
}

function dependencies(): OutboxWorkerDependencies {
  return {
    publisher: { publish: jest.fn() },
    relayEventLog: jest.fn().mockResolvedValue({ published: 1, failed: 0, dead_lettered: 0 }),
    relayEventBus: jest.fn().mockResolvedValue({ published: 2, failed: 1, dead_lettered: 0 }),
    shutdown: jest.fn().mockResolvedValue(undefined),
  };
}

describe('OutboxWorker', () => {
  test('runOnce drains canonical and event-bus outboxes with shared bounded options', async () => {
    const deps = dependencies();
    const worker = new OutboxWorker(options(), deps);

    const result = await worker.runOnce();

    expect(result).toEqual({
      eventLog: { published: 1, failed: 0, dead_lettered: 0 },
      eventBus: { published: 2, failed: 1, dead_lettered: 0 },
    });
    expect(deps.relayEventLog).toHaveBeenCalledWith(deps.publisher, {
      limit: 7,
      workerId: 'test-outbox-worker',
      maxAttempts: 3,
    });
    expect(deps.relayEventBus).toHaveBeenCalledWith({
      limit: 7,
      workerId: 'test-outbox-worker',
      maxAttempts: 3,
    });
  });

  test('loop in once mode runs exactly one batch and closes runtime resources', async () => {
    const deps = dependencies();
    const worker = new OutboxWorker(options({ once: true }), deps);

    await worker.loop();

    expect(deps.relayEventLog).toHaveBeenCalledTimes(1);
    expect(deps.relayEventBus).toHaveBeenCalledTimes(1);
    expect(deps.shutdown).toHaveBeenCalledTimes(1);
  });
});
