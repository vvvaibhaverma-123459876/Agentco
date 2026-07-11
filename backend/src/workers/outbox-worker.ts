import { disconnectProducer, getProducer } from '../db/kafka';
import { eventBus } from '../services/event-bus.service';
import { OutboxEnvelope, OutboxPublisher, transactionalOutbox } from '../services/transactional-outbox.service';
import { shutdownRuntimeResources } from '../runtime/shutdown';

type RelayResult = { published: number; failed: number; dead_lettered: number };

export interface OutboxWorkerOptions {
  pollIntervalMs: number;
  batchSize: number;
  maxAttempts: number;
  workerId: string;
  once: boolean;
}

export interface OutboxWorkerDependencies {
  publisher: OutboxPublisher;
  relayEventLog: (publisher: OutboxPublisher, options: { limit: number; workerId: string; maxAttempts: number }) => Promise<RelayResult>;
  relayEventBus: (options: { limit: number; workerId: string; maxAttempts: number }) => Promise<RelayResult>;
  shutdown: () => Promise<void>;
}

export interface OutboxWorkerRunResult {
  eventLog: RelayResult;
  eventBus: RelayResult;
}

function positiveIntEnv(name: string, fallback: number): number {
  const parsed = Number(process.env[name]);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

const kafkaPublisher: OutboxPublisher = {
  async publish(topic: string, envelope: OutboxEnvelope): Promise<void> {
    const producer = await getProducer();
    await producer.send({
      topic,
      messages: [{ key: envelope.event_id, value: JSON.stringify(envelope) }],
    });
  },
};

const DEFAULT_OPTIONS: OutboxWorkerOptions = {
  pollIntervalMs: positiveIntEnv('AGENTCO_OUTBOX_WORKER_POLL_MS', 1000),
  batchSize: positiveIntEnv('AGENTCO_OUTBOX_WORKER_BATCH_SIZE', 50),
  maxAttempts: positiveIntEnv('AGENTCO_OUTBOX_WORKER_MAX_ATTEMPTS', 5),
  workerId: process.env.AGENTCO_OUTBOX_WORKER_ID || `outbox-worker-${process.pid}`,
  once: process.env.AGENTCO_OUTBOX_WORKER_ONCE === '1',
};

const DEFAULT_DEPENDENCIES: OutboxWorkerDependencies = {
  publisher: kafkaPublisher,
  relayEventLog: (publisher, options) => transactionalOutbox.relayBatch(publisher, options),
  relayEventBus: options => eventBus.relayOutboxBatch(options),
  shutdown: async () => {
    await disconnectProducer();
    await shutdownRuntimeResources({ closeDb: true });
  },
};

export class OutboxWorker {
  private stopping = false;

  constructor(
    private options: OutboxWorkerOptions = DEFAULT_OPTIONS,
    private dependencies: OutboxWorkerDependencies = DEFAULT_DEPENDENCIES,
  ) {}

  stop(): void {
    this.stopping = true;
  }

  async runOnce(): Promise<OutboxWorkerRunResult> {
    const relayOptions = {
      limit: this.options.batchSize,
      workerId: this.options.workerId,
      maxAttempts: this.options.maxAttempts,
    };
    const eventLog = await this.dependencies.relayEventLog(this.dependencies.publisher, relayOptions);
    const eventBus = await this.dependencies.relayEventBus(relayOptions);
    return { eventLog, eventBus };
  }

  async loop(): Promise<void> {
    process.once('SIGTERM', () => this.stop());
    process.once('SIGINT', () => this.stop());
    try {
      do {
        const result = await this.runOnce();
        console.log('[outbox-worker] relay batch', JSON.stringify(result));
        if (this.options.once) return;
        await sleep(this.options.pollIntervalMs);
      } while (!this.stopping);
    } finally {
      await this.dependencies.shutdown();
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

if (require.main === module) {
  new OutboxWorker().loop().catch(error => {
    console.error('[outbox-worker] fatal error', error);
    process.exit(1);
  });
}
