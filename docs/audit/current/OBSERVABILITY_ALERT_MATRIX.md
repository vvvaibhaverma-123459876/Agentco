# Observability Alert Matrix

| Alert | Signal | Delivery |
| --- | --- | --- |
| backend unavailable | readiness failure | local alert receiver |
| outbox backlog | pending/dead-letter query | local alert receiver |
| dead-letter event | event_outbox dead_lettered | local alert receiver |
| Kafka publication failure | forced worker publish failure | local alert receiver |
| migration failure | failed migration job | local alert receiver |
| backup failure | backup command nonzero | local alert receiver |
