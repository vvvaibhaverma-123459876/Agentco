# Integration Contract Matrix

Tracked structural snapshot input hash `5fb6528e6b23795e8922ba9c6bde4510d949f64d0653b5b7a3c38d0863078978`.

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
