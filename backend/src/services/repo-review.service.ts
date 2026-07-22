/**
 * Decision-receipt repository review pipeline.
 *
 * Flow: acquire repo -> identify one concrete problem -> propose a change ->
 * validate it mechanically -> INDEPENDENT evaluation by a second model with a
 * skeptical-reviewer prompt -> issue an Ed25519-signed, hash-chained decision
 * receipt that a third party can verify from the receipt row alone.
 *
 * Trust boundaries, stated plainly:
 *  - Remote sources are restricted to https://github.com/<owner>/<repo>,
 *    shallow-cloned with no submodules, and size-capped. Repository files are
 *    READ and syntax-checked but never executed: running an untrusted repo's
 *    test suite is arbitrary code execution and is out of scope here.
 *  - `local_copy` mode (plain directory copy, for the bundled demo fixture and
 *    jest) is enabled only when AGENTCO_REVIEW_ALLOW_LOCAL=1. Only in that
 *    trusted mode, and only when AGENTCO_REVIEW_RUN_TESTS=1, is the fixture's
 *    `npm test` executed (before AND after the patch, so the receipt shows a
 *    measured improvement rather than a claimed one).
 *  - Both LLM calls go through llmProviderService (budget-enforced in
 *    production); the receipt records each stage's model and token usage.
 */
import { execFile } from 'child_process';
import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { promisify } from 'util';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { llmProvider, LlmJsonRequest, LlmJsonResult } from './llm-provider.service';
import { canonicalJson, sha256Hex, signReceipt } from './receipt-signer';

const execFileAsync = promisify(execFile);

const GITHUB_URL_PATTERN = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+?(\.git)?$/;
const MAX_REPO_KB = 200 * 1024;
const MAX_ANALYSIS_FILES = 12;
const MAX_ANALYSIS_BYTES = 24 * 1024;
const MAX_TARGET_FILE_BYTES = 32 * 1024;
const SOURCE_EXTENSIONS = new Set(['.js', '.mjs', '.cjs', '.ts', '.py', '.json']);

export interface StartReviewInput {
  repo_url: string;
  requested_by_actor_id?: string;
}

export interface ReviewRun {
  id: string;
  repo_url: string;
  source_mode: 'git_clone' | 'local_copy';
  repo_head_sha: string | null;
  status: string;
  problem: Record<string, unknown> | null;
  proposal: Record<string, unknown> | null;
  validation: Record<string, unknown> | null;
  evaluation: Record<string, unknown> | null;
  error: string | null;
  requested_by_actor_id: string | null;
  created_at: string;
}

type LlmCaller = (request: LlmJsonRequest) => Promise<LlmJsonResult>;

function proposerModel(): string | undefined {
  return process.env.LLM_MODEL_FRONTIER || process.env.LLM_MODEL_DEFAULT || undefined;
}

function evaluatorModel(): string | undefined {
  return process.env.LLM_MODEL_MONITOR || process.env.LLM_MODEL_DEFAULT || undefined;
}

async function run(cmd: string, args: string[], cwd?: string, timeoutMs = 60_000): Promise<{ stdout: string; stderr: string }> {
  return execFileAsync(cmd, args, { cwd, timeout: timeoutMs, maxBuffer: 4 * 1024 * 1024 });
}

/** Resolve a model-supplied file reference to an actual path in the repo. */
function resolveFileRef(ref: unknown, files: string[]): string | null {
  if (typeof ref !== 'string') return null;
  const normalized = ref.replace(/^\.\//, '').trim();
  if (files.includes(normalized)) return normalized;
  const byBasename = files.filter(file => path.basename(file) === path.basename(normalized));
  return byBasename.length === 1 ? byBasename[0] : null;
}

/** Models often wrap file bodies in ```lang fences despite json_object mode; strip them. */
function stripCodeFence(content: string): string {
  const fence = content.match(/^\s*```[a-zA-Z0-9]*\n([\s\S]*?)\n```\s*$/);
  return fence ? fence[1] : content;
}

function listSourceFiles(root: string): string[] {
  const out: string[] = [];
  const walk = (dir: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.name === 'node_modules' || entry.name === '.git' || entry.name.startsWith('.')) continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (SOURCE_EXTENSIONS.has(path.extname(entry.name))) out.push(path.relative(root, full));
    }
  };
  walk(root);
  return out.sort();
}

async function syntaxCheck(root: string, relFile: string): Promise<{ tool: string; ok: boolean; detail: string }> {
  const full = path.join(root, relFile);
  const ext = path.extname(relFile);
  try {
    if (ext === '.js' || ext === '.mjs' || ext === '.cjs') {
      await run(process.execPath, ['--check', full]);
      return { tool: 'node --check', ok: true, detail: 'syntax ok' };
    }
    if (ext === '.py') {
      await run(process.env.AGENTCO_PYTHON || 'python3', ['-m', 'py_compile', full]);
      return { tool: 'py_compile', ok: true, detail: 'syntax ok' };
    }
    if (ext === '.json') {
      JSON.parse(fs.readFileSync(full, 'utf8'));
      return { tool: 'JSON.parse', ok: true, detail: 'syntax ok' };
    }
    return { tool: 'none', ok: true, detail: `no syntax checker for ${ext}; skipped` };
  } catch (error) {
    return { tool: ext === '.py' ? 'py_compile' : 'node --check', ok: false, detail: (error as Error).message.slice(0, 500) };
  }
}

export class RepoReviewService {
  constructor(private readonly llm: LlmCaller = request => llmProvider.callJson(request)) {}

  async startRun(input: StartReviewInput): Promise<ReviewRun> {
    const allowLocal = process.env.AGENTCO_REVIEW_ALLOW_LOCAL === '1';
    const looksRemote = /^[a-z][a-z0-9+.-]*:\/\//i.test(input.repo_url);
    const isGithub = GITHUB_URL_PATTERN.test(input.repo_url);
    // A remote URL must be github.com — never fall back to local-path handling
    // for an off-allowlist URL, or an https URL could be probed as a filesystem path.
    if (looksRemote && !isGithub) {
      throw new Error('repo_url must be https://github.com/<owner>/<repo>');
    }
    const isLocal = !isGithub;
    if (isLocal) {
      if (!allowLocal) {
        throw new Error('repo_url must be https://github.com/<owner>/<repo> (local paths require AGENTCO_REVIEW_ALLOW_LOCAL=1)');
      }
      if (!fs.existsSync(input.repo_url) || !fs.statSync(input.repo_url).isDirectory()) {
        throw new Error(`local repo path does not exist: ${input.repo_url}`);
      }
    }
    const inserted = await db.query<ReviewRun>(
      `INSERT INTO repo_review_runs (repo_url, source_mode, requested_by_actor_id)
       VALUES ($1, $2, $3) RETURNING *`,
      [input.repo_url, isLocal ? 'local_copy' : 'git_clone', input.requested_by_actor_id ?? null]
    );
    const runRow = inserted.rows[0];
    void this.process(runRow.id).catch(() => undefined);
    return runRow;
  }

  async getRun(id: string): Promise<ReviewRun | null> {
    const result = await db.query<ReviewRun>(`SELECT * FROM repo_review_runs WHERE id = $1`, [id]);
    return result.rows[0] ?? null;
  }

  async getReceipt(runId: string): Promise<{
    receipt: Record<string, unknown>;
    content_hash: string;
    signature: string;
    public_key_pem: string;
  } | null> {
    const result = await db.query(
      `SELECT receipt, content_hash, signature, public_key_pem FROM decision_receipts WHERE run_id = $1`,
      [runId]
    );
    return (result.rows[0] as never) ?? null;
  }

  /** Runs the whole pipeline; every stage transition is persisted before the next begins. */
  async process(runId: string): Promise<void> {
    let workdir: string | null = null;
    try {
      const runRow = await this.getRun(runId);
      if (!runRow) throw new Error('run not found');

      workdir = fs.mkdtempSync(path.join(os.tmpdir(), 'agentco-review-'));
      const repoDir = path.join(workdir, 'repo');
      const headSha = await this.acquireSource(runRow, repoDir);
      await this.transition(runId, 'analyzing', { repo_head_sha: headSha });

      const problem = await this.identifyProblem(repoDir);
      await this.transition(runId, 'proposing', { problem });

      const proposal = await this.proposeChange(repoDir, problem);
      await this.transition(runId, 'validating', { proposal });

      const validation = await this.validate(runRow, repoDir, problem, proposal);
      await this.transition(runId, 'evaluating', { validation });

      const evaluation = await this.evaluate(problem, proposal, validation);
      await this.transition(runId, 'evaluating', { evaluation });

      await this.issueReceipt(runId);
    } catch (error) {
      await db.query(
        `UPDATE repo_review_runs SET status='failed', error=$2, updated_at=now() WHERE id=$1`,
        [runId, (error as Error).message.slice(0, 2000)]
      );
    } finally {
      if (workdir) fs.rmSync(workdir, { recursive: true, force: true });
    }
  }

  private async acquireSource(runRow: ReviewRun, repoDir: string): Promise<string> {
    if (runRow.source_mode === 'git_clone') {
      await run('git', ['clone', '--depth', '1', '--no-tags', '--single-branch', runRow.repo_url, repoDir], undefined, 120_000);
      const size = await run('du', ['-sk', repoDir]);
      if (Number(size.stdout.split('\t')[0]) > MAX_REPO_KB) throw new Error('repository exceeds size cap');
      const head = await run('git', ['rev-parse', 'HEAD'], repoDir);
      return head.stdout.trim();
    }
    fs.cpSync(runRow.repo_url, repoDir, {
      recursive: true,
      filter: source => !source.includes('node_modules') && !source.includes('/.git'),
    });
    // No git history in local_copy mode; identify the tree by content hash instead.
    const files = listSourceFiles(repoDir);
    const digest = crypto.createHash('sha256');
    for (const file of files) digest.update(file).update('\0').update(fs.readFileSync(path.join(repoDir, file)));
    return `local:${digest.digest('hex')}`;
  }

  private async identifyProblem(repoDir: string): Promise<Record<string, unknown>> {
    const files = listSourceFiles(repoDir);
    if (files.length === 0) throw new Error('no reviewable source files found');

    const precheck: Array<Record<string, unknown>> = [];
    for (const file of files.slice(0, 50)) {
      const check = await syntaxCheck(repoDir, file);
      if (!check.ok) precheck.push({ file, ...check });
    }

    let budget = MAX_ANALYSIS_BYTES;
    const excerpts: Array<{ file: string; content: string }> = [];
    for (const file of files.slice(0, MAX_ANALYSIS_FILES)) {
      const content = fs.readFileSync(path.join(repoDir, file), 'utf8');
      const slice = content.slice(0, Math.min(content.length, budget));
      if (slice.length === 0) break;
      excerpts.push({ file, content: slice });
      budget -= slice.length;
      if (budget <= 0) break;
    }

    const result = await this.llm({
      operation: 'repo_review.identify_problem',
      model: proposerModel(),
      responseFormat: 'json_object',
      system:
        'You are a senior engineer reviewing a repository. Identify exactly ONE concrete, small, fixable defect ' +
        'in the provided files (a real bug, not a style preference). Respond as JSON: ' +
        '{"file": "<relative path from the provided list>", "title": "<one line>", ' +
        '"description": "<what is wrong and why it matters>", "evidence": "<the specific code that is wrong>"}',
      user: canonicalJson({ files, syntax_failures: precheck, excerpts }),
      maxTokens: 700,
    });

    const problem = result.json as Record<string, unknown>;
    const resolvedFile = resolveFileRef(problem.file, files);
    if (!resolvedFile) {
      throw new Error(`problem identification returned an unknown file: ${String(problem.file)}`);
    }
    return { ...problem, file: resolvedFile, syntax_failures: precheck, model: result.model, usage: result.usage };
  }

  private async proposeChange(repoDir: string, problem: Record<string, unknown>): Promise<Record<string, unknown>> {
    const relFile = problem.file as string;
    const original = fs.readFileSync(path.join(repoDir, relFile), 'utf8');
    if (Buffer.byteLength(original) > MAX_TARGET_FILE_BYTES) {
      throw new Error(`target file too large for full-file proposal: ${relFile}`);
    }

    const result = await this.llm({
      operation: 'repo_review.propose_change',
      model: proposerModel(),
      responseFormat: 'json_object',
      system:
        'You are fixing exactly one identified defect. Return the COMPLETE corrected file content, changing as ' +
        'little as possible. Respond as JSON: {"rationale": "<why this fix is correct>", ' +
        '"patched_file_content": "<entire file, corrected>"}',
      user: canonicalJson({ problem: { file: relFile, title: problem.title, description: problem.description, evidence: problem.evidence }, file_content: original }),
      maxTokens: 2000,
    });

    const rawPatched = result.json.patched_file_content;
    if (typeof rawPatched !== 'string' || rawPatched.trim().length === 0) {
      throw new Error('proposal did not include patched_file_content');
    }
    const patched = stripCodeFence(rawPatched);
    if (patched === original) throw new Error('proposal is identical to the original file');
    return {
      file: relFile,
      rationale: result.json.rationale ?? null,
      patched_file_content: patched,
      original_sha256: sha256Hex(original),
      patched_sha256: sha256Hex(patched),
      model: result.model,
      usage: result.usage,
    };
  }

  private async validate(
    runRow: ReviewRun,
    repoDir: string,
    problem: Record<string, unknown>,
    proposal: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const relFile = proposal.file as string;
    const trustedFixture = runRow.source_mode === 'local_copy' && process.env.AGENTCO_REVIEW_RUN_TESTS === '1';

    const runFixtureTests = async (): Promise<Record<string, unknown> | null> => {
      if (!trustedFixture || !fs.existsSync(path.join(repoDir, 'package.json'))) return null;
      try {
        const result = await run('npm', ['test', '--silent'], repoDir, 60_000);
        return { ok: true, output: (result.stdout + result.stderr).slice(-1500) };
      } catch (error) {
        const failed = error as { stdout?: string; stderr?: string; message: string };
        return { ok: false, output: ((failed.stdout ?? '') + (failed.stderr ?? '') || failed.message).slice(-1500) };
      }
    };

    const testsBefore = await runFixtureTests();

    const originalPath = path.join(repoDir, relFile);
    const patchedPath = path.join(repoDir, `${relFile}.agentco-patched`);
    fs.writeFileSync(patchedPath, proposal.patched_file_content as string);
    let diff = '';
    try {
      await run('git', ['diff', '--no-index', '--', originalPath, patchedPath], undefined, 30_000);
    } catch (error) {
      // git diff --no-index exits 1 when files differ; the diff is on stdout.
      diff = (error as { stdout?: string }).stdout ?? '';
    }
    fs.rmSync(patchedPath);

    fs.writeFileSync(originalPath, proposal.patched_file_content as string);
    const syntax = await syntaxCheck(repoDir, relFile);
    const testsAfter = await runFixtureTests();

    return {
      diff: diff.slice(0, 20_000),
      diff_sha256: sha256Hex(diff),
      syntax_check: syntax,
      tests_before: testsBefore,
      tests_after: testsAfter,
      tests_executed: trustedFixture,
      problem_file_matches: relFile === problem.file,
    };
  }

  private async evaluate(
    problem: Record<string, unknown>,
    proposal: Record<string, unknown>,
    validation: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const result = await this.llm({
      operation: 'repo_review.independent_evaluation',
      model: evaluatorModel(),
      responseFormat: 'json_object',
      system:
        'You are an INDEPENDENT, skeptical reviewer. You did not write this change. Judge only from the evidence: ' +
        'does the diff actually fix the stated problem without breaking anything visible? Reject changes that are ' +
        'cosmetic, off-target, or unsupported by the validation evidence. Respond as JSON: ' +
        '{"verdict": "approve" | "reject" | "uncertain", "confidence": <0..1>, "reasoning": "<grounds>"}',
      user: canonicalJson({
        problem: { file: problem.file, title: problem.title, description: problem.description, evidence: problem.evidence },
        rationale: proposal.rationale,
        diff: validation.diff,
        syntax_check: validation.syntax_check,
        tests_before: validation.tests_before,
        tests_after: validation.tests_after,
      }),
      maxTokens: 600,
    });

    const verdict = String(result.json.verdict ?? '');
    if (!['approve', 'reject', 'uncertain'].includes(verdict)) {
      throw new Error(`evaluator returned invalid verdict: ${verdict}`);
    }
    return {
      verdict,
      confidence: typeof result.json.confidence === 'number' ? result.json.confidence : null,
      reasoning: result.json.reasoning ?? null,
      model: result.model,
      usage: result.usage,
      independent_of_proposer: result.model !== (proposal as { model?: string }).model || evaluatorModel() !== proposerModel(),
    };
  }

  private async issueReceipt(runId: string): Promise<void> {
    const runRow = await this.getRun(runId);
    if (!runRow?.problem || !runRow.proposal || !runRow.validation || !runRow.evaluation) {
      throw new Error('cannot issue receipt: pipeline stages incomplete');
    }

    const stages: Array<Record<string, unknown>> = [];
    let prev: string | null = null;
    for (const [stage, payload] of [
      ['problem_identified', runRow.problem],
      ['change_proposed', runRow.proposal],
      ['validation', runRow.validation],
      ['independent_evaluation', runRow.evaluation],
    ] as Array<[string, Record<string, unknown>]>) {
      const payloadSha = sha256Hex(canonicalJson(payload));
      stages.push({ stage, payload, payload_sha256: payloadSha, prev_sha256: prev });
      prev = payloadSha;
    }

    const receipt: Record<string, unknown> = {
      version: 'agentco-receipt-v1',
      run_id: runId,
      repository: { url: runRow.repo_url, source_mode: runRow.source_mode, head: runRow.repo_head_sha },
      stages,
      verdict: (runRow.evaluation as { verdict?: string }).verdict ?? null,
      models: {
        proposer: (runRow.proposal as { model?: string }).model ?? null,
        evaluator: (runRow.evaluation as { model?: string }).model ?? null,
      },
      issued_at: new Date().toISOString(),
    };

    const signed = signReceipt(receipt);
    await db.query(
      `INSERT INTO decision_receipts (run_id, receipt, content_hash, signature, public_key_pem)
       VALUES ($1, $2::jsonb, $3, $4, $5)`,
      [runId, JSON.stringify(receipt), signed.contentHash, signed.signature, signed.publicKeyPem]
    );
    await db.query(`UPDATE repo_review_runs SET status='receipted', updated_at=now() WHERE id=$1`, [runId]);

    const actorId = runRow.requested_by_actor_id ?? process.env.LLM_RESOURCE_ACTOR_ID;
    if (actorId) {
      await eventLog
        .append({
          event_type: 'decision_receipt.issued',
          actor_id: actorId as string,
          object_type: 'decision_receipt',
          object_id: runId,
          payload: { run_id: runId, content_hash: signed.contentHash, verdict: receipt.verdict },
        })
        .catch(() => undefined);
    }
  }

  private async transition(runId: string, status: string, fields: Partial<Record<'repo_head_sha', string> & Record<'problem' | 'proposal' | 'validation' | 'evaluation', Record<string, unknown>>>): Promise<void> {
    const sets: string[] = [`status=$2`, `updated_at=now()`];
    const params: unknown[] = [runId, status];
    for (const [key, value] of Object.entries(fields)) {
      params.push(key === 'repo_head_sha' ? value : JSON.stringify(value));
      sets.push(`${key}=$${params.length}${key === 'repo_head_sha' ? '' : '::jsonb'}`);
    }
    await db.query(`UPDATE repo_review_runs SET ${sets.join(', ')} WHERE id=$1`, params);
  }
}

export const repoReviewService = new RepoReviewService();
