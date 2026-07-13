# Remediation 04 Deployment Operational Resilience

Scope: deployment topology, local Kubernetes staging, rollback, backup/restore, observability alerts, RBAC/security checks, and RTI-002 event-topology resolution.

RTI-002 decision: intentional separation. `event_outbox` is the event-log transactional outbox; `event_bus_outbox` is the signed EventBus domain outbox. `OutboxWorker` is the shared relay process and drains both contracts with separate schemas and dead-letter tables.

Final commit SHA: recorded in EXECUTION_LEDGER.json for runtime evidence
