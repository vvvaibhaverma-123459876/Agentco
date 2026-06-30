import { db } from '../db/client';
import { disconnectProducer } from '../db/kafka';

let shutdownStarted = false;

export interface ShutdownOptions {
  closeDb?: boolean;
}

export async function shutdownRuntimeResources(options: ShutdownOptions = {}): Promise<void> {
  if (shutdownStarted) return;
  shutdownStarted = true;

  await disconnectProducer();

  if (options.closeDb) {
    await db.end();
  }
}
