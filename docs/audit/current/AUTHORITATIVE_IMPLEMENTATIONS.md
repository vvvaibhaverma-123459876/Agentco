# Authoritative Implementations

Tracked structural snapshot input hash: `57b96c248c3ab254eef56abbf0e0881723336bedf1584e7d17a7f2edfe31cea9`

| Concept | Implementation | Decision | Evidence |
| --- | --- | --- | --- |
| Agents | Python BaseAgentV2 active agents and TS TeamActivation specialist spawner | authoritative | release gate, specialist spawn tests, runtime integration |
| V1 specialists | agents/autonomy SpecialistAgent subclasses | compatibility layer | live only through TS spawner; high/critical V1 governance remains blocked |
| Audit writers | Python DurableAuditWriter + TS audit/event log services | authoritative with cross-writer contract | decision_log chain tests and runtime outbox proof |
| Event publication | EventLogService transactional outbox | authoritative for transactional event_log outbox | make audit-runtime-integration |
| EventBus outbox | EventBusService event_bus_outbox | parallel active implementation | candidate for consolidation with event_log outbox |
| Learning | runtime/controlled_learning and runtime/self_improvement | authoritative bounded mechanisms | release gate report checks; no longitudinal mission proof |
| Standalone learning/ synthesis | learning/ and synthesis/ | experimental | tests only; no backend deployment startup wiring observed |

Consolidation recommendation: keep the event-log transactional outbox as the authoritative durable event path and either adapt or retire `event_bus_outbox` after a compatibility plan.
