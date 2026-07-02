# Historical Documents — Not Current Truth

Everything in this directory is a **historical artifact**: superseded status
reports, phase-completion claims, old test-run summaries, and committed run
outputs that used to live at the repository root.

These documents describe what the project believed at some past moment. They
are **not** verified claims about the current system. Many of them assert
"COMPLETE", "FINAL", or "PRODUCTION READY" states that later adversarial
audits found to be partial or superseded.

The only sources of truth for current implementation status are:

- `BUILD_LEDGER.yaml` (checked by `python3.13 scripts/build_ledger.py status`)
- `docs/CURRENT_IMPLEMENTATION_REALITY.md`
- `docs/CURRENT_RUNTIME_CANONICAL.md`
- Reports generated under `reports/system_run/latest/` by reproducible
  commands (`make verify-clean-room`, `make mission-progress`, score
  validation).

If a claim in this directory conflicts with those sources, the claim here is
wrong.
