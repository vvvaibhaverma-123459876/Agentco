# Actual Deployment Topology

Evidence target: local-real Kubernetes via Kind. Hosted production remains unverified.

## Release Sequence

1. build immutable images
1. create Kind cluster
1. deploy data services
1. run migration job with migration identity
1. grant runtime identity
1. deploy backend/outbox/frontend
1. verify readiness
1. exercise workflow
1. backup/restore
1. rolling update and rollback
1. failure injection
1. cleanup

## Hosted Boundary Classification

- managed_kubernetes: unverified
- managed_postgresql: unverified
- managed_redis: unverified
- managed_kafka: unverified
- cloud_backup_storage: unverified
- production_alert_destination: unverified
- live_llm_provider: unverified
