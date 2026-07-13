/**
 * KafkaJS client — singleton producer + consumer factory.
 * Brokers from KAFKA_BROKERS env var (default: localhost:9092).
 */
import { Kafka, Producer, Consumer, CompressionTypes, logLevel } from 'kafkajs';

const brokers = (process.env.KAFKA_BROKERS ?? 'localhost:9092').split(',');
const retries = Number(process.env.KAFKA_RETRIES ?? 5);
const initialRetryTime = Number(process.env.KAFKA_INITIAL_RETRY_MS ?? 300);
const factor = Number(process.env.KAFKA_RETRY_FACTOR ?? 0.2);
const multiplier = Number(process.env.KAFKA_RETRY_MULTIPLIER ?? 2);

export const kafka = new Kafka({
  clientId: 'agentco-backend',
  brokers,
  logLevel: logLevel.WARN,
  retry: { retries, initialRetryTime, factor, multiplier },
});

let _producer: Producer | null = null;

export async function getProducer(): Promise<Producer> {
  if (!_producer) {
    const producer = kafka.producer({
      allowAutoTopicCreation: true,
      transactionTimeout: 30000,
    });
    try {
      await producer.connect();
      _producer = producer;
    } catch (error) {
      await producer.disconnect().catch(() => undefined);
      throw error;
    }
  }
  return _producer;
}

export function createConsumer(groupId: string): Consumer {
  return kafka.consumer({ groupId, sessionTimeout: 30000 });
}

export async function checkKafkaHealth(): Promise<void> {
  const admin = kafka.admin();
  try {
    await admin.connect();
    await admin.fetchTopicMetadata();
  } finally {
    await admin.disconnect().catch(() => undefined);
  }
}

export async function disconnectProducer(): Promise<void> {
  if (_producer) {
    try {
      await _producer.disconnect();
      _producer = null;
    } catch (err) {
      console.error('Error disconnecting Kafka producer:', err);
    }
  }
}

export { CompressionTypes };
