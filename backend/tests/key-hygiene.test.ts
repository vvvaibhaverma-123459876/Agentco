/**
 * Key Hygiene Guard (B5 / GA5)
 * ============================
 * Fails if any git-tracked file contains an OpenAI-style API key (or key
 * prefix). The pattern targets `sk-...`/`sk-proj-...` followed by a long
 * alphanumeric run — it does NOT match ordinary words like "risk-adjusted"
 * or "risk-tier" (no word boundary before `sk`, and the alnum run is short).
 *
 * If this test fails, a secret (or secret prefix) has been committed: scrub
 * it, and rotate the key.
 */

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { describe, expect, test } from '@jest/globals';

const repoRoot = path.resolve(__dirname, '..', '..');

// Real OpenAI keys: sk-<20+ alnum> or sk-proj-<20+ alnum>. Word boundary
// before `sk` so "risk-" (no boundary between i and s) never matches.
const KEY_PATTERN = /\bsk-(proj-)?[A-Za-z0-9]{20,}/;

describe('key hygiene (B5)', () => {
  test('no tracked file contains an OpenAI-style key or key prefix', () => {
    const files = execSync('git ls-files', { cwd: repoRoot, encoding: 'utf8' })
      .split('\n')
      .map(f => f.trim())
      .filter(Boolean)
      // Skip this guard file itself and binary/lock files.
      .filter(f => !f.endsWith('key-hygiene.test.ts'))
      .filter(f => !/\.(png|jpg|jpeg|gif|ico|pdf|zip|lock|pem)$/i.test(f));

    const offenders: string[] = [];
    for (const file of files) {
      const abs = path.join(repoRoot, file);
      let content: string;
      try {
        content = fs.readFileSync(abs, 'utf8');
      } catch {
        continue; // deleted/unreadable
      }
      if (KEY_PATTERN.test(content)) offenders.push(file);
    }
    expect(offenders).toEqual([]);
  });

  test('the guard pattern matches real keys but not "risk-" words (self-test)', () => {
    expect(KEY_PATTERN.test('sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')).toBe(true);
    expect(KEY_PATTERN.test('sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345')).toBe(true);
    expect(KEY_PATTERN.test('risk-adjusted return and risk-tier classifier')).toBe(false);
    expect(KEY_PATTERN.test('[REDACTED-KEY-PREFIX]')).toBe(false);
  });
});
