/**
 * Event Bus Service — Kafka producer/consumer wrapper.
 * Every event MUST conform to the spec envelope schema.
 * HMAC-SHA256 signing on all events; consumers verify before processing.
 */
import crypto from 'crypto';

const SIGNING_KEY = process.env.EVENT_BUS_SIGNING_KEY || 'dev-key-replace-in-production';

export interface AgentEvent {
  event_id: string;
  event_type: string;
  producer_agent_id: string;
  timestamp: string;
  confidence_score: number;
  payload: Record<string, unknown>;
  correlation_id?: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  requires_ack: boolean;
  ttl_seconds?: number;
}

export interface SignedEvent extends AgentEvent {
  signature: string;
}

export const KAFKA_TOPICS: Record<string, string> = {
  research: 'agentco.research',
  product: 'agentco.product',
  engineering: 'agentco.engineering',
  sales: 'agentco.sales',
  cx: 'agentco.cx',
  finance: 'agentco.finance',
  people: 'agentco.people',
  legal: 'agentco.legal',
  override: 'agentco.override',
};

function topicForEventType(eventType: string): string {
  const domain = eventType.split('.')[0];
  return KAFKA_TOPICS[domain] ?? 'agentco.general';
}

function sign(event: AgentEvent): string {
  const payload = JSON.stringify(event);
  return crypto.createHmac('sha256', SIGNING_KEY).update(payload).digest('hex');
}

function verify(signed: SignedEvent): boolean {
  const { signature, ...event } = signed;
  const expected = sign(event as AgentEvent);
  return crypto.timingSafeEqual(Buffer.from(signature, 'hex'), Buffer.from(expected, 'hex'));
}

export class EventBusService {
  async publish(event: AgentEvent): Promise<void> {
    this.validateEnvelope(event);
    const signed: SignedEvent = { ...event, signature: sign(event) };
    const topic = topicForEventType(event.event_type);

    // In production: await kafkaProducer.send({ topic, messages: [{ value: JSON.stringify(signed) }] })
    console.log(`[EVENT_BUS] ${event.producer_agent_id} → ${event.event_type} on ${topic}`);
  }

  async consume(topic: string, groupId: string, handler: (event: AgentEvent) => Promise<void>): Promise<void> {
    // In production: kafkaConsumer.subscribe({ topic }); kafkaConsumer.run({ eachMessage: ... })
  }

  validateEnvelope(event: AgentEvent): void {
    const required: (keyof AgentEvent)[] = [
      'event_id', 'event_type', 'producer_agent_id', 'timestamp',
      'confidence_score', 'payload', 'risk_level', 'requires_ack'
    ];
    for (const field of required) {
      if (event[field] === undefined || event[field] === null) {
        throw new Error(`Event envelope missing required field: ${field}`);
      }
    }
    if (event.confidence_score < 0 || event.confidence_score > 1) {
      throw new Error(`Event confidence_score out of range: ${event.confidence_score}`);
    }
  }

  verifySignature(signed: SignedEvent): boolean {
    return verify(signed);
  }
}

export const eventBus = new EventBusService();
