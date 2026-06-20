# Master Learning & Epistemic Resilience Baseline

**Date:** 2026-06-20  
**Current Branch:** `codex/full-civilization-gated-build`  
**Starting Commit:** `5dbafb2` (evals: update phase 15 acceptance test results)  
**Task:** Implement Universal Learning Layer (Phases 1–16) + Epistemic Resilience Layer (Phases 17–24)

---

## Current Repository State

### What Previous Codex Build Phases Completed

The `codex/full-civilization-gated-build` branch has implemented phases 1–15:

- **Phase 1–6:** Core calibration, reserve, ledger infrastructure
- **Phase 7–8:** Agent reputation and department models
- **Phase 9–10:** Institution kernel with bounded contracts
- **Phase 11–12:** Governance and memory services
- **Phase 13–15:** Society layer, civilization constitution, lifecycle evolution

### Existing Calibration Infrastructure

| File | Status | Purpose |
|------|--------|---------|
| `calibration/ledger/prediction_ledger.py` | ✓ Shipped | Pre-registration, immutable claim ledger |
| `calibration/ledger/schema.sql` | ✓ Shipped | Ledger persistence |
| `calibration/resolution/resolution_service.py` | ✓ Shipped | External evidence resolution |
| `calibration/resolution/source_independence.py` | ✓ Shipped | Independence checking for sources |
| `calibration/scoring/scoring_module.py` | ✓ Shipped | Brier/log scoring |
| `calibration/trust/trust_controller.py` | ✓ Shipped | Trust updates |
| `calibration/firewall/firewall.py` | ✓ Shipped | Authority checks |

**Calibration Ledger Interface:**

```python
# From prediction_ledger.py
class PredictionRecord:
    prediction_id: str
    claim: str
    probability: float
    confidence_basis: dict[str, Any]
    producing_agent_id: str
    resolution_criterion: str
    resolution_date: datetime
    ground_truth_source: str
    domain: str
    claim_type: str
    # Resolution fields (None until resolved)
    resolved: bool
    resolved_outcome: Optional[bool]
    resolved_at: Optional[datetime]
    brier_score: Optional[float]
    log_score: Optional[float]
    was_surprise: bool
    claim_source_url: Optional[str]
    claim_source_canonical_url: Optional[str]
    claim_source_fingerprint: Optional[str]
    claim_evidence_hash: Optional[str]
```

### Existing Civilization / Governance Infrastructure

| File | Purpose |
|------|---------|
| `civilization/services/institution_service.py` | Institution creation, contracts, departments |
| `civilization/services/governance_service.py` | Governance policies, votes, promotion decisions |
| `civilization/services/review_service.py` | Institution reviews of claims/decisions |
| `civilization/services/reputation_service.py` | Trust/reputation scoring |
| `civilization/services/memory_service.py` | Institutional memory storage |
| `civilization/services/dispute_service.py` | Dispute/contradiction tracking |
| `civilization/services/jurisdiction_service.py` | Authority domain mapping |
| `civilization/services/economy_service.py` | Budget and resource allocation |

**Governance Interface Signature:**

```python
# From governance_service.py (partial)
class GovernanceService:
    def propose_policy(policy: dict) -> policy_id
    def vote_on_policy(policy_id, voter_institution_id, vote: bool)
    def resolve_policy(policy_id) -> approved: bool
    def register_authority_gate(gate_name, required_calibration, required_reputation)
```

### Existing Memory Systems

| File | Purpose |
|------|---------|
| `civilization/services/memory_service.py` | Institutional memory |
| `civilization/services/civilization_memory_service.py` | Constitutional/civilizational memory |
| `agents/core/memory/learning_loop.py` | Learning loop integration |

**Memory Interface Signature:**

```python
# From memory_service.py
class MemoryService:
    def store_memory(entity_id, memory_type, content, metadata)
    def retrieve_memory(entity_id, memory_type, query_filters)
    def link_memory_to_claim(memory_id, claim_id)
```

### Existing Learning / Testing Infrastructure

| File | Purpose |
|------|---------|
| `learning/learning_loop.py` | Scaffold learning loop |
| `learning/trainer_agent/trainer_agent.py` | Learning agent |
| `learning/intelligence_agent/intelligence_agent.py` | Intelligence gathering |
| `tests/civilization/` | Civilization integration tests |
| `evals/acceptance/` | Phase acceptance traces and fixtures |

---

## Gaps This Master Prompt Fills

### Universal Learning Layer Gaps (Phases 1–16)

| Gap | Current State | This Prompt Fills |
|-----|---------------|--------------------|
| Knowledge Claim model | Scaffold only | Full dataclass, validation, provenance hashing, status transitions |
| Source Registry | Partial via URLs in predictions | Full registry with fingerprinting, derivation tracking, independence checks |
| Medium adapters | None shipped | Text, PDF, web, video/audio transcripts, slides, code, dataset, human feedback adapters |
| Scientific Evidence Engine | Partial in resolution service | Full classification hierarchy, limitations detection, replication marking |
| Curiosity Engine | None | Novel/contradiction/uncertainty signals, learning mission ranking |
| Hypothesis Engine | Partial (pre-registration only) | Pre-registration, calibration linking, test plan generation |
| Sandbox Experiment Lab | None | Deterministic fixture experiments, result hashing, audit traces |
| Learning Memory System | Partial memory service | Layered: raw, semantic, episodic, procedural, calibration, institutional, civilizational |
| Cross-Domain Synthesis | None | Principle extraction, transfer hypotheses, assumption mapping, failure modes |
| Learning Institutions | Blueprint in civilization services | Full contracts, department mappings, promotion rules, learning missions |
| Learning Governance | Partial (governance service exists) | Promotion workflow, evidence requirements per level, dispute blocking |
| Learning Scorecard | Evals traces only | Formal metrics: extraction accuracy, promotion rate, false belief detection |
| Autonomous Learning Loop | Scaffold | Bounded loop, read-only sandbox, deterministic test mode, audit export |
| Universal Learning Demo | None | Deterministic end-to-end example |

### Epistemic Resilience Layer Gaps (Phases 17–24)

| Gap | Current State | This Prompt Fills |
|-----|---------------|--------------------|
| Truth Maintenance (TMS) | None | Dependency-directed belief revision, justification tracking, circular detection |
| Claim Identity as Fallible | Partial hashing | Graded verdicts, method tracking, escalation on uncertainty |
| Contradiction as Fallible | Contradiction search noted | Graded verdicts, scope tracking, conditional/domain-bounded tension |
| Reflexive Evidence Priors | Static hierarchy | Domain-scoped priors, track record, anomaly detection, governance-gated recalibration |
| Adversarial Epistemic Security | Partial via firewall | Injection detection, independence laundering, citation rings, promotion gradient anomalies |
| Normative Reasoning Path | None | is/ought split, deliberation vs empirical verification, constitutional coherence check |
| Value-of-Information Triage | None | Consequence scoring, cost estimation, budget-gated learning missions |
| Epistemic Polity & Incentives | Governance exists | Separation of powers enforced, no-profit-from-falsehood invariant, disconfirmation rewards |
| Red-Team Evaluation | Evals exist | Adversarial scenarios, attack surfaces, defense verification |

---

## Existing Resolution Independence Interface

From `calibration/resolution/source_independence.py`:

```python
def is_independent_source(source_id_a: str, source_id_b: str, source_registry: dict) -> bool
def detect_derivative_source(source_a, source_b) -> bool
def compute_source_fingerprint(source_uri: str, content: str) -> str
def detect_same_canonical_source(uri_a: str, uri_b: str) -> bool
```

This is the foundation for Phase 3 (Source Registry) and will be extended in Phase 20.

---

## Existing Audit & Trust Interfaces

From various services:

```python
# Audit
class AuditTrace:
    event_id: str
    timestamp: datetime
    actor_id: str
    action: str
    target_id: str
    change: dict

# Trust / Reputation
class TrustRecord:
    entity_id: str
    trust_score: float
    confidence: float
    resolution_count: int
    brier_score: float
    last_updated: datetime
```

---

## Database Migrations Already Shipped

**Backend Migrations (Backend/reserve):**
- 001–016: Agent state, memory, beliefs, prediction ledger, decision chains
- 006–013 (reserve): Civilization, society, jurisdiction, disputes, economy, constitution, memory, lifecycle

These migrations provide schema for:
- Predictions and resolutions
- Institution/society/civilization entities
- Memory storage (agent, institutional, civilizational)
- Audit traces
- Trust/reputation records

---

## Commands Run Before Modification

```bash
# Current status
git status
# On branch codex/full-civilization-gated-build
# Untracked files: (none after commit)

# Recent commits
git log --oneline -10
# 5dbafb2 evals: update phase 15 acceptance test results and calibration data
# 2fdbae7 docs: record phase 14 status
# ... (phases 1-14)

# Available tests
make test  # (would run all tests if run now)
make smoke # (would run smoke tests)

# Existing evaluation infrastructure
ls -la evals/
# evals/acceptance/, evals/regression/, evals/financial_calibration_toolkit/
```

---

## Test Status at Baseline

Test infrastructure exists. All prior phase tests expected passing (as indicated by commit history without "fix" commits).

This baseline did not run all tests to preserve context. Next action after each phase: run phase-specific tests.

---

## Known Limits at Baseline

1. **Medium adapters:** Only PDF parsing, video/audio transcription are scaffold points. Heavy OCR/transcription dependencies not bundled. Tests use deterministic fixtures.

2. **Semantic judgment engines:** Identity, contradiction, independence are heuristic. Methods layered; embedding hook has deterministic stub for tests.

3. **Source trust:** No ML-based source modeling. Trust scored by institutional review and track record only.

4. **Adversarial security:** Heuristic detection. Injection scanning is signature-based on fixture tests. Real-world adversary complexity exceeds Phase 20.

5. **Normative reasoning:** Coherence check is institutional audit, not philosophical solver. Unresolved value conflicts block promotion; system does not adjudicate ethics.

6. **External human deliberation:** Not shipped. Governance review is institutional (agent-modeled), not human-participatory.

---

## Next Steps

1. ✅ **Created:** MASTER_LEARNING_RESILIENCE_BASELINE.md
2. **Phase 1 (this turn):** Core learning architecture documents
3. **Phase 2:** Knowledge Claim model and validation
4. **Phase 3:** Source Registry with fingerprinting
5. ... (Phases 4–16 for Universal Learning)
6. ... (Phases 17–24 for Epistemic Resilience)
7. **Final:** Red-team evaluation + integration + final report

---

## Reuse Strategy

All phases will:
- **Extend, not duplicate**, existing calibration, resolution, governance, memory, institution, society, civilization services
- **Use PredictionRecord as Evidence Record** where claims enter the calibration ledger
- **Use GovernanceService for Knowledge Promotion** decisions
- **Use MemoryService for Learning Traces** (raw, semantic, episodic, etc.)
- **Use InstitutionService for Learning Institution Contracts** and department roles
- **Use AuditTrace for all auditable decisions** in the learning pipeline
- **Use TrustRecord to track Learning Institution calibration** (how well Discovery, Replication, Adversarial Critique, etc. perform)

This ensures learning is not a parallel system but an integral layer within the civilization architecture.

---

## Architecture Principle

> Agentco must be free to learn from everything, but disciplined enough to believe only what survives evidence and governance.

The Universal Learning Layer provides freedom: learn from any medium without immediate commitment.

The Epistemic Resilience Layer provides discipline: revision, fallible judgment, adversarial security, incentive alignment, and no profit from falsehood.

Together they form a civilization-grade epistemic system.

---

**Ready to proceed to Phase 1: Core Learning Architecture Documents**
