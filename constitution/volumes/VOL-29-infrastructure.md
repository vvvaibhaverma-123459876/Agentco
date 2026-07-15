# Volume 29 — Infrastructure

## 1. Header

| Field | Value |
|---|---|
| Volume | 29 |
| Name | Infrastructure |
| Tier | regulation |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V3 (Runtime Operating System), V2 (Civilization Kernel), V30 (Verification), V32 (Security), V28 (Operator Experience) |

## 2. Purpose

Infrastructure is where the civilization physically runs: the container stack for local
development, the Helm chart for Kubernetes deployment, the workers, and the observability
plumbing. As a **regulation-tier** volume it is the most freely changeable layer — but two
properties are load-bearing and cited: migrations run as a gated job before the app serves,
and the workloads carry health probes so an unhealthy instance is not sent traffic. Mixed
status; every present-tense claim cites its file.

```text
LOCAL STACK  docker-compose.yml
   postgres · redis · kafka · vault · prometheus · grafana · otel
   ▼
DEPLOY  infrastructure/kubernetes/helm/agentco/
   ├─ migration-job.yaml   runs db:migrate BEFORE serving (V2 bootstrap)
   ├─ deployment.yaml      backend + liveness/readiness probes → /health
   ├─ frontend-deployment.yaml
   ├─ outbox-worker-deployment.yaml       (V3 relay)
   ├─ civilization-scheduler-deployment.yaml  (V3 leader-elected tick)
   ├─ hpa.yaml             autoscaling (cpu/mem)
   ├─ pdb.yaml             disruption budget
   └─ services.yaml · ingress.yaml · serviceaccount.yaml
   ▼
OBSERVABILITY  prometheus + grafana + otel   /metrics (prom-client)
```

## 3. Definitions

- **Local stack** — the docker-compose environment for development
  (`docker-compose.yml`; staging `docker-compose.staging.yml`).
- **Helm chart** — the Kubernetes deployment template
  (`infrastructure/kubernetes/helm/agentco/`).
- **Migration job** — the pre-serve job that applies migrations
  (`migration-job.yaml` running `db:migrate`; V2).
- **Health probes** — liveness/readiness checks against `/health`
  (`deployment.yaml`; `backend/src/server.ts` `/health`).
- **Workers** — the outbox relay and civilization scheduler deployments (V3).
- **Autoscaling / disruption budget** — `hpa.yaml`, `pdb.yaml`.
- **Observability** — Prometheus/Grafana/OTel plumbing (`infrastructure/`), `/metrics`.

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V29-INV-001 | Migrations run as a dedicated job before the application serves traffic, so no instance serves against an un-migrated schema. | enforced | `infrastructure/kubernetes/helm/agentco/templates/migration-job.yaml`, `backend/tests/helm-deployment-contract.test.ts` |
| V29-INV-002 | Backend and frontend workloads declare liveness and readiness probes, so an unhealthy instance is not sent traffic. | enforced | `infrastructure/kubernetes/helm/agentco/templates/deployment.yaml`, `backend/src/server.ts` |
| V29-INV-003 | The outbox relay and civilization scheduler run as their own deployments, matching the runtime OS worker model. | enforced | `infrastructure/kubernetes/helm/agentco/templates/outbox-worker-deployment.yaml`, `infrastructure/kubernetes/helm/agentco/templates/civilization-scheduler-deployment.yaml` |
| V29-INV-004 | The local stack provides the full dependency set (Postgres, Redis, Kafka, Vault, Prometheus, Grafana, OTel) so the system is runnable end to end locally. | enforced | `docker-compose.yml` |
| V29-INV-005 | The deployment exposes Prometheus metrics via the application `/metrics` endpoint. | enforced | `backend/src/server.ts`, `infrastructure/prometheus` |
| V29-INV-006 | Autoscaling and a pod disruption budget are defined so the backend scales and survives voluntary disruption. | enforced | `infrastructure/kubernetes/helm/agentco/templates/hpa.yaml`, `infrastructure/kubernetes/helm/agentco/templates/pdb.yaml` |
| V29-INV-007 | A Docker startup verification exists that boots the full stack and checks each dependency. | enforced | `scripts/verify_docker_startup.py`, `backend/tests/phase4-production-deployment.test.ts` |
| V29-INV-008 | Hosted production operation (continuous SLOs, DR, backups, incident response, long-running operational evidence) is certified against a live cluster. | planned | — |
| V29-INV-009 | Secrets are delivered from a managed secret store (Vault) in production rather than environment plaintext. | planned | — |

## 5. Interfaces

- **Local** — `docker-compose.yml`, `docker-compose.staging.yml`;
  `make docker-production-smoke`, `make docker-startup-verify`.
- **Deploy** — the Helm chart (`infrastructure/kubernetes/helm/agentco/`) with
  `values.yaml` toggles for backend/frontend/workers/autoscaling.
- **Health** — `/health` (public), `/metrics` (Prometheus) in `backend/src/server.ts`.
- **Observability** — `infrastructure/prometheus`, `infrastructure/grafana`,
  `infrastructure/otel`.
- **Secrets** — `infrastructure/vault` (dev); production secret guards (V32).

## 6. State

- **Compose:** `docker-compose.yml`, `docker-compose.staging.yml`.
- **Helm:** `infrastructure/kubernetes/helm/agentco/` (templates + `values.yaml`).
- **Observability config:** `infrastructure/{prometheus,grafana,otel}`.
- **CI:** `staging-deployment-audit.yml`, `hosted-staging-audit.yml`, `deploy.yml`.

## 7. Failure modes and responses

- **Serving an un-migrated schema** — the migration job runs before the app serves
  (V29-INV-001), verified by the Helm deployment contract test.
- **Traffic to an unhealthy pod** — liveness/readiness probes gate traffic (V29-INV-002).
- **Lost events under load** — the outbox worker runs as its own deployment so relay
  keeps up independently of request handling (V29-INV-003; V3).
- **Not actually runnable** — the compose stack provides every dependency and a startup
  verifier boots and checks them (V29-INV-004, V29-INV-007).
- **Hosted production not certified** — the honest boundary: `README.md` and the
  completion reports state that continuous SLOs, DR, backups, and incident evidence
  require a live cluster and are **not** claimed (V29-INV-008 planned; open question 1).
- **Plaintext secrets in production** — Vault exists (dev) but production secret delivery
  from a managed store is not yet enforced (V29-INV-009 planned); today V32 startup guards
  reject dev-default secrets but do not mandate Vault.

## 8. Verification obligations

Existing and green today: `backend/tests/helm-deployment-contract.test.ts`,
`backend/tests/phase4-production-deployment.test.ts`, `scripts/verify_docker_startup.py`,
the staging-deployment-audit workflow.

Must exist before the planned invariants flip: live hosted-production certification
evidence (V29-INV-008), and a production secret-delivery-from-Vault contract
(V29-INV-009).

## 9. Implementation mapping

- `docker-compose.yml`, `docker-compose.staging.yml` — local/staging stacks.
- `infrastructure/kubernetes/helm/agentco/templates/` — migration-job, deployment
  (probes), frontend, outbox-worker, civilization-scheduler, hpa, pdb, services, ingress.
- `backend/src/server.ts` — `/health`, `/metrics`.
- `infrastructure/{prometheus,grafana,otel,vault}` — observability and secrets.
- `scripts/verify_docker_startup.py` — full-stack boot check.

## 10. Open questions

1. **Hosted production is not certified.** Every completion claim in this repo explicitly
   excludes hosted production (continuous SLOs, DR, backups, incident response). The
   deployment *contract* is production-grade; a live certification against a real cluster
   is out of the current environment's scope (V29-INV-008 planned) — this is the honest
   ceiling of the whole build.
2. **Secret delivery.** Vault is wired for dev; production should deliver secrets from a
   managed store rather than environment plaintext (V29-INV-009). V32 guards reject
   dev-defaults but do not mandate the source.
3. **Regulation tier means fast change.** As the freely-changeable layer, infrastructure
   should not accrete invariants that ossify deployment choices; the load-bearing ones
   (migrate-before-serve, health probes, worker isolation) are the ones worth binding, and
   the rest stays flexible.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 24) | Bind the runnable stack, the Helm deployment contract (migrate-before-serve, health probes, worker isolation, autoscaling), and observability into one citable infrastructure layer — while honestly marking hosted-production certification as the build's ceiling. |
