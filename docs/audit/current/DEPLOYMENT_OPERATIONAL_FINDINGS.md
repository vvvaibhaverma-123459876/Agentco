# Deployment Operational Findings

| ID | Severity | Component | Status | Impact |
| --- | --- | --- | --- | --- |
| DOP-001 | S2 | network-policy | validated_by_staging_audit | deny rules may render but not isolate traffic |
| RTI-002 | S3 | event topology | intentional_separation | operator confusion if not documented |
| DOP-002 | S3 | local Kafka-compatible broker | accepted_local_real_boundary | local-real evidence proves Kafka protocol integration, not vendor-specific Kafka packaging |
