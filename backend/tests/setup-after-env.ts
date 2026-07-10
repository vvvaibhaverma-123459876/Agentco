import { afterAll } from '@jest/globals';
import { disconnectProducer } from '../src/db/kafka';

afterAll(async () => {
  await disconnectProducer();
});
