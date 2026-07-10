import type { Config } from 'jest';

const config: Config = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  testMatch: ['**/*.test.ts'],
  setupFiles: ['<rootDir>/tests/setup-env.ts'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup-after-env.ts'],
  transform: {
    '^.+\\.ts$': ['ts-jest', { tsconfig: { rootDir: '.' } }],
  },
  testTimeout: 30000,
};

export default config;
