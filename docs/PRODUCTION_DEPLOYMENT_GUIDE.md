> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# Production Deployment Guide

**Version:** 1.0  
**Last Updated:** 2026-06-23  
**Status:** Ready for Staging/Production

---

## Overview

This guide covers deploying the AgentCo Civilization Trust Governance system to production. The system enforces 7 non-negotiable safety rules and requires strict configuration validation.

---

## Prerequisites

### Infrastructure Requirements

1. **PostgreSQL 14+** 
   - ≥2 CPU cores, ≥8GB RAM
   - TLS/SSL enabled
   - Automated backups configured
   - Read replicas recommended

2. **Apache Kafka 3.0+** (or cloud equivalent)
   - ≥3 brokers for production
   - TLS/SSL enabled
   - Topic replication factor ≥3
   - Retention: ≥7 days

3. **OpenTelemetry Collector** (for observability)
   - Compatible with Datadog, New Relic, or Grafana Tempo
   - TLS/SSL enabled

4. **Monitoring & Alerting**
   - Prometheus (or compatible metrics backend)
   - Grafana (or equivalent visualization)
   - Alert manager configured

5. **Secret Management**
   - HashiCorp Vault OR AWS Secrets Manager
   - AppRole or equivalent auth method
   - Rotation policy: ≤90 days

### Required Knowledge

- PostgreSQL administration
- Kubernetes or container orchestration
- TLS/SSL certificate management
- Secrets management systems
- Monitoring and observability tools

---

## Step 1: Prepare Environment

### 1.1 Generate Required Secrets

All secrets MUST be randomly generated, never reused, and stored in secure secret management:

```bash
# Generate API key (32 bytes hex)
openssl rand -hex 16 > /tmp/agentco_api_key.txt

# Generate JWT secret (32 bytes hex)
openssl rand -hex 16 > /tmp/jwt_secret.txt

# Generate service identity secret (32 bytes hex)
openssl rand -hex 16 > /tmp/service_identity_secret.txt

# Store in secret management system, NOT in .env files
# Example: AWS Secrets Manager
aws secretsmanager create-secret \
  --name agentco/prod/api-key \
  --secret-string "$(cat /tmp/agentco_api_key.txt)"
```

### 1.2 Verify Infrastructure

```bash
# Test PostgreSQL connection
psql -h postgres.example.com -U agentco -d agentco_prod -c "SELECT 1"

# Test Kafka connectivity
kafka-broker-api-versions.sh --bootstrap-server kafka1:9092

# Test OpenTelemetry endpoint
curl -X POST https://otel.example.com/v1/metrics/export \
  -H "Content-Type: application/protobuf"
```

### 1.3 Create Production Configuration

```bash
# Copy template and fill in real values
cp .env.production.example .env.production

# Edit with real values (use secret management for actual secrets)
# DO NOT commit .env.production to git
# Add to .gitignore if not already present
echo ".env.production" >> .gitignore
```

---

## Step 2: Build & Package

### 2.1 Build Backend

```bash
cd backend
npm install --production  # Production dependencies only
npm run build             # TypeScript compilation
```

**Validation:**
```bash
# Verify build output
ls -la dist/server.js
# Should be ≥100KB (not empty/corrupted)

# Check for errors
npm run build 2>&1 | grep -i "error"
# Should output nothing
```

### 2.2 Build Docker Image

```bash
docker build \
  -t agentco/backend:latest \
  -t agentco/backend:$(date +%Y%m%d-%H%M%S) \
  -f Dockerfile \
  .
```

### 2.3 Push to Registry

```bash
docker push agentco/backend:latest
docker push agentco/backend:$(date +%Y%m%d-%H%M%S)
```

---

## Step 3: Initialize Database

### 3.1 Run Migrations

```bash
# Run all pending migrations
python3 backend/src/db/run_migrations.py

# Verify migrations applied
psql -h postgres.example.com -U agentco -d agentco_prod \
  -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 5"
```

**Expected output:**
```
 version
---------
     019
     018
     017
     016
     015
(5 rows)
```

### 3.2 Verify Schema

```bash
# Check that critical tables exist
psql -h postgres.example.com -U agentco -d agentco_prod \
  -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename" | wc -l
# Should be 50+ tables

# Check that triggers exist
psql -h postgres.example.com -U agentco -d agentco_prod \
  -c "SELECT COUNT(*) FROM pg_trigger" 
# Should be 15+ immutability triggers
```

---

## Step 4: Deploy Backend

### 4.1 Kubernetes Deployment

```bash
# Apply manifests
kubectl apply -f infrastructure/kubernetes/namespace.yaml
kubectl apply -f infrastructure/kubernetes/configmap.yaml
kubectl apply -f infrastructure/kubernetes/secret.yaml
kubectl apply -f infrastructure/kubernetes/deployment.yaml
kubectl apply -f infrastructure/kubernetes/service.yaml

# Verify deployment
kubectl get deployments -n agentco-prod
kubectl get pods -n agentco-prod
```

### 4.2 Container Orchestration Alternative (Docker Compose)

```bash
docker-compose -f docker-compose.production.yml up -d
docker-compose logs backend
```

### 4.3 Verify Startup

```bash
# Wait for startup (30-60 seconds)
sleep 30

# Check health endpoint
curl -X GET http://localhost:3001/health

# Expected response:
# {"status":"ok","timestamp":"2026-06-23T10:00:00Z"}
```

---

## Step 5: Production Validation

### 5.1 Run Security Gate

```bash
# Verify RBAC enforcement
curl -X POST http://localhost:3001/api/governance/bootstrap \
  -H "x-actor-id: unauthorized_user"
# Should return 403 Forbidden

# Verify API key requirement
curl -X POST http://localhost:3001/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name":"test"}'
# Should return 401 Unauthorized
```

### 5.2 Run Smoke Test

```bash
# Create production test
python3 scripts/test_production_smoke.py

# Expected output:
# ✓ Database connectivity: PASS
# ✓ Kafka connectivity: PASS  
# ✓ API authentication: PASS
# ✓ RBAC enforcement: PASS
# ✓ Governance gates: PASS
# RESULT: 5/5 PASS
```

### 5.3 Run Load Test

```bash
# Concurrent requests test
ab -n 100 -c 10 http://localhost:3001/health

# Should complete without errors
# Keep-Alive enabled
# Response time < 500ms
```

---

## Step 6: Configure Observability

### 6.1 OpenTelemetry Setup

```bash
# Deploy OTel collector
kubectl apply -f infrastructure/otel/otel-collector.yaml

# Verify traces are flowing
# Check Datadog/Grafana for incoming traces
```

### 6.2 Configure Prometheus

```bash
# Update Prometheus config
kubectl apply -f infrastructure/prometheus/prometheus.yml

# Test metrics endpoint
curl http://localhost:9090/metrics | grep agentco_
# Should return metrics
```

### 6.3 Configure Grafana

```bash
# Import dashboards
kubectl apply -f infrastructure/grafana/dashboards/

# Verify dashboards are visible in Grafana UI
# http://grafana.example.com/d/agentco-overview
```

### 6.4 Configure Alerts

```bash
# Deploy alert rules
kubectl apply -f infrastructure/alerts/agentco-alert-rules.yml

# Verify rules are loaded
curl http://localhost:9093/api/v1/rules
```

---

## Step 7: Production Readiness Checks

### 7.1 Run Full Production Gate

```bash
make production-release-gate

# Expected output:
# ✓ Backend build successful
# ✓ Security tests passed
# ✓ Governance gates enforced
# ✓ Protected surfaces enforced
# ✓ Smoke test passed
# ✓ Load test passed
# ✓ Observability configured
# VERDICT: PRODUCTION_READY
```

### 7.2 Final Validation Checklist

- [ ] All 7 non-negotiable safety rules are enforced
- [ ] Production secrets are NOT in version control
- [ ] TLS/SSL is enabled on all connections
- [ ] Database backups are automated
- [ ] Observability is flowing to monitoring system
- [ ] Alert rules are loaded
- [ ] Incident response runbook is available to team
- [ ] Disaster recovery procedures have been tested

---

## Step 8: Launch

### 8.1 Traffic Cutover

```bash
# Route traffic to new deployment
# For Kubernetes:
kubectl patch service agentco-backend \
  -n agentco-prod \
  -p '{"spec":{"selector":{"app":"agentco-backend","version":"prod"}}}'

# Monitor error rates
kubectl logs -f deployment/agentco-backend -n agentco-prod

# Watch metrics
# http://grafana.example.com/d/agentco-overview
```

### 8.2 Monitor First Hour

- Watch error rates (should be < 0.1%)
- Watch response times (p95 < 500ms)
- Watch database connections (should be < max_connections/2)
- Watch Kafka lag (should be < 100ms)

---

## Rollback Procedure

If critical issues emerge:

```bash
# Quick rollback to previous version
kubectl set image deployment/agentco-backend \
  backend=agentco/backend:PREVIOUS_VERSION \
  -n agentco-prod

# Verify rollback
kubectl get deployment agentco-backend -n agentco-prod
kubectl logs -f deployment/agentco-backend -n agentco-prod
```

---

## Emergency Procedures

### Emergency Shutdown

If a critical safety violation is detected:

```bash
# Activate emergency shutdown
curl -X POST http://localhost:3001/api/governance/emergency-shutdown \
  -H "x-actor-id: system_admin" \
  -H "x-api-key: $API_KEY"
```

### Emergency Trust Freeze

If trust policy system is compromised:

```bash
# Freeze all trust policy changes
curl -X POST http://localhost:3001/api/governance/emergency-freeze \
  -H "x-actor-id: system_admin" \
  -H "x-api-key: $API_KEY" \
  -d '{"action":"activate","reason":"trust_policy_compromise"}'
```

---

## Disaster Recovery

### Database Restore from Backup

```bash
# List available backups
aws s3 ls s3://agentco-prod-backups-encrypted/

# Restore to point-in-time
pg_restore \
  -h postgres.example.com \
  -U agentco \
  -d agentco_prod_recovery \
  s3://agentco-prod-backups-encrypted/backup-2026-06-23-10-00.sql

# Verify restore
psql -h postgres.example.com -U agentco -d agentco_prod_recovery \
  -c "SELECT COUNT(*) FROM autonomy_goals"
```

### Service Recovery

```bash
# Scale deployment to 0
kubectl scale deployment agentco-backend --replicas=0 -n agentco-prod

# Clear corrupted state if needed
kubectl delete deployment agentco-backend -n agentco-prod

# Redeploy
kubectl apply -f infrastructure/kubernetes/deployment.yaml
```

---

## Support & Escalation

**For production issues:**

1. **Page on-call:** Alert system will page automatically
2. **Check incident response runbook:** `docs/INCIDENT_RESPONSE_RUNBOOK.md`
3. **Review governance gates:** All changes must pass safety checks
4. **Escalate if needed:** Contact security team for policy violations

---

## Monitoring Commands

```bash
# Check all pods
kubectl get pods -n agentco-prod

# Stream logs
kubectl logs -f deployment/agentco-backend -n agentco-prod

# Check database connections
psql -h postgres.example.com -U agentco -d agentco_prod \
  -c "SELECT count(*) FROM pg_stat_activity"

# Monitor Kafka lag
kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group agentco \
  --describe
```

---

## Success Criteria

Production deployment is successful when:

1. ✅ All pods are running (replica count = desired count)
2. ✅ Health checks pass (5/5)
3. ✅ No error spikes in monitoring
4. ✅ API response times are < 500ms p95
5. ✅ Governance gates are enforcing all 7 safety rules
6. ✅ Protected surfaces are blocking mutations
7. ✅ Observability is flowing to monitoring systems
8. ✅ No unresolved security alerts

---

**Document Revision:** 1.0  
**Last Validated:** 2026-06-23  
**Next Review:** 2026-07-23
