import { db } from '../db/client';
import { disconnectProducer } from '../db/kafka';

let producerDisconnected = false;
let dbClosed = false;

export interface ShutdownOptions {
  closeDb?: boolean;
}

export async function shutdownRuntimeResources(options: ShutdownOptions = {}): Promise<void> {
  if (!producerDisconnected) {
    producerDisconnected = true;
    await disconnectProducer();
  }

  if (options.closeDb && !dbClosed) {
    dbClosed = true;
    await db.end();
  }
}
