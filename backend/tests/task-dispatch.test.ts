jest.mock('../src/db/client', () => ({
  query: jest.fn(),
}));

import fs from 'fs';
import path from 'path';
import { query } from '../src/db/client';
import { cancelTask, createTask, getTask, leaseOneTask } from '../src/services/task-dispatch.service';

const mockedQuery = query as jest.MockedFunction<typeof query>;

const row = {
  task_id: 'task-1',
  agent_id: 'agent-1',
  task_type: 'test',
  payload: { x: 1 },
  status: 'queued',
  queued_at: '2026-06-21T00:00:00.000Z',
  retry_count: 0,
  max_retries: 3,
  correlation_id: 'task-1',
};

describe('durable task dispatch service', () => {
  beforeEach(() => mockedQuery.mockReset());

  test('createTask inserts durable queued task and appends event', async () => {
    mockedQuery.mockResolvedValueOnce([row]).mockResolvedValueOnce([{ id: 'event-1' }]);

    const task = await createTask('agent-1', 'test', { x: 1 });

    expect(task.task_id).toBe('task-1');
    expect(task.status).toBe('queued');
    expect(mockedQuery.mock.calls[0][0]).toContain('INSERT INTO agent_tasks');
    expect(mockedQuery.mock.calls[1][0]).toContain('INSERT INTO agent_task_events');
  });

  test('getTask reads from database', async () => {
    mockedQuery.mockResolvedValueOnce([row]);

    const task = await getTask('task-1');

    expect(task!.task_id).toBe('task-1');
    expect(mockedQuery.mock.calls[0][0]).toContain('FROM agent_tasks');
  });

  test('cancelTask updates durable status and appends event', async () => {
    mockedQuery.mockResolvedValueOnce([{ ...row, status: 'cancelled' }]).mockResolvedValueOnce([{ id: 'event-1' }]);

    const task = await cancelTask('task-1');

    expect(task!.status).toBe('cancelled');
    expect(mockedQuery.mock.calls[0][0]).toContain("status = 'cancelled'");
  });

  test('leaseOneTask uses skip locked lease query', async () => {
    mockedQuery.mockResolvedValueOnce([{ ...row, status: 'leased', lease_owner: 'worker-1' }]).mockResolvedValueOnce([{ id: 'event-1' }]);

    const task = await leaseOneTask('worker-1');

    expect(task!.status).toBe('leased');
    expect(mockedQuery.mock.calls[0][0]).toContain('FOR UPDATE SKIP LOCKED');
  });

  test('agents route no longer declares in-memory taskQueue', () => {
    const source = fs.readFileSync(path.resolve(__dirname, '../src/routes/agents.routes.ts'), 'utf8');
    expect(source).not.toContain('taskQueue');
  });
});
