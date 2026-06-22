# Build Plan

Current open gate: **none; Gates 0-17 complete for implemented repo scope**.

The build proceeds in dependency-gated order. A phase is not done until its tests are wired into CI.

| Phase | Gate | Status |
|---|---|---|
| 0 Audit, truth reset, stabilization | Fresh clone bootstraps via `make dev` + `make smoke`; README states one promise; no product surface claims North Star capabilities; write actions receive API key | **REAL** |
| 1 Canonical architecture and contracts | Every current module mapped; schema migrates up/down; foundational contracts defined | **REAL** |
| 2 Evidence Kernel + source independence | Same-source and derivative resolution mechanically impossible; simulation/fixture evidence cannot promote | **REAL** |
| 3 Durable execution | Real task survives restart and is RBAC gated; no placeholder dispatch output | **REAL** |
| 4 Provenance & attestation | External verifier validates action provenance; tamper tests fail closed | **REAL** |
| 5 Uncertainty stack | Brier/log/ECE/coverage on real resolved claims; abstention gates action | **REAL** |
| 6 Memory Kernel | Persistent memory read/write changes later behavior; immutable/mutable split enforced | **REAL** |
| 7 Universal ingestion | Text/web/code ingestion emits untrusted claims with provenance | **REAL** |
| 8 Learning loop | Observe-to-govern loop writes durable memory and governed adaptation proposal | **REAL** |
| 9 Agent/skill/task kernel | Trust-weighted routing, spawn proposal, demotion, policy-gated activation | **REAL** |
| 10 Governance DSL | Mechanical policy gates and protected-surface denial paths pass | **REAL** |
| 11 Institutions/societies | Persisted proposal lifecycle over real agents/institutions | **REAL** |
| 12 Simulation | Simulation quarantined; hypothesis promotes only after external validation | **REAL** |
| 13 Self-modification | Safe patch sandboxed/reversible; unsafe/protected changes blocked | **REAL** |
| 14 Model Foundry | Trace converts to dataset item with provenance and calibration weighting | **REAL** |
| 15 Validation suite | Single command runs external benchmark gates with evidence-quality labels | **REAL** |
| 16 Operator console | Operator can inspect why allowed/blocked with provenance/policy/evidence chain | **REAL** |
| 17 CI master gate | Breaking any Gate 0-16 invariant fails CI | **REAL** |
