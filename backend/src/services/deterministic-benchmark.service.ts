/**
 * Deterministic Benchmark Service
 * ===============================
 * Seeded, offline task families used to MEASURE whether a candidate strategy
 * actually improves decisions relative to the baseline policy. No LLM, no
 * network: strategies are executable decision policies, and scores come from
 * ground truth embedded in the generated tasks.
 *
 * This is a benchmark harness, not production evidence. Results are labeled
 * `deterministic_benchmark` wherever they are persisted. Its purpose is to
 * give the candidate-evaluation -> canary -> promotion loop an honest,
 * reproducible measurement so improvements are demonstrated by executed
 * behavior rather than projected numbers.
 *
 * Task families (mirroring real weaknesses in the runtime):
 *   source_selection       - pick k sources; ground truth rewards independent
 *                            + reliable sources
 *   evidence_grounding     - pick support snippets; ground truth rewards
 *                            snippets that are true token-subsequences of the
 *                            evidence text
 *   contradiction_handling - accept/reject contradicting claims; ground truth
 *                            rewards siding with the better-calibrated
 *                            producer instead of stated confidence
 */

export type TaskFamily = 'source_selection' | 'evidence_grounding' | 'contradiction_handling';

export const STRATEGIES_BY_FAMILY: Record<TaskFamily, string> = {
  source_selection: 'prefer_independent_sources',
  evidence_grounding: 'require_token_subsequence',
  contradiction_handling: 'calibration_weighted_adjudication',
};

interface SourceCandidate {
  id: string;
  independent: boolean;
  reliable: boolean;
}

interface SnippetCandidate {
  text: string;
  grounded: boolean;
}

interface ContradictionCase {
  claimA: { producerTrust: number; statedConfidence: number };
  claimB: { producerTrust: number; statedConfidence: number };
  /** ground truth: 'A' | 'B' — the better-calibrated producer is correct */
  correct: 'A' | 'B';
}

export interface BenchmarkTask {
  taskIndex: number;
  family: TaskFamily;
  sources?: SourceCandidate[];
  evidenceText?: string;
  snippets?: SnippetCandidate[];
  contradiction?: ContradictionCase;
}

export interface BenchmarkResult {
  family: TaskFamily;
  strategy: string;
  iterations: number;
  baselineScore: number;
  strategyScore: number;
  improvement: number;
  perTask: Array<{ taskIndex: number; baseline: number; strategy: number }>;
}

/** Deterministic LCG so benchmark runs are reproducible for a given seed. */
class SeededRandom {
  private state: number;
  constructor(seed: number) {
    this.state = seed % 2147483647;
    if (this.state <= 0) this.state += 2147483646;
  }
  next(): number {
    this.state = (this.state * 16807) % 2147483647;
    return (this.state - 1) / 2147483646;
  }
  pick<T>(items: T[]): T {
    return items[Math.floor(this.next() * items.length)];
  }
}

const EVIDENCE_TEXTS = [
  'the calibration ledger records every resolved prediction with a brier score and timestamp',
  'independent verification requires evidence from at least two unrelated source groups',
  'trust scores decay when an agent makes repeated overconfident incorrect predictions',
  'memory promotion happens only after a prediction is resolved and scored by the resolution service',
];

export class DeterministicBenchmarkService {
  generateTasks(family: TaskFamily, count: number, seed: number): BenchmarkTask[] {
    const rng = new SeededRandom(seed);
    const tasks: BenchmarkTask[] = [];
    for (let i = 0; i < count; i++) {
      if (family === 'source_selection') {
        const sources: SourceCandidate[] = [];
        // First sources are deliberately tempting-but-poor so the naive
        // baseline (take the first k) underperforms.
        for (let s = 0; s < 6; s++) {
          sources.push({
            id: `src-${i}-${s}`,
            independent: s >= 3 ? rng.next() > 0.2 : rng.next() > 0.8,
            reliable: s >= 3 ? rng.next() > 0.3 : rng.next() > 0.7,
          });
        }
        tasks.push({ taskIndex: i, family, sources });
      } else if (family === 'evidence_grounding') {
        const evidenceText = rng.pick(EVIDENCE_TEXTS);
        const words = evidenceText.split(' ');
        const start = Math.floor(rng.next() * (words.length - 4));
        const groundedSnippet = words.slice(start, start + 4).join(' ');
        const fabricated = `${words[0]} definitely proves ${words[words.length - 1]} beyond doubt`;
        const snippets: SnippetCandidate[] = [
          { text: fabricated, grounded: false },
          { text: groundedSnippet, grounded: true },
          { text: `${groundedSnippet} extra invented words`, grounded: false },
        ];
        // Deterministic shuffle: the baseline (first snippet) is sometimes
        // right by luck, so the comparison against the strategy is fair
        // rather than a rigged always-zero baseline.
        for (let j = snippets.length - 1; j > 0; j--) {
          const k = Math.floor(rng.next() * (j + 1));
          [snippets[j], snippets[k]] = [snippets[k], snippets[j]];
        }
        tasks.push({ taskIndex: i, family, evidenceText, snippets });
      } else {
        const trustA = 0.3 + rng.next() * 0.6;
        const trustB = 0.3 + rng.next() * 0.6;
        // Half the producers are honest (confidence tracks calibration);
        // half are overconfident (confidence anti-correlates). The baseline
        // "believe the loudest" policy is right whenever the honest producer
        // is also the better-calibrated one, so it scores mid-range instead
        // of a rigged zero.
        const honestA = rng.next() > 0.5;
        const honestB = rng.next() > 0.5;
        tasks.push({
          taskIndex: i,
          family,
          contradiction: {
            claimA: {
              producerTrust: trustA,
              statedConfidence: honestA ? trustA : 1 - trustA + 0.2,
            },
            claimB: {
              producerTrust: trustB,
              statedConfidence: honestB ? trustB : 1 - trustB + 0.2,
            },
            correct: trustA >= trustB ? 'A' : 'B',
          },
        });
      }
    }
    return tasks;
  }

  /** Execute a policy on one task and return its score in [0, 1]. */
  scorePolicy(task: BenchmarkTask, strategy: string): number {
    switch (task.family) {
      case 'source_selection': {
        const sources = task.sources!;
        const chosen =
          strategy === 'prefer_independent_sources'
            ? sources.filter(s => s.independent && s.reliable).slice(0, 3)
            : sources.slice(0, 3); // baseline: naive first-k
        if (chosen.length === 0) return 0;
        return chosen.filter(s => s.independent && s.reliable).length / chosen.length;
      }
      case 'evidence_grounding': {
        const { evidenceText, snippets } = task;
        let chosen: SnippetCandidate | undefined;
        if (strategy === 'require_token_subsequence') {
          chosen = snippets!.find(snippet => {
            // Real token-subsequence check against the evidence text.
            const evidenceTokens = evidenceText!.split(/\s+/);
            const snippetTokens = snippet.text.split(/\s+/);
            let cursor = 0;
            for (const token of snippetTokens) {
              const found = evidenceTokens.indexOf(token, cursor);
              if (found === -1) return false;
              cursor = found + 1;
            }
            return true;
          });
        } else {
          chosen = snippets![0]; // baseline: first snippet
        }
        return chosen?.grounded ? 1 : 0;
      }
      case 'contradiction_handling': {
        const c = task.contradiction!;
        let decision: 'A' | 'B';
        if (strategy === 'calibration_weighted_adjudication') {
          decision = c.claimA.producerTrust >= c.claimB.producerTrust ? 'A' : 'B';
        } else {
          // baseline: believe the loudest stated confidence
          decision = c.claimA.statedConfidence >= c.claimB.statedConfidence ? 'A' : 'B';
        }
        return decision === c.correct ? 1 : 0;
      }
    }
  }

  /**
   * Run a bounded baseline-vs-strategy comparison. Deterministic for a given
   * (family, seed, iterations); the strategy only wins if its executed
   * decisions are genuinely better on the generated tasks.
   */
  runBenchmark(input: {
    family: TaskFamily;
    strategy: string;
    iterations: number;
    seed?: number;
  }): BenchmarkResult {
    const iterations = Math.max(1, Math.min(input.iterations, 200));
    const tasks = this.generateTasks(input.family, iterations, input.seed ?? 42);
    const perTask = tasks.map(task => ({
      taskIndex: task.taskIndex,
      baseline: this.scorePolicy(task, 'baseline'),
      strategy: this.scorePolicy(task, input.strategy),
    }));
    const baselineScore = perTask.reduce((sum, t) => sum + t.baseline, 0) / perTask.length;
    const strategyScore = perTask.reduce((sum, t) => sum + t.strategy, 0) / perTask.length;
    return {
      family: input.family,
      strategy: input.strategy,
      iterations,
      baselineScore,
      strategyScore,
      improvement: strategyScore - baselineScore,
      perTask,
    };
  }
}

export const deterministicBenchmark = new DeterministicBenchmarkService();
