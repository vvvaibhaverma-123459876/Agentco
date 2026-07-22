/**
 * Decision-receipt pipeline (migration 146 + repo-review.service).
 *
 * The LLM is injected as a deterministic fake (no network, no budget); git,
 * the filesystem pipeline, hashing, signing, and Postgres are all real. The
 * fixture is the bundled checkout-pricing repo whose applyDiscount() is
 * missing the /100 — its tests fail before the patch and pass after, so the
 * receipt records a measured improvement, not a claimed one.
 */
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { RepoReviewService } from '../src/services/repo-review.service';
import { canonicalJson, sha256Hex, signReceipt, verifyReceipt } from '../src/services/receipt-signer';
import { LlmJsonRequest, LlmJsonResult } from '../src/services/llm-provider.service';

const FIXTURE = path.resolve(__dirname, '../../deploy/local/demo-fixture-repo');

const FIXED_PRICING = fs
  .readFileSync(path.join(FIXTURE, 'pricing.js'), 'utf8')
  .replace('return Math.round(price - price * percent);', 'return Math.round(price - (price * percent) / 100);');

function fakeLlm(request: LlmJsonRequest): Promise<LlmJsonResult> {
  const respond = (json: Record<string, unknown>): LlmJsonResult => ({
    json,
    usage: { promptTokens: 100, completionTokens: 50, totalTokens: 150 },
    model: request.operation === 'repo_review.independent_evaluation' ? 'fake-evaluator' : 'fake-proposer',
    attempts: 1,
  });
  switch (request.operation) {
    case 'repo_review.identify_problem':
      return Promise.resolve(respond({
        file: 'pricing.js',
        title: 'applyDiscount treats percent as a fraction multiplier',
        description: 'price - price * percent subtracts percent TIMES the price; a 20% discount on 1000 yields -19000.',
        evidence: 'return Math.round(price - price * percent);',
      }));
    case 'repo_review.propose_change':
      return Promise.resolve(respond({
        rationale: 'Divide by 100 so percent is interpreted as a percentage, per the documented 0..100 contract.',
        patched_file_content: FIXED_PRICING,
      }));
    case 'repo_review.independent_evaluation':
      return Promise.resolve(respond({
        verdict: 'approve',
        confidence: 0.95,
        reasoning: 'The diff addresses the documented contract and the fixture tests flip from failing to passing.',
      }));
    default:
      return Promise.reject(new Error(`unexpected llm operation: ${request.operation}`));
  }
}

async function waitForTerminal(service: RepoReviewService, runId: string): Promise<string> {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const run = await service.getRun(runId);
    if (run && (run.status === 'receipted' || run.status === 'failed')) return run.status;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error('run did not reach a terminal status in time');
}

describe('decision receipts (repo review pipeline)', () => {
  const service = new RepoReviewService(fakeLlm);

  beforeAll(async () => {
    process.env.RECEIPT_SIGNING_SEED = crypto.randomBytes(32).toString('hex');
    process.env.AGENTCO_REVIEW_ALLOW_LOCAL = '1';
    process.env.AGENTCO_REVIEW_RUN_TESTS = '1';
    for (const file of ['079_identity_authority.sql', '146_decision_receipts.sql']) {
      await migrationDb.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${file}`), 'utf8'));
    }
  });

  test('full pipeline: fixture bug -> patch -> tests flip to green -> approved, signed receipt', async () => {
    const run = await service.startRun({ repo_url: FIXTURE });
    expect(run.source_mode).toBe('local_copy');

    const status = await waitForTerminal(service, run.id);
    const finished = await service.getRun(run.id);
    expect(`${status}:${finished?.error ?? ''}`).toBe('receipted:');

    expect(finished!.problem!.file).toBe('pricing.js');
    const validation = finished!.validation as { tests_before?: { ok: boolean }; tests_after?: { ok: boolean }; diff: string; syntax_check: { ok: boolean } };
    expect(validation.tests_before?.ok).toBe(false); // the bug is real
    expect(validation.tests_after?.ok).toBe(true);   // the patch measurably fixes it
    expect(validation.syntax_check.ok).toBe(true);
    expect(validation.diff).toContain('/ 100');
    expect((finished!.evaluation as { verdict: string }).verdict).toBe('approve');

    const stored = await service.getReceipt(run.id);
    expect(stored).not.toBeNull();
    const { hashValid, signatureValid } = verifyReceipt(
      stored!.receipt, stored!.content_hash, stored!.signature, stored!.public_key_pem
    );
    expect(hashValid).toBe(true);
    expect(signatureValid).toBe(true);

    // The stage hash chain links problem -> proposal -> validation -> evaluation.
    const stages = (stored!.receipt as { stages: Array<Record<string, unknown>> }).stages;
    expect(stages.map(stage => stage.stage)).toEqual([
      'problem_identified', 'change_proposed', 'validation', 'independent_evaluation',
    ]);
    let prev: string | null = null;
    for (const stage of stages) {
      expect(stage.prev_sha256).toBe(prev);
      expect(stage.payload_sha256).toBe(sha256Hex(canonicalJson(stage.payload)));
      prev = stage.payload_sha256 as string;
    }
  }, 120_000);

  test('the system can say NO: a reject verdict still produces a signed receipt recording the rejection', async () => {
    const rejectingLlm = (request: LlmJsonRequest): Promise<LlmJsonResult> =>
      request.operation === 'repo_review.independent_evaluation'
        ? Promise.resolve({
            json: { verdict: 'reject', confidence: 0.9, reasoning: 'The diff does not address the stated defect.' },
            usage: { promptTokens: 100, completionTokens: 50, totalTokens: 150 },
            model: 'fake-evaluator',
            attempts: 1,
          })
        : fakeLlm(request);
    const rejectService = new RepoReviewService(rejectingLlm);

    const run = await rejectService.startRun({ repo_url: FIXTURE });
    const status = await waitForTerminal(rejectService, run.id);
    expect(status).toBe('receipted');

    const finished = await rejectService.getRun(run.id);
    expect((finished!.evaluation as { verdict: string }).verdict).toBe('reject');

    const stored = await rejectService.getReceipt(run.id);
    expect((stored!.receipt as { verdict: string }).verdict).toBe('reject');
    const { hashValid, signatureValid } = verifyReceipt(
      stored!.receipt, stored!.content_hash, stored!.signature, stored!.public_key_pem
    );
    expect(hashValid && signatureValid).toBe(true);
  }, 120_000);

  test('a model file reference with a ./ prefix resolves to the real file', async () => {
    const prefixLlm = (request: LlmJsonRequest): Promise<LlmJsonResult> =>
      request.operation === 'repo_review.identify_problem'
        ? Promise.resolve({
            json: {
              file: './pricing.js',
              title: 'discount math',
              description: 'wrong',
              evidence: 'return Math.round(price - price * percent);',
            },
            usage: { promptTokens: 100, completionTokens: 50, totalTokens: 150 },
            model: 'fake-proposer',
            attempts: 1,
          })
        : fakeLlm(request);
    const run = await new RepoReviewService(prefixLlm).startRun({ repo_url: FIXTURE });
    const svc = new RepoReviewService(prefixLlm);
    const status = await waitForTerminal(svc, run.id);
    expect(status).toBe('receipted');
    expect((await svc.getRun(run.id))!.problem!.file).toBe('pricing.js');
  }, 120_000);

  test('a tampered receipt fails verification', () => {
    const receipt = { version: 'agentco-receipt-v1', verdict: 'approve' };
    const signed = signReceipt(receipt);
    const tampered = { ...receipt, verdict: 'reject' };
    const result = verifyReceipt(tampered, signed.contentHash, signed.signature, signed.publicKeyPem);
    expect(result.hashValid).toBe(false);
  });

  test('a forged signature fails verification even with a correct hash', () => {
    const receipt = { version: 'agentco-receipt-v1', verdict: 'approve' };
    const signed = signReceipt(receipt);
    const forged = Buffer.from(signed.signature, 'base64');
    forged[0] = forged[0] ^ 0xff;
    const result = verifyReceipt(receipt, signed.contentHash, forged.toString('base64'), signed.publicKeyPem);
    expect(result.hashValid).toBe(true);
    expect(result.signatureValid).toBe(false);
  });

  test('receipts are immutable at the database layer', async () => {
    const inserted = await db.query<{ run_id: string }>(
      `SELECT run_id FROM decision_receipts LIMIT 1`
    );
    expect(inserted.rowCount).toBe(1);
    await expect(
      db.query(`UPDATE decision_receipts SET content_hash='tampered' WHERE run_id=$1`, [inserted.rows[0].run_id])
    ).rejects.toThrow(/DECISION RECEIPT GUARD/);
    await expect(
      db.query(`DELETE FROM decision_receipts WHERE run_id=$1`, [inserted.rows[0].run_id])
    ).rejects.toThrow(/DECISION RECEIPT GUARD/);
  });

  test('remote URLs outside github.com are rejected', async () => {
    await expect(service.startRun({ repo_url: 'https://evil.example.com/x/y' })).rejects.toThrow(/github\.com|AGENTCO_REVIEW_ALLOW_LOCAL/);
  });

  test('local paths are rejected when AGENTCO_REVIEW_ALLOW_LOCAL is off', async () => {
    const prior = process.env.AGENTCO_REVIEW_ALLOW_LOCAL;
    delete process.env.AGENTCO_REVIEW_ALLOW_LOCAL;
    try {
      await expect(service.startRun({ repo_url: FIXTURE })).rejects.toThrow(/AGENTCO_REVIEW_ALLOW_LOCAL/);
    } finally {
      process.env.AGENTCO_REVIEW_ALLOW_LOCAL = prior;
    }
  });
});
