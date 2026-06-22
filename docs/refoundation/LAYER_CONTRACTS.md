# Layer Contracts

Status: **REAL** for Gates 0-2 contracts; later-layer contracts remain target contracts.

## Foundational Contracts

- Substrate Runtime: append-only audit records are hash-chained; migrations have one canonical path; events include producer, timestamp, confidence, risk, payload hash, and verification material.
- Evidence Kernel: claims are untrusted by default; evidence has provenance; resolutions are write-once; promotion requires independent evidence, contradiction checks, resolver rules, and firewall approval.
- Source Independence: source identity is canonicalized; same-source and derivative evidence cannot resolve the originating claim; every promotion has an independence score.
- Durable Execution: task state persists outside process memory; retries are idempotent; dispatch produces audit/event/result records; irreversible tools require sandbox attestation.
- Provenance: consequential actions produce signed `action_attestations`; external verification does not require trusting mutable application state.
- Uncertainty: action confidence uses trusted confidence, not raw stated confidence; high uncertainty triggers abstention or escalation.

## Core Contracts

- Memory: immutable experiential memory is append-only and points to provenance; mutable operational memory is separately scoped and supersedable.
- Learning: learning writes claims/evidence/memory and proposes adaptations; adaptations route through governance before activation.
- Ingestion: adapters never write trusted memory directly; extracted claims enter Evidence Kernel as untrusted with provenance.

## Organizational Contracts

- Agents and skills: task routing is capability and trust weighted; activation/demotion are governed.
- Governance: policy gates are mechanical; high/critical risk cannot silently auto-approve; protected surfaces are denied by default.
- Institutions and societies: organizational objects govern real agents and workflows, not static labels.

## Advanced Contracts

- Simulation: simulation outputs stay quarantined; only external validation can promote related claims.
- Self-modification: changes are pre-registered, sandboxed, evaluated, reversible, and audit logged.
- Model Foundry: training examples preserve lineage from task, claim, evidence, action, outcome, calibration update, and approval.
