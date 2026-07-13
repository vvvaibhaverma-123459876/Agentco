# Integration Contract Matrix

Tracked structural snapshot input hash `d222041325198eaeeee5107a73ece1708a6c86c0631ce0d620e43218d78e091d`.

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
