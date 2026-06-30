#!/usr/bin/env ts-node
/**
 * Bounded Civilization Learning Run CLI
 * =====================================
 *
 * Usage:
 *   ts-node src/cli/run-bounded-learning.ts --goal "Learn about AI safety" \
 *     --source-pack ai_tech --max-pages 3 --provider openai --real-web-enabled true
 *
 *   # Dry run (discovery only, no fetching)
 *   ts-node src/cli/run-bounded-learning.ts --goal "Test source discovery" \
 *     --source-pack technical --dry-run true
 *
 *   # Local fixtures only (no real web)
 *   ts-node src/cli/run-bounded-learning.ts --goal "Test pipeline" \
 *     --source-pack ai_tech --provider deterministic_test_only
 */

import * as fs from 'fs';
import * as path from 'path';
import { BoundedCivilizationLearningRun } from '../services/bounded-learning-run.service';
import { assertDeterministicProviderAllowed } from '../runtime-mode';

// Load .codex.env if available
const codexEnvPath = path.join(__dirname, '../../.codex.env');
if (fs.existsSync(codexEnvPath)) {
  const codexEnv = fs.readFileSync(codexEnvPath, 'utf-8');
  for (const line of codexEnv.split('\n')) {
    if (line.startsWith('export ')) {
      const match = line.match(/export\s+(\w+)=(.*)$/);
      if (match) {
        const [, key, value] = match;
        if (!process.env[key]) {
          process.env[key] = value;
        }
      }
    }
  }
}

interface CliArgs {
  goal: string;
  sourcePack: string;
  maxPages?: number;
  maxClaims?: number;
  maxDurationSeconds?: number;
  allowedDomains?: string[];
  deniedDomains?: string[];
  provider?: 'openai' | 'local_llm' | 'deterministic_test_only';
  dryRun?: boolean;
  realWebEnabled?: boolean;
}

export function parseArgs(argv: string[] = process.argv.slice(2)): CliArgs {
  const args = argv;
  const parsed: any = {
    goal: '',
    sourcePack: 'technical',
    maxPages: 5,
    maxClaims: 20,
    maxDurationSeconds: 300,
    provider: 'local_llm',
    dryRun: false,
    realWebEnabled: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--goal') {
      parsed.goal = args[++i];
    } else if (arg === '--source-pack') {
      parsed.sourcePack = args[++i];
    } else if (arg === '--max-pages') {
      parsed.maxPages = parseInt(args[++i], 10);
    } else if (arg === '--max-claims') {
      parsed.maxClaims = parseInt(args[++i], 10);
    } else if (arg === '--max-duration') {
      parsed.maxDurationSeconds = parseInt(args[++i], 10);
    } else if (arg === '--allowed-domains') {
      parsed.allowedDomains = args[++i].split(',');
    } else if (arg === '--denied-domains') {
      parsed.deniedDomains = args[++i].split(',');
    } else if (arg === '--provider') {
      parsed.provider = args[++i];
    } else if (arg === '--dry-run') {
      parsed.dryRun = args[++i].toLowerCase() === 'true';
    } else if (arg === '--real-web-enabled') {
      parsed.realWebEnabled = args[++i].toLowerCase() === 'true';
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    }
  }

  if (!parsed.goal) {
    console.error('Error: --goal is required');
    printHelp();
    process.exit(1);
  }

  return parsed;
}

function printHelp(): void {
  console.log(`
Bounded Civilization Learning Run CLI
=====================================

USAGE:
  ts-node src/cli/run-bounded-learning.ts [OPTIONS]

REQUIRED OPTIONS:
  --goal TEXT
    Learning goal/topic (e.g., "Learn about AI safety from recent sources")

OPTIONAL OPTIONS:
  --source-pack PACK
    Source pack to use (default: technical)
    Options: technical, ai_tech, scientific, business, governance

  --max-pages N
    Maximum pages to fetch (default: 5)

  --max-claims N
    Maximum claims to extract (default: 20)

  --max-duration N
    Maximum duration in seconds (default: 300)

  --provider PROVIDER
    LLM provider for claim extraction (default: local_llm)
    Options: openai, local_llm, deterministic_test_only

  --allowed-domains DOMAIN1,DOMAIN2,...
    Comma-separated list of allowed domains

  --denied-domains DOMAIN1,DOMAIN2,...
    Comma-separated list of denied domains

  --dry-run true|false
    Run in dry-run mode (discovery only, no fetching)
    (default: false)

  --real-web-enabled true|false
    Enable fetching from real public internet
    (default: false)

  --help, -h
    Show this help message

EXAMPLES:

  # Learn from AI tech sources with OpenAI extraction
  ts-node src/cli/run-bounded-learning.ts \\
    --goal "Learn about latest AI autonomy research" \\
    --source-pack ai_tech \\
    --max-pages 5 \\
    --provider openai \\
    --real-web-enabled true

  # Dry run to test source discovery
  ts-node src/cli/run-bounded-learning.ts \\
    --goal "Test source discovery" \\
    --source-pack technical \\
    --dry-run true

  # Local fixtures only
  ts-node src/cli/run-bounded-learning.ts \\
    --goal "Test the pipeline" \\
    --source-pack ai_tech \\
    --provider deterministic_test_only

  # With allowed domains
  ts-node src/cli/run-bounded-learning.ts \\
    --goal "Learn from safe sources" \\
    --source-pack technical \\
    --allowed-domains github.com,arxiv.org \\
    --real-web-enabled true

NOTES:
  - OpenAI provider requires OPENAI_API_KEY environment variable
  - Real web fetching respects robots.txt and rate limits
  - Claims from deterministic_test_only are labeled as fixtures
  - All operations are logged in autonomy_audit_events table
  `);
}

export async function main(argv: string[] = process.argv.slice(2)): Promise<void> {
  const args = parseArgs(argv);

  console.log(`\nLoading configuration...`);
  console.log(`  LLM Provider: ${process.env.LLM_PROVIDER}`);
  console.log(`  LLM Model: ${process.env.LLM_MODEL_DEFAULT}`);
  console.log(`  OpenAI API Key: ${process.env.OPENAI_API_KEY ? '(set)' : '(not set)'}`);
  console.log(`  LLM API Key: ${process.env.LLM_API_KEY ? '(set)' : '(not set)'}`);

  try {
    assertDeterministicProviderAllowed('bounded_learning.provider', args.provider);
    const orchestrator = new BoundedCivilizationLearningRun();
    const result = await orchestrator.execute({
      goal: args.goal,
      sourcePack: args.sourcePack,
      maxPages: args.maxPages,
      maxClaims: args.maxClaims,
      maxDurationSeconds: args.maxDurationSeconds,
      allowedDomains: args.allowedDomains,
      deniedDomains: args.deniedDomains,
      provider: args.provider as any,
      dryRun: args.dryRun,
      realWebEnabled: args.realWebEnabled,
    });

    // Write results to file
    const resultsFile = `learning_run_${result.runId}.json`;
    fs.writeFileSync(resultsFile, JSON.stringify(result, null, 2));
    console.log(`\n📄 Results saved to: ${resultsFile}`);

    process.exit(result.status === 'success' ? 0 : 1);
  } catch (error: any) {
    console.error(`\n❌ Error: ${error.message}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
