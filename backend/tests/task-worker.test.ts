import { runSubprocess } from '../src/workers/task-worker';

describe('supervised task worker subprocess execution', () => {
  test('parses successful JSON output', async () => {
    const result = await runSubprocess(
      process.execPath,
      ['-e', 'console.log(JSON.stringify({status:"done", task_id:"t1"}))'],
      2000,
      4096,
      'corr-success',
    );

    expect(result.ok).toBe(true);
    expect(result.parsed).toEqual({ status: 'done', task_id: 't1' });
    expect(result.correlationId).toBe('corr-success');
  });

  test('classifies malformed JSON output', async () => {
    const result = await runSubprocess(
      process.execPath,
      ['-e', 'console.log("not-json")'],
      2000,
      4096,
      'corr-malformed',
    );

    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/malformed executor JSON output/);
  });

  test('classifies failed subprocess exit', async () => {
    const result = await runSubprocess(
      process.execPath,
      ['-e', 'console.error("boom"); process.exit(7)'],
      2000,
      4096,
      'corr-failed',
    );

    expect(result.ok).toBe(false);
    expect(result.exitCode).toBe(7);
    expect(result.stderr).toContain('boom');
  });

  test('terminates subprocess on timeout', async () => {
    const result = await runSubprocess(
      process.execPath,
      ['-e', 'setTimeout(() => console.log("{}"), 5000)'],
      100,
      4096,
      'corr-timeout',
    );

    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/timed out/);
  });
});
