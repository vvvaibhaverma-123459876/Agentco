import { main, parseArgs } from '../src/cli/run-bounded-learning';

describe('bounded learning CLI guard', () => {
  const originalEnv = process.env.AGENTCO_ENV;
  let exitSpy: jest.SpyInstance;
  let errorSpy: jest.SpyInstance;
  let logSpy: jest.SpyInstance;

  beforeEach(() => {
    exitSpy = jest.spyOn(process, 'exit').mockImplementation(((code?: string | number | null) => {
      throw new Error(`process.exit:${code}`);
    }) as never);
    errorSpy = jest.spyOn(console, 'error').mockImplementation(() => undefined);
    logSpy = jest.spyOn(console, 'log').mockImplementation(() => undefined);
  });

  afterEach(() => {
    if (originalEnv === undefined) {
      delete process.env.AGENTCO_ENV;
    } else {
      process.env.AGENTCO_ENV = originalEnv;
    }
    exitSpy.mockRestore();
    errorSpy.mockRestore();
    logSpy.mockRestore();
  });

  test('parses deterministic provider explicitly', () => {
    const args = parseArgs([
      '--goal',
      'test deterministic guard',
      '--source-pack',
      'ai_tech',
      '--provider',
      'deterministic_test_only',
    ]);

    expect(args.provider).toBe('deterministic_test_only');
  });

  test('production rejects deterministic provider before executing a run', async () => {
    process.env.AGENTCO_ENV = 'production';

    await expect(main([
      '--goal',
      'test deterministic guard',
      '--source-pack',
      'ai_tech',
      '--provider',
      'deterministic_test_only',
    ])).rejects.toThrow(/process.exit:1/);

    expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining('deterministic_test_only'));
  });
});
