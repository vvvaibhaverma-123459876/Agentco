# Volume 17 — Self Inspection

## 1. Header

| Field | Value |
|---|---|
| Volume | 17 |
| Name | Self Inspection |
| Tier | statute |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V18 (Civilization Self Model), V30 (Verification), V0 (Vision), V19 (Structural Evolution Framework), V16 (Autonomous Evolution) |

## 2. Purpose

Self Inspection is how AgentCo looks at itself and tells the truth: it inspects its
runtime, source, architecture, docs, deployment, tests, CI, and ledger, and produces a
grounded picture of what exists, what is reachable, and where documentation has drifted
from code. Its defining property is that inspection outputs are **machine-generated from
the artifacts themselves and re-checkable in CI** — so a status claim cannot silently
diverge from reality. This is the volume that exists because the repo's docs *have* drifted
before (V0 open question 1). Mixed status; every present-tense claim cites its file.

```text
ARTIFACTS                          INSPECTORS (machine-generated, re-checkable)
   ledger (BUILD_LEDGER.yaml) ───► generate_status.py --check   → README status block
   source + routes ─────────────► generate_runtime_reachability.py → reachability snapshot
   tracked files ───────────────► generate_forensic_inventory.py --check
   gate machinery ──────────────► verify_gate_integrity.py --check
   runtime health ──────────────► runtime/orchestration/doctor.py (modes)
   integration ─────────────────► audit_clean_room / audit_runtime_integration.py
   civilization ledger ─────────► generate_civilization_completion.py (predicate)
   constitution ────────────────► scripts/constitution/check_constitution.py
                                     │
                                     ▼
                        PRODUCES: status, reachability, drift, gaps
                        (partial: gaps are surfaced, not yet a governed backlog)
```

## 3. Definitions

- **Inspector** — a script that reads an artifact and emits a re-checkable report
  (the `generate_*`/`audit_*`/`verify_*` scripts and the constitution checker).
- **Status block** — the README implementation-status region generated from the ledger,
  marked "do not edit" (`scripts/generate_status.py`).
- **Reachability snapshot** — a conservative static record of which entry points reach
  which services (`scripts/generate_runtime_reachability.py`).
- **Forensic inventory** — a tracked-file census used for audit
  (`scripts/generate_forensic_inventory.py`,
  `docs/audit/FORENSIC_FILE_INVENTORY.md`).
- **Doctor** — the runtime health check with modes
  (`runtime/orchestration/doctor.py`).
- **Drift** — a divergence between a doc/claim and the code; the thing inspection exists
  to catch.
- **`--check` mode** — the CI-time assertion that a generated artifact is current, failing
  the build if regeneration would change it.

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V17-INV-001 | The README implementation-status block is generated from the ledger and is re-checkable, not hand-edited. | enforced | `scripts/generate_status.py`, `README.md` (STATUS:BEGIN/END markers) |
| V17-INV-002 | A tracked-file forensic inventory is generated and re-checkable in CI. | enforced | `scripts/generate_forensic_inventory.py`, `docs/audit/FORENSIC_FILE_INVENTORY.json` |
| V17-INV-003 | Gate integrity is inspected and fails closed on fake-success or bypass patterns. | enforced | `scripts/verify_gate_integrity.py` |
| V17-INV-004 | Static runtime reachability is generated conservatively so unreachable or newly-added services are visible. | enforced | `scripts/generate_runtime_reachability.py` |
| V17-INV-005 | Runtime health is inspectable via a doctor with explicit modes (offline, local-native, production). | enforced | `runtime/orchestration/doctor.py` |
| V17-INV-006 | Integration is audited in a clean room and against the running runtime, producing evidence artifacts. | enforced | `scripts/audit_clean_room.py`, `scripts/audit_runtime_integration.py` |
| V17-INV-007 | The constitution itself is inspected for drift on every push (headers, enforcement paths, domain neutrality). | enforced | `scripts/constitution/check_constitution.py`, `.github/workflows/constitution.yml` |
| V17-INV-008 | Inspection findings (capability gaps, incomplete systems, drift) are emitted as a structured, governed backlog rather than prose reports. | planned | — |
| V17-INV-009 | Every generated inspection artifact is enforced current by a `--check` gate in CI, so no inspector output can go stale unnoticed. | planned | — |

## 5. Interfaces

- **Status** — `scripts/generate_status.py` (`--check`), reading `BUILD_LEDGER.yaml`.
- **Reachability** — `scripts/generate_runtime_reachability.py`.
- **Inventory / controls** — `scripts/generate_forensic_inventory.py` (`--check`),
  `scripts/generate_forensic_audit_controls.py` (`--check`).
- **Gate integrity** — `scripts/verify_gate_integrity.py` (`--check`).
- **Audits** — `scripts/audit_clean_room.py`, `scripts/audit_runtime_integration.py`,
  `scripts/audit_staging_deployment.py`, `scripts/agentco_integration_audit.py`.
- **Doctor** — `runtime/orchestration/doctor.py`.
- **Completion** — `scripts/generate_civilization_completion.py` (predicate).
- **Constitution** — `scripts/constitution/check_constitution.py`.
- **Make** — `status`, `status-check`, `gate-integrity`, `audit-clean-room`,
  `audit-runtime-integration` targets.

## 6. State

- **Source artifacts:** `BUILD_LEDGER.yaml`, `CIVILIZATION_BUILD_LEDGER.yaml`, source
  tree, routes, migrations, `.github/workflows/`.
- **Generated reports:** README status block, `docs/audit/FORENSIC_FILE_INVENTORY.*`,
  `docs/audit/FORENSIC_AUDIT_CONTROLS.*`, `reports/system_run/latest/`,
  `reports/civilization_completion/latest/`, reachability snapshots.
- **Historical:** `docs/CURRENT_IMPLEMENTATION_REALITY.md` (marked HISTORICAL),
  `AGENTCO_REPO_AUDIT.md`.

## 7. Failure modes and responses

- **Doc/code drift** — the very failure this volume addresses: generated status
  (V17-INV-001), forensic inventory (V17-INV-002), and the constitution checker
  (V17-INV-007) all regenerate-and-compare, so a stale claim fails CI. (This is how the
  stale forensic inventory that broke `main`'s CI on 2026-07-15 was caught and fixed.)
- **Fake success** — `verify_gate_integrity.py` fails closed on echo-only or
  force-exit gate patterns (V17-INV-003) — it flagged this build's own `--forceExit`
  targets.
- **Hidden unreachable code** — conservative static reachability surfaces services not
  wired to an entry point (V17-INV-004).
- **Findings that go nowhere** — the gap: inspection produces reports, but capability
  gaps and drift are not yet a structured governed backlog that feeds V16/V19
  (V17-INV-008 planned; open question 1).
- **Stale inspectors** — not every generated artifact has a wired `--check` gate
  (V17-INV-009 planned; the reachability snapshot and some reports are generated but not
  all CI-enforced current).

## 8. Verification obligations

Existing and green today: `scripts/constitution/check_constitution.py` (CI),
`generate_status.py --check`, `generate_forensic_inventory.py --check`,
`verify_gate_integrity.py --check`, the clean-room and runtime-integration audits (CI
workflows).

Must exist before the planned invariants flip: a structured findings backlog emitted by
the inspectors and consumed by autonomous improvement (V17-INV-008), and a `--check`
gate for every generated inspection artifact (V17-INV-009).

## 9. Implementation mapping

- `scripts/generate_status.py` — ledger → README status (V17-INV-001).
- `scripts/generate_runtime_reachability.py` — static reachability (V17-INV-004).
- `scripts/generate_forensic_inventory.py`,
  `scripts/generate_forensic_audit_controls.py` — file/controls census (V17-INV-002).
- `scripts/verify_gate_integrity.py` — gate/bypass inspection (V17-INV-003).
- `runtime/orchestration/doctor.py` — runtime health modes (V17-INV-005).
- `scripts/audit_clean_room.py`, `scripts/audit_runtime_integration.py` — integration
  audits (V17-INV-006).
- `scripts/constitution/check_constitution.py` — constitution drift (V17-INV-007).
- `scripts/generate_civilization_completion.py` — civilization completion predicate.

## 10. Open questions

1. **Findings are prose, not a backlog.** The inspectors emit reports, but capability
   gaps, incomplete systems, and drift are not yet a structured, governed backlog that
   Autonomous Evolution (V16) and Structural Evolution (V19) can consume (V17-INV-008).
   This is the missing link that would turn self-inspection into self-improvement.
2. **Not every inspector is `--check`-gated.** Some artifacts (reachability snapshots,
   certain reports) are generated but not CI-enforced-current, so they can drift
   (V17-INV-009). The pre-existing `main` CI failures (V0 open question 4) are exactly
   this class.
3. **Self Model dependency.** Rich inspection needs a Self Model (V18) — an explicit
   architecture/dependency/capability graph — to inspect *against*; today inspection is
   artifact-by-artifact rather than graph-aware.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 20) | Bind the generate/audit/verify inspectors and the constitution checker into one citable self-inspection layer — the anti-drift machinery — and name the missing findings-to-backlog link that would make inspection feed improvement. |
