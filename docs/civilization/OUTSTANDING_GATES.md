# Outstanding Gates — Honest Status of the C0–C15 Civilization Layer

The C0–C15 civilization layer is **implemented and verified against its own focused
test suites and a full backend jest regression** (117 suites / 873 tests green on an
isolated Postgres/Kafka/Redis stack, clean `tsc`, route-auth contract, dependency
audit + secret scan clean). That is real, durable work.

## Gate status (updated 2026-07-15 after the canonical gates were run)

1. **`make release-gate` — ✅ RUN GREEN against the built code (2026-07-15).**
   The repo's authoritative 12-step gate executed end-to-end on the isolated stack at
   `main` HEAD `b1470c0` with **exit 0**: clean tree, gate-integrity, advertised
   targets, status/conformance/calibration/learning/self-improvement/score-validation
   checks, backend install + migrations + least-privilege role grants, the Python
   default suite (776 passed), backend build, the full 873-test jest regression,
   route-auth contract, decision-log chain cross-writer test, frontend install +
   typecheck + build, and the clean-tree-after-gate check. Precondition fixed en route:
   the `docs/audit/current/*` runtime snapshots predated the civilization layer and were
   refreshed with verification (zero entrypoints lost, 132 → 287, all 155 additions are
   civilization modules; generator idempotent; no new adverse findings).
2. **Post-build reachability (`make audit-runtime-integration`) — ✅ GREEN in CI.**
   The Runtime Integration Audit workflow runs `make audit-runtime-integration` on every
   push to `main` and has passed repeatedly against the merged civilization code (e.g.
   runs 29387180128, 29388024926, 29388721599, and the fully-green run set on commit
   `b1470c0`, 2026-07-15). The Clean-Room Audit and CI workflows are also green on
   `b1470c0` — the first fully green `main` since the civilization merge.
3. **B.2 anti-stub / no-simulation sweep — ✅ CLEAN over the full `backend/src` tree
   (2026-07-15).** The full-tree grep for deferral/stub markers (TODO/FIXME/HACK/XXX,
   "not implemented", "placeholder", "fake success", "simulated result") over all
   runtime `.ts` files found 4 hits, all benign: two documentation comments in
   `simulator.service.ts` *prohibiting* fake success, and two occurrences of the
   `placeholders` variable for SQL `$1,$2,…` parameters in
   `institution-governance.service.ts`. Zero genuine stub or deferral markers.

4. **Coordinator-driven reachability — ✅ IMPLEMENTED + tested (2026-07-16).** The C12 OS
   tick now runs a **LayerOrchestrator** that drives the previously-only-observed layers as
   real work inside the loop: coalition escalations targeting the judiciary become cases
   (`routeEscalationsToJudiciary`, idempotent via `source_dispute_id`); post-promotion
   monitored learning candidates are retained through the safe-evolution status machine
   after a window (`retireMonitoredCandidates`); active domains below their trust threshold
   are suspended (`domainRegistry.suspendBelowThreshold`); and claims standing on
   already-retracted provenance are weakened (`collectiveKnowledge.sweepDanglingProvenance`).
   Every step is idempotent and per-layer error-isolated, with counts in the tick's
   `status.orchestrated` projection. Proven by `backend/tests/civilization-os-orchestration.test.ts`
   (4 tests, each asserting a real effect **and** re-tick idempotence) plus the full
   civilization suite green.

## Remaining gap (why the predicate is still `false`)

- **Hosted production certification** (live SLO/DR/backup/incident evidence) is out of
  environment scope and is not claimed (this was always excluded, not a regression).
- **Predicate flip pending fresh reconciliation.** All four brief gates now have executable
  evidence, but `termination_predicate_met` is deliberately **not** flipped in the same
  breath as writing the orchestrator: the flip must be driven by a fresh `make release-gate`
  + `make civilization-completion` reconciliation against this new HEAD, not asserted. That
  re-run is the next step; until it is green the predicate stays `false`.

## Disposition

This document exists so the ledger's honesty is not left to a self-authored
reconciliation script. All four brief gates are now closed with executable evidence
(release-gate log, CI run IDs, B.2 sweep, and the orchestration suite).
`termination_predicate_met` stays **false** by deliberate discipline: the flip is gated on
a fresh `make release-gate` + `make civilization-completion` run against this new HEAD — the
same discipline that produced the 2026-07-14 walk-back — not on this document's say-so.
