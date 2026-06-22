# Agentco

Agentco is an evidence-governed control plane for autonomous systems: if an agent acts through Agentco, you can inspect the policy that governed it, the evidence it relied on, the calibration record behind its confidence, the attested environment it ran in, and the exact conditions under which it was permitted to affect the world.

## Status

Agentco is under refoundation. Claims in this repository use explicit status labels:

- **REAL**: implemented and proven by passing tests on real or external evidence.
- **FIXTURE**: implemented and proven only against internally-authored deterministic fixtures.
- **EXTERNAL-VALIDATED**: proven against an external benchmark or independent ground truth the repo did not author.
- **PARTIAL**: partially implemented; the implemented slice is specified.
- **FACADE**: named or scaffolded but not functional.
- **BROKEN / MISSING / DEPRECATED**: self-explanatory.

The long-range R&D vision is kept separately in [NORTH_STAR.md](docs/refoundation/NORTH_STAR.md). Product surfaces should only claim capabilities proven by tests.

## Trustworthiness Measurement & Benchmarking

Agentco now includes a rigorous platform for measuring LLM and agent trustworthiness:

### Core Platform (Proven)
- **Canonical Uncertainty Schema** — Unified representation for confidence, entropy, abstention, and provenance
- **Evaluation Framework** — Benchmark manifests, trial records, grading results with append-only audit trail
- **Pluggable Graders** — Exact match, normalized string, JSON fields, abstention-aware, tool-use success
- **Benchmark Registry** — YAML-based benchmark definitions with reproducible dataset hashing
- **Evaluation Runner** — Orchestrates model inference, grading, and uncertainty capture with optional DB persistence

**Status:** 76/76 tests passing | `python3 -m pytest evals/core -q`

### Enterprise Vendor Risk Triage Benchmark (Smoke-Test Ready)

High-stakes enterprise problem that exposes LLM failure modes:
- **15 realistic scenarios** — Compliance gaps, geopolitical risks, hallucination traps, policy violations
- **Comprehensive scoring** — Decision accuracy (25%), risk level (15%), evidence discipline (15%), policy compliance (15%), hallucination avoidance (10%), calibration (10%), escalation (10%)
- **Multi-provider comparison** — Adapters for Agentco, OpenAI, Anthropic, Google, Mistral, Ollama (fake:deterministic proven)
- **Zero-credential smoke tests** — Run without any API keys: `make vendor-risk-smoke`
- **Leaderboard generation** — JSON + Markdown results with metric interpretation

**Status:** 10/10 tests passing | Deterministic fake model achieves 0.711 trustworthiness score | See [benchmark guide](docs/agentco_vs_llms_vendor_risk_benchmark.md)

## Current Proven Surface

| Capability | Status | Proof |
|---|---|---|
| Calibration, trusted confidence, reality firewall, learning-loop regression slice | **FIXTURE** | `python3 -m pytest calibration runtime learning synthesis evals/regression -q` |
| Backend audit log, event bus, memory store, override queue services | **PARTIAL** | `backend/tests/integration/*` require local Postgres/Kafka setup |
| Frontend operator dashboard | **PARTIAL** | Next.js source exists; dependency install required before TS/build verification |
| Trustworthiness measurement platform: uncertainty schema, evaluation framework, grader registry | **REAL** | `python3 -m pytest evals/core -q` (76/76 tests) |
| Enterprise vendor risk triage benchmark: 15 scenarios, multi-provider comparison, policy compliance scoring | **FIXTURE** | `make vendor-risk-smoke` (deterministic fake model, 10/10 tests) |
| Durable execution, external attestation, canonical source independence, full governance DSL | **MISSING** | Tracked in [IMPLEMENTATION_MATRIX.md](docs/refoundation/IMPLEMENTATION_MATRIX.md) |

## Local Development

### Core Setup
```bash
make dev
make smoke
```

`make dev` installs frontend/backend dependencies and starts local infrastructure. `make smoke` runs the local Python smoke slice and checks backend/frontend type surfaces when dependencies are installed.

For write-auth testing, set the same key in backend and frontend:
```bash
export AGENTCO_API_KEY=dev-agentco-key
export NEXT_PUBLIC_AGENTCO_API_KEY=dev-agentco-key
```

When `AGENTCO_API_KEY` is unset, backend write-auth is disabled for local bring-up.

### Trustworthiness Benchmarks

Run without external credentials:
```bash
make vendor-risk-smoke      # Deterministic vendor risk benchmark (10 sec)
```

Run with real provider credentials:
```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...

make vendor-risk-full       # Compare Agentco + real LLMs
```

Results appear in `/results/enterprise_vendor_risk/latest.md` (human-readable leaderboard).

## Roadmap: Trustworthiness Platform

### Completed (Phase 1 & 2)
- ✅ Canonical uncertainty schema with validation and persistence
- ✅ Evaluation framework (manifests, trial records, grading results)
- ✅ Pluggable grader registry with 6 grader types
- ✅ Benchmark registry and runner
- ✅ Enterprise vendor risk triage benchmark: 15 scenarios, fake deterministic model, scoring
- ✅ Leaderboard generation (JSON + Markdown)
- ✅ Comprehensive test suite (86/86 tests)

### In Progress (Phase 3)
- 🔄 Agentco runtime integration (current: stubbed; needs: actual runtime API + tool-calling)
- 🔄 External LLM adapters (OpenAI, Anthropic, Google, Mistral, Ollama)
- 🔄 Real-world validation with actual provider credentials

### Future (Phase 4+)
- Real-time leaderboard dashboard with historical tracking
- Additional benchmarks (customer support, incident triage, code review, hiring decisions)
- Automated red-teaming and adversarial case generation
- Integration with CI/CD for continuous trustworthiness tracking
- Fine-tuning playground and performance regression detection
- Multi-dimensional trustworthiness certification (iso-trustworthiness regions)

## Architecture and Refoundation Docs

- [Agentco vs LLMs: Vendor Risk Triage Benchmark](docs/agentco_vs_llms_vendor_risk_benchmark.md)
- [True North](docs/refoundation/AGENTCO_TRUE_NORTH.md)
- [Current State Audit](docs/refoundation/CURRENT_STATE_AUDIT.md)
- [Implementation Matrix](docs/refoundation/IMPLEMENTATION_MATRIX.md)
- [Build Plan](docs/refoundation/BUILD_PLAN.md)
- [Layer Contracts](docs/refoundation/LAYER_CONTRACTS.md)
- [Repo Truth Ledger](docs/refoundation/REPO_TRUTH_LEDGER.md)
- [Validation Plan](docs/refoundation/VALIDATION_PLAN.md)
- [Testing](docs/refoundation/TESTING.md)
- [Session Handoff](docs/refoundation/SESSION_HANDOFF.md)
