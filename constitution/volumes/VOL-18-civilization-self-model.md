# Volume 18 — Civilization Self Model

## 1. Header

| Field | Value |
|---|---|
| Volume | 18 |
| Name | Civilization Self Model |
| Tier | statute |
| Epistemic status | prescriptive |
| Doc status | written |
| Related volumes | V17 (Self Inspection), V34 (Civilization Memory), V19 (Structural Evolution Framework), V16 (Autonomous Evolution), V28 (Operator Experience) |

## 2. Purpose

The Self Model is AgentCo's structured understanding of *its own present structure* — the
graphs of services, dependencies, institutions, capabilities, topology, runtime, evolution,
and health. It is deliberately separated from Civilization Memory (V34): Memory is *what
happened* (history, lineage), the Self Model is *what currently is* (structure). This
separation was mandated by the Domain Neutrality correction
(`GENERALIZATION_REPORT.md` §7). Prescriptive tier: the Self Model as a first-class,
queryable set of graphs does **not** yet exist; this volume is the design to build, and
§9 cites honestly the partial substrate that seeds it.

```text
CIVILIZATION SELF MODEL (to build) — graphs kept current from the live system:
   ├─ architecture graph   services, modules, boundaries
   ├─ dependency graph     who calls whom            (seed: reachability snapshot)
   ├─ institution graph    institutions, mandates, jurisdictions   (V6)
   ├─ capability graph     domains, skills, grants   (V15)
   ├─ topology graph       runtime processes, workers, queues       (V3, V29)
   ├─ runtime graph        live health, leaders, ticks              (V17 doctor)
   ├─ evolution graph      version lineage, migrations              (V2, V19)
   └─ health graph         SLO/error/latency signals                (V29)
   ▲
   built by  ◄── Self Inspection (V17) reads artifacts and populates the model
   used by   ──► Structural Evolution (V19), Autonomous Evolution (V16),
                 Operator Experience (V28 explorers)
```

## 3. Definitions

- **Self Model** — the queryable set of graphs describing the system's current structure
  (to be built).
- **Architecture graph** — services/modules and their boundaries.
- **Dependency graph** — the call/uses relationships between services (partial seed:
  `scripts/generate_runtime_reachability.py` `direct_dependencies` / `service_chain`).
- **Institution / capability / topology / runtime / evolution / health graph** — the
  structural views listed above, each sourced from its owning volume.
- **Component inventory** — the enumeration of built components (partial seed:
  `BUILD_LEDGER.yaml`, `CIVILIZATION_BUILD_LEDGER.yaml`).
- **Currency** — the property that the model reflects the live system, not a stale
  snapshot (the hard part; ties to V17's `--check` discipline).

## 4. Invariants

Prescriptive: most are planned. The two enforced entries are genuine partial seeds, named
as such — not claims that the Self Model exists.

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V18-INV-001 | A machine-readable component inventory of the system exists (the seed of the architecture graph). | enforced | `BUILD_LEDGER.yaml`, `CIVILIZATION_BUILD_LEDGER.yaml` |
| V18-INV-002 | A conservative static dependency snapshot of entry points to services exists (the seed of the dependency graph). | enforced | `scripts/generate_runtime_reachability.py` |
| V18-INV-003 | The Self Model represents the architecture graph — services, modules, and their boundaries — as first-class queryable data. | planned | — |
| V18-INV-004 | The Self Model represents the dependency graph and is kept current from the live system, not a manual snapshot. | planned | — |
| V18-INV-005 | The Self Model represents the institution, capability, and topology graphs, sourced from their owning subsystems. | planned | — |
| V18-INV-006 | The Self Model represents the evolution graph (version lineage and migrations) and the health graph (live operational signals). | planned | — |
| V18-INV-007 | The Self Model is populated by Self Inspection (V17) and is provably current — a drift between model and reality fails a check. | planned | — |
| V18-INV-008 | The Self Model is queryable by the operator (V28) and by Autonomous/Structural Evolution (V16/V19) as the substrate for change decisions. | planned | — |
| V18-INV-009 | The Self Model is strictly separated from Civilization Memory (V34): structure-now versus history. | planned | — |

## 5. Interfaces

Prescriptive — the intended interface:

- **Builder** — Self Inspection (V17) inspectors populate the model from artifacts
  (ledger, reachability, migrations, route matrix, health).
- **Query** — a read API returning each graph (for the operator explorers, V28).
- **Consumers** — Structural Evolution (V19) reads the architecture/dependency graphs to
  plan changes; Autonomous Evolution (V16) reads the capability/health graphs to pick
  goals.
- **Partial substrate today** — `BUILD_LEDGER.yaml` (inventory),
  `scripts/generate_runtime_reachability.py` (dependency snapshot),
  `docs/audit/ROUTE_SENSITIVITY_MATRIX.md` (surface), `constitution/invariants.yaml`
  (enforcement graph).

## 6. State

- **To be built:** a persisted, versioned Self Model (graphs) with a currency guarantee.
- **Partial seeds today:** `BUILD_LEDGER.yaml`, `CIVILIZATION_BUILD_LEDGER.yaml`,
  reachability snapshots, the route sensitivity matrix, `schema_migrations` (evolution
  lineage), the constitution invariant registry (an enforcement graph over the code).

## 7. Failure modes and responses

- **Structure known only to humans** — today the architecture lives in code and prose; no
  queryable model lets the system reason about its own shape (V18-INV-003 planned) — the
  core gap.
- **Stale model** — the hardest failure: a model that drifts from reality is worse than
  none. The design binds currency to V17's `--check` discipline (V18-INV-007 planned).
- **Memory/structure conflation** — the pre-split Self Model mixed history and structure;
  keeping them separate (V18-INV-009) is why V34 exists.
- **Change without a map** — Structural/Autonomous Evolution (V19/V16) need the model to
  make safe changes; without it, self-modification is blind (V18-INV-008 planned).

## 8. Verification obligations

Existing and green today: the partial seeds are themselves inspected — reachability
generation runs, and the ledger drives the generated status (V17).

Must exist to satisfy the volume: a persisted Self Model with a currency `--check`
(V18-INV-007), graph representations for architecture/dependency/institution/capability/
topology/evolution/health (V18-INV-003..006), and a query API (V18-INV-008).

## 9. Implementation mapping

- **Partial seeds (enforced fragments):** `BUILD_LEDGER.yaml` /
  `CIVILIZATION_BUILD_LEDGER.yaml` (component inventory),
  `scripts/generate_runtime_reachability.py` (dependency snapshot).
- **Adjacent structural data:** `docs/audit/ROUTE_SENSITIVITY_MATRIX.md` (surface),
  `schema_migrations` (evolution lineage), `constitution/invariants.yaml` (enforcement
  graph), the institution/capability tables (V6/V15).
- **Not yet built:** the unified, queryable, current Self Model. No service today
  materializes the eight graphs as first-class data.

## 10. Open questions

1. **Build vs derive.** Is the Self Model a persisted store kept in sync, or a view
   derived on demand from the seeds (ledger + reachability + tables)? Derive-on-demand is
   cheaper and inherently current but slower to query; a materialized model is queryable
   but needs a currency guarantee (V18-INV-007).
2. **Currency is the hard part.** The value of the model is proportional to how current it
   is; the entire design hinges on binding it to Self Inspection's `--check` discipline.
3. **Overlap with the constitution.** This constitution is itself a partial self model
   (an enforcement graph over the code). The Self Model and the constitution should
   cross-reference — invariants name enforcement paths; the dependency graph names the
   same files — rather than duplicate.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written (prescriptive; split from Memory per GENERALIZATION_REPORT §7). | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 21) | Design the structure-now Self Model as a buildable set of graphs, separated from history (V34), and name the partial seeds (ledger, reachability) without claiming the model exists. |
