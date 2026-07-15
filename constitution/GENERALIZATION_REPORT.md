# Architecture Generalization Report — Domain Neutrality Correction

- **Date:** 2026-07-15
- **Authorized by:** operator directive "AgentCo Constitutional Architecture Correction —
  Generalize All Domain-Specific Components" (2026-07-15)
- **Applied by:** Claude (build agent)
- **Scope:** the constitutional specification (`constitution/`), its diagrams, and an
  audit of runtime terminology, APIs, and seeded data for domain-specific assumptions.
- **Design rule applied:** *"Would this component still make sense if tomorrow AgentCo
  became interested in a completely new field that does not exist today?"* If no, it was
  refactored into a generalized framework.
- **Result:** 8 volume renames, 1 volume split (one new volume), 2 structural mandates,
  1 new permanently-enforced constitutional invariant, 4 code-level migration items.
  Checker enforcement proven (the domain lexicon flagged `Coder Civilization` and
  `Scientific Research` with exit 1 before the renames; green after).

---

## 1. The new constitutional invariant (directive §15)

**V0-INV-009 — Domain Neutrality** (tier: constitutional, status: **enforced**):

> No permanent architectural component may exist solely for a specific knowledge domain
> or profession — domain expertise emerges through the capability, domain, institution,
> and knowledge-discovery frameworks.

It applies to every future constitutional revision. Mechanical enforcement:
`scripts/constitution/check_constitution.py` scans every volume name in
`constitution/INDEX.md` against a domain/profession lexicon (coding, coder, physics,
chemistry, biology, finance, mathematics, medicine, robotics, law, science, …) and fails
CI on a match. Name-level scanning cannot judge *content*, so every volume review must
also apply the design rule above; the checker is the tripwire, not the whole defense.

## 2. Renames and splits applied to the constitutional specification

| Vol | Old name | New name | Directive |
|---|---|---|---|
| 25 | Coder Civilization | **Capability Evolution Framework** | §1 |
| 20 | Scientific Research | **Knowledge Discovery Framework** | §2 |
| 21 | World Models | **Reality Models** | §4 |
| 22 | Imagination Engine | **Hypothesis Generation Framework** | §5 |
| 24 | Response Intelligence | **Interaction Intelligence** | §6 |
| 18 | Self Model | **Civilization Self Model** (split) | §7 |
| 34 | — (new volume) | **Civilization Memory** (split from Self Model) | §7 |
| 19 | Architecture Evolution | **Structural Evolution Framework** | §9 |
| 27 | Superuser Control Plane | **Operator Control Plane** | §10 |

Structural mandates recorded without rename (names already mechanism-neutral):

- **V16 Autonomous Evolution** (§8): must be specified as six separated loops with
  distinct responsibilities — Autonomous Goal Generation, Autonomous Planning,
  Autonomous Execution, Autonomous Improvement, Autonomous Research, Autonomous
  Scheduling — not one monolithic subsystem.
- **V6 Institutions** (§11): must be specified as the emergent-institution lifecycle
  (capability gap → research proposal → temporary program → specialists assigned →
  evaluation → permanent institution *or* archived program), with creation, branching,
  merging, splitting, succession, retirement, and federation. No permanent institution
  without ongoing justification.

## 3. Item-by-item disposition

### §1 Coder Civilization → Capability Evolution Framework
Coding is one capability among many; nothing in the architecture may privilege it.
The framework (V25) defines how *any* capability is developed: repository/artifact
understanding, testing, migration, deployment, verification, and debugging generalize
to "understanding, exercising, validating, and operating the artifacts of a capability."
Existing code evidence that coding is already only an *instance*: the `selfcoding/`
Python stack is quarantined as non-canonical (`docs/civilization/CANONICAL_RUNTIME_MAP.md`),
and no backend service, route, or table is named for coding (verified by lexicon sweep
over `backend/src/`). Relationship to V15 (Capability Expansion): V25 defines the
*practice* of developing a capability; V15 defines the *gates* that admit, restrict, and
revoke it (migrations `102/103/106/107/139`). The universal lifecycle (§12 below) spans
both.

### §2 Scientific Research → Knowledge Discovery Framework
Science becomes one discovery methodology among: scientific experimentation, simulation,
formal proof, optimization, observation, benchmarking, adversarial evaluation, human
instruction, evidence synthesis, and future methodologies. V20 (charter tier) will
define the methodology registry; all methods must emit **evidence** into the existing
knowledge system (claims, provenance, contradictions — V9) rather than owning private
truth stores. Existing instances to generalize from: `evals/` (benchmarking),
`backend/tests/` (adversarial evaluation), the falsifiable-prediction machinery
(`backend/src/services/falsifiable-prediction.service.ts` — experimentation with
pre-registration and independent resolution).

### §3 Hardcoded domains → Dynamic Domain Framework
**Largely already implemented in code.** The architecture contains no `Physics
Institution` or similar: domains are runtime rows in `domain_registry`
(`backend/src/db/migrations/102_domain_registry.sql`) with lifecycle statuses
`proposed → active / suspended / rejected`, institution custody, trust thresholds, and
proof-of-competence linkage. Domain admission runs the five-stage expansion gate
(`139_capability_expansion.sql`: risk_review → benchmark_design → limited_trial →
calibration_review → governance_review) with append-only stage records; grants are
revocable (`capability_grants`). **Gap:** no `retired` status (migration item M1 below);
suspension exists, retirement does not.

### §4 World Models → Reality Models
Renamed (V21, charter). The model-class list (physical, biological, social, political,
legal, economic, computational, software, infrastructure, organizational, agent,
civilization, future unknown classes) must be an open registry, not an enum: the volume,
when written, must define model classes as data.

### §5 Imagination Engine → Hypothesis Generation Framework
Renamed (V22, charter). Imagination becomes one mechanism within hypothesis generation
(counterfactuals, alternative futures, architecture/institution/capability proposals,
research questions, optimization opportunities, uncertainty exploration). Outputs are
proposals into existing governed pipelines (governance proposals, expansion proposals,
learning candidates) — never direct state changes.

### §6 Response Intelligence → Interaction Intelligence
Renamed (V24). Conversation must not be the architectural center: chat is one
interaction mode among planning, execution, negotiation, governance, teaching,
explanation, simulation, supervision, inspection, collaboration, and future modes. The
volume must define mode-agnostic routing/verification/calibration obligations.

### §7 Self Model split → Civilization Memory (V34) + Civilization Self Model (V18)
Two different things were conflated: **memory** (historical knowledge: what happened,
what was learned, lineage) and **self model** (current structure: architecture graph,
dependency graph, institution graph, capability graph, topology graph, runtime graph,
evolution graph, health graph). V34 added to INDEX (statute, mixed — memory machinery
partially exists: `memory-promotion-pipeline.service.ts`, `memory-retrieval.service.ts`,
`agent_memories` + `event_log` migrations). V18 renamed (statute, prescriptive — the
graphs do not exist yet as first-class artifacts).

### §8 Autonomous Evolution split
Six separated loops mandated (see §2 above). Existing instance: the goal-formation tick
in the supervised runtime is an early Autonomous Goal Generation loop; the civilization
OS tick (`backend/src/services/civilization-os.service.ts`) is an early Autonomous
Scheduling loop. The volume must keep them separate rather than fusing them.

### §9 Architecture Evolution → Structural Evolution Framework
Renamed (V19). Architecture is one evolvable structure among: runtime, services,
institutions, governance, economy, communication, deployment, memory organization,
schedulers, organizational topology. The promotion pattern to reuse exists:
`backend/src/services/skill-canary.service.ts` and
`backend/src/services/safe-evolution.service.ts` (evaluator ≠ proposer, canary breach →
rollback).

### §10 Superuser → Operator Control Plane
V27 renamed. The interface component is the **Operator Interface** with modes Observe,
Inspect, Chat, Preview, Execute, Govern, Emergency; *superuser is one operator role*,
not the interface itself. Existing instances: override queue
(`backend/src/services/override-queue.service.ts`), kill switch
(`backend/src/services/kill-switch.service.ts`), governed emergency powers
(`backend/src/services/governance.service.ts`), operator console
(`frontend/src/app/civilization/page.tsx`).

### §11 Dynamic Institution Framework
Mandated for V6 (see §2 above). Compliance audit of today's seeds: the ten mandatory
institutions (`backend/src/services/institution-governance.service.ts`,
`MANDATORY_INSTITUTIONS`) are Evidence Court, Calibration Office, Safety Council,
Memory Bureau, Treasury, Evaluation Lab, Judiciary, Expansion Board, Identity Registry,
Observability Office — every one is a **constitutionally fundamental function**
(evidence, calibration/trust, safety, memory, resources, evaluation, justice,
expansion, identity, observability), not a knowledge-domain profession. They therefore
*pass* Domain Neutrality. They do **not** yet satisfy "no permanent institution without
ongoing justification" — the periodic-review mechanism is migration item M2.

### §12 Capability Evolution Framework — universal lifecycle
One lifecycle for every capability, no exceptions: capability gap → verification →
research → knowledge acquisition → experimentation → implementation → evaluation →
independent verification → promotion → monitoring → restriction or retirement.
Mapping to existing machinery: gap detection (generality tracker, migration `103`),
verification/evaluation (proof-of-competence, migration `106`; Evaluation Lab mandate),
independent verification (evaluator ≠ proposer in
`backend/src/services/safe-evolution.service.ts`), promotion/rollback (skill promotion
loop, migration `108`), restriction/revocation (`capability_grants` +
`assertCapabilityGranted` in `backend/src/services/capability-expansion.service.ts`).
The V25 volume must bind these stages into one named lifecycle and close the stage gaps
(research and knowledge-acquisition stages have no first-class records today — M4).

### §13 Universal Domain Principle
Adding a new discipline must require **no new architectural layer, no new runtime, no
constitutional redesign** — only domain registration, institution evolution, capability
development, knowledge acquisition. Walkthrough against today's code: a genuinely new
field would be (1) registered in `domain_registry` (102), (2) admitted through the
five-stage expansion gate (139), (3) assigned to an institution created through the
governed institution APIs (131), (4) exercised by citizens under capability grants with
trust-linked budgets (130/134). **The principle holds structurally today** — no schema
or service names a discipline. Verified by lexicon sweep: no banned domain term appears
as a table, service, or route name in `backend/src/` (the only hits are generic words
inside documentation strings).

## 4. Audit table (directive §14)

| Current name | Why too specific | Replacement | Migration impact | Affected docs | Affected diagrams | Dependency-graph impact | Backward compat | Priority |
|---|---|---|---|---|---|---|---|---|
| Coder Civilization (V25) | Privileges one profession (coding) as architecture | Capability Evolution Framework | Spec-only now; `selfcoding/` remains one capability instance | INDEX, VOL-00 | VOL-00 layer chain | V25 now feeds V15 gates for *all* capabilities | Old name persists only in historical docs | done (spec) |
| Scientific Research (V20) | Elevates one discovery methodology to the governing abstraction | Knowledge Discovery Framework | Spec-only; `evals/` becomes one methodology instance | INDEX, VOL-00 | VOL-00 layer chain | V20 emits evidence into V9 instead of owning truth | same | done (spec) |
| World Models (V21) | "World" implied a fixed model taxonomy | Reality Models (open model-class registry) | Spec-only | INDEX, VOL-00 | VOL-00 layer chain | unchanged | same | done (spec) |
| Imagination Engine (V22) | Mechanism named for one cognitive style | Hypothesis Generation Framework | Spec-only | INDEX, VOL-00 | VOL-00 layer chain | outputs route into governed proposal pipelines | same | done (spec) |
| Response Intelligence (V24) | Centers conversation/chat | Interaction Intelligence (modes registry) | Spec-only | INDEX, VOL-00 | VOL-00 layer chain | unchanged | same | done (spec) |
| Self Model (V18) | Conflated history with structure | Civilization Self Model (V18) + Civilization Memory (V34) | Spec-only; V34 added | INDEX, VOL-00 | VOL-00 layer chain | V34 depends on V9; V18 depends on V17 | none | done (spec) |
| Architecture Evolution (V19) | Architecture is one structure among many | Structural Evolution Framework | Spec-only | INDEX, VOL-00 | VOL-00 layer chain | unchanged | same | done (spec) |
| Superuser Control Plane (V27) | Names a single role as the plane | Operator Control Plane (Operator Interface, 7 modes; superuser = one role) | Spec-only | INDEX, VOL-00 | VOL-00 layer chain | unchanged | same | done (spec) |
| Autonomous Evolution (V16, monolith) | One loop hid six responsibilities | Six separated autonomous loops | Spec mandate; loops land when V16 is written/implemented | INDEX note | none | six loop nodes replace one | n/a | volume-writing time |
| `domain_registry` lifecycle (code) | No retirement state — domains can only be suspended/rejected | add `retired` status (M1) | one small migration + service/service-test updates | V15 volume | none | none | additive enum change | medium |
| `MANDATORY_INSTITUTIONS` seed (code) | Permanent by seed; no ongoing justification | periodic justification review via governance (M2) | new review mechanism in institution-governance + scheduler tick | V6 volume | none | V6→V12 review edge | seeds unchanged; review added on top | medium |
| Five-department template (code, `institutions.service.ts`) | Fixed structural template for every institution | emergent department structure per institution charter (M3) | service change + migration for department provenance | V6 volume | none | none | existing departments remain valid | low |
| `SPECIALIST_ROLES` constant (code, `backend/src/types/specialist-roles.ts`) | Compile-time role catalogue, not a registry | registry-driven roles with lifecycle (M5) | move catalogue to DB registry seeded from current constant | V26 volume | none | roles become runtime entities | constant becomes the seed | low |
| Research/acquisition lifecycle stages (code gap) | Universal capability lifecycle has unrecorded stages | first-class records for research + knowledge-acquisition stages (M4) | schema addition bound to expansion proposals | V25/V15 volumes | none | none | additive | medium |

**No domain-profession violations were found in runtime terminology, APIs, tables, or
seeded names** — the ossification was confined to the constitutional plan's volume
names, which are now corrected and mechanically policed.

## 5. What was deliberately not changed

- **Historical documents** (`docs/civilization/PLAN_AND_PROGRESS.md`, build briefs,
  ledgers, `AGENTCO_REPO_AUDIT.md`) keep their original wording: they are records of
  what happened, and rewriting history would itself be drift. Readers should treat any
  old names there as superseded by this report.
- **Working, tested code** (C0–C15 services, migrations): no rename churn was applied to
  code because the audit found no domain-specific top-level component in it. The
  migration items above (M1–M5) are recorded for their owning volumes' implementation
  phases rather than executed as an unreviewed mass refactor.
- **`selfcoding/`, `evals/`, `runtime/`** Python stacks: quarantined/advisory per
  `docs/civilization/CANONICAL_RUNTIME_MAP.md`; they are instances of capabilities and
  methodologies, not architecture.

## 6. Completion criteria mapping (directive)

| Criterion | Status |
|---|---|
| All domain-specific top-level architecture generalized | ✅ 8 renames + 1 split in INDEX/VOL-00; checker-enforced |
| Coding treated as one capability among many | ✅ V25 reframed; `selfcoding/` = instance; no privileged code paths found |
| Science treated as one discovery methodology among many | ✅ V20 reframed with methodology registry mandate |
| Institutions emerge dynamically instead of predefined | ✅ mandate recorded for V6; seeds audited (function-fundamental); M2/M3 track the remaining mechanisms |
| Domains are runtime entities, not architectural assumptions | ✅ already true in code (`domain_registry` + 5-stage gate); M1 adds retirement |
| Diagrams, documentation, dependency graphs, APIs, runtime terminology, constitutional references reflect the design | ✅ VOL-00 diagram + INDEX + invariants updated; APIs/terminology audited clean; historical docs intentionally preserved |
| A new discipline requires no structural redesign | ✅ walkthrough in §3 (§13) against existing mechanisms |
| Architecture Generalization Report | ✅ this document |

The invariant V0-INV-009 makes this correction permanent: any future volume or revision
that names a domain or profession as architecture fails CI.
