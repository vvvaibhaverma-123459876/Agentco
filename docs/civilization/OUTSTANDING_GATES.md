# Outstanding Gates — Honest Status of the C0–C15 Civilization Layer

The C0–C15 civilization layer is **implemented and verified against its own focused
test suites and a full backend jest regression** (117 suites / 873 tests green on an
isolated Postgres/Kafka/Redis stack, clean `tsc`, route-auth contract, dependency
audit + secret scan clean). That is real, durable work.

It is **not** "complete" under the brief's canonical release gates. `termination_predicate_met`
is therefore `false`. The gap, stated plainly (surfaced by adversarial review):

## Gates not yet run against the built code

1. **`make release-gate`** — the repo's authoritative 12-step gate (Python default suite,
   `npm run build`, score-validation, decision-log chain, `gate-integrity` which rejects
   fake-success patterns, route-auth contract, clean-tree assertions). The civilization
   jest suites + `tsc` are a *subset* of this. Not yet executed post-build.
2. **Post-build reachability (`make audit-runtime-integration`)** — the only reachability
   evidence on record is the **C0 baseline**, captured *before* the 15 new civilization
   services existed. It must be re-run so the coordinator-reachability claim reflects the
   built code.
3. **B.2 anti-stub / no-simulation grep** over the full `backend/src/` runtime tree — run
   only over the civilization service files so far (one `later` marker found and removed;
   a full-tree sweep is outstanding).

## Known scope limits (not defects, but not "complete")

- **Coordinator reachability is partial.** The C12 OS tick actively drives mission routing +
  emergency/reservation sweeps and *observes* every other layer in its status projection,
  but does not yet orchestrate judiciary/coalition/learning/expansion/knowledge as work
  inside the tick loop. The brief (A.6/B.8) makes full coordinator-driven reachability a
  release gate.
- **Hosted production certification** (live SLO/DR/backup/incident evidence) is out of
  environment scope and is not claimed.

## Disposition

This document exists so the ledger's honesty is not left to a self-authored reconciliation
script. The completion-evidence generator checks file/ledger presence; it does **not** run
the canonical gates above. Until those gates run green against the built code — and the
coordinator drives every registered service — the correct status is **"implemented; gates
outstanding," predicate `false`.**
