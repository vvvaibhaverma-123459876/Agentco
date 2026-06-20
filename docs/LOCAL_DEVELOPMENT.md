# Local Development

Use offline checks first:

```bash
make doctor
make smoke
make demo
```

Start minimal local services:

```bash
make dev-minimal
```

The minimal profile starts PostgreSQL only. It does not require Kafka, Vault, Prometheus, Grafana, Pinecone, or paid LLM keys.

Full local stack:

```bash
make dev-full
```

Run tests:

```bash
make test
```

Use `make smoke-real` only when intentionally testing a live/local LLM provider and service integrations.
