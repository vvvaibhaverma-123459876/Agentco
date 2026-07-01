# Real-World Proof Plan

AgentCo cannot prove long-horizon generality, durable autonomous improvement,
broad open-domain transfer, or hosted production operations by adding code alone.
Those claims become true only after repeated real operation produces auditable
evidence. The repo now treats that evidence as a gate in
`scripts/verify_mission_progress.py`.

## 1. Long-Horizon Generality

Run at least 10 successful real-world mission runs across at least 30 calendar
days. Each counted run must keep safety gates green and record held-out domain
coverage. The claim only upgrades when the longitudinal registry shows an
improving aggregate trend and at least 12 held-out domains have been covered.

Required record fields:

- `real_world: true`
- `success: true`
- `safety_gates_green: true`
- `held_out_domain_count >= 12` over the registry window
- `aggregate_score` improving over time

Command path:

```bash
make live-cross-domain
make memory-influence-live
make release-gates
make mission-progress-record-real-world
```

## 2. Durable Autonomous Improvement

Run at least 3 real-world improvement cycles where a prior lesson, skill, or
candidate measurably improves later performance. Each cycle must include a
before/after delta, promotion proof, canary or rollback result, event-log
lineage, and green safety gates.

Required record fields:

- `improvement_cycle: true`
- `before_after_delta > 0`
- `promotion_proof: true`
- `canary_or_rollback_passed: true`
- `event_log_lineage: true`
- `safety_gates_green: true`

## 3. Broad Open-Domain Transfer

The existing bounded verifier is not enough. Build or run a live held-out suite
where task schemas are selected after the verifier is written, span at least 12
domains, use independent evidence sources, and are independently adjudicated.
Only then remove the bounded-verifier limitation from the generated report.

Required report fields:

- `success: true`
- `simulated: false`
- `not_proof_of_general_intelligence: false`
- `held_out_task_schemas: true`
- `independent_adjudication: true`
- `domains` length at least 12

## 4. Hosted Production Operations

Local Docker production posture is not hosted production certification. A hosted
or production-equivalent environment must record deployment identity, release
artifact, SLO dashboards, alert routing, backup/restore, DR runbook, incident
response, and production-equivalent smoke/load/security gates.

Required report fields under `hosted_ops_evidence`:

- `slo_dashboard_verified: true`
- `alert_routing_verified: true`
- `backup_restore_verified: true`
- `dr_runbook_verified: true`
- `incident_response_verified: true`
- `production_equivalent_gates_passed: true`

## Current Rule

Until those records exist, `make mission-progress` must keep the corresponding
claims as `partial` or `unproven`. That is intentional: the system should earn
the claim through evidence, not documentation language.
