# Civilization Constitution Demo

Deterministic offline demo for the calibration-first Agentco civilization architecture.

Run:

```bash
make demo
```

The demo exports:

- `artifacts/audit_package.json`
- `artifacts/demo_trace.md`

It does not call paid external LLM APIs and does not require Kafka, Vault, Prometheus, Grafana, Pinecone, or any hosted service.
