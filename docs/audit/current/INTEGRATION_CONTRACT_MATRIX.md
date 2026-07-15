# Integration Contract Matrix

Tracked structural snapshot input hash `6b771fc38fb382b88877f86b65e3f71e580313204ce010a0aef62c6cb5f6ec6d`.

| producer | consumer | transport | status | runtime_test |
| --- | --- | --- | --- | --- |
| frontend | backend | HTTP | configured_unexecuted | frontend typecheck/build; no browser E2E in Batch 03 |
| backend | PostgreSQL | pg | verified_local_real | migrations + runtime integration |
| backend | Redis | ioredis | verified_local_real | runtime integration ping/set/get |
| event_log transaction | event_outbox | PostgreSQL transaction | verified_local_real | runtime integration |
| outbox worker | Kafka | KafkaJS | verified_local_real | runtime integration |
| Kafka | consumer | KafkaJS | verified_local_real | runtime integration consumer read |
| agent | tool registry | Python runtime | verified_local_real | release/clean-room agent tests |
| evaluation | learning proposal | Python runtime | integration_tested | release gate report checks |
