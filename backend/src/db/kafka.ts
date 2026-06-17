/**
 * KafkaJS client — singleton producer + consumer factory.
 * Brokers from KAFKA_BROKERS env var (default: localhost:9092).
 */
import { Kafka, Producer, Consumer, CompressionTypes, logLevel } from 'kafkajs';

const brokers = (process.env.KAFKA_BROKERS ?? 'localhost:9092').split(',');

export const kafka = new Kafka({
  clientId: 'agentco-backend',
  brokers,
  logLevel: logLevel.WARN,
  retry: { retries: 5, initialRetryTime: 300, factor: 2 },
});

let _producer: Producer | null = null;

export async function getProducer(): Promise<Producer> {
  if (!_producer) {
    _producer = kafka.producer({
      allowAutoTopicCreation: true,
      transactionTimeout: 30000,
    });
    await _producer.connect();
  }
  return _producer;
}

export function createConsumer(groupId: string): Consumer {
  return kafka.consumer({ groupId, sessionTimeout: 30000 });
}

export { CompressionTypes };
