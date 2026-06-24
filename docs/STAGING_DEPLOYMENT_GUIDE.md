# Staging Deployment Guide

**Date:** 2026-06-23  
**Environment:** Staging (Production-like, isolated from real-world effects)  
**Audience:** DevOps, SRE, Infrastructure Team  
**Last Updated:** 2026-06-23

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Infrastructure Requirements](#infrastructure-requirements)
4. [Secrets Management](#secrets-management)
5. [Environment Configuration](#environment-configuration)
6. [Database Setup](#database-setup)
7. [Building the Backend](#building-the-backend)
8. [Deploying to Staging](#deploying-to-staging)
9. [Smoke Tests](#smoke-tests)
10. [Security Gates](#security-gates)
11. [Load Testing](#load-testing)
12. [Disaster Recovery](#disaster-recovery)
13. [Rollback Procedures](#rollback-procedures)
14. [Emergency Procedures](#emergency-procedures)
15. [Observability Setup](#observability-setup)
16. [48-Hour Burn-In Checklist](#48-hour-burn-in-checklist)
17. [Production Promotion Criteria](#production-promotion-criteria)
18. [Conditions That Block Production](#conditions-that-block-production)
19. [Runbook: Incident Response](#runbook-incident-response)
20. [Support & Escalation](#support--escalation)

---

## Overview

This guide walks through a complete staging deployment of AgentCo Civilization Trust Governance. Staging is a **production-like environment** that is **isolated from real-world effects** to allow thorough testing before production deployment.

### Key Characteristics

- **Production-Grade:** Uses same code, configuration patterns, and infrastructure stack as production
- **Safety Isolated:** Cannot affect real external systems (APIs, user data, etc.)
- **Test Enabled:** Allows load testing, chaos testing, and disaster recovery testing
- **Rollback Ready:** All procedures are reversible and testable
- **Observable:** Prometheus, Grafana, and OpenTelemetry for complete visibility

### Success Criteria

✅ All infrastructure components healthy  
✅ Database migrations apply cleanly  
✅ Backend starts without errors  
✅ Smoke tests pass  
✅ Security gates pass (7 non-negotiable rules verified)  
✅ Load test completes  
✅ Disaster recovery procedures tested  
✅ 48-hour burn-in stable  

---

## Prerequisites

### Team Requirements
- **DevOps Lead:** Responsible for infrastructure provisioning
- **SRE:** Responsible for monitoring and incident response
- **Database Admin:** Responsible for migration and backup procedures
- **Security Team:** Verifies security gates pass

### Knowledge Requirements
- Docker and Docker Compose
- PostgreSQL 14+
- Kafka message queue concepts
- Linux/MacOS shell scripting
- Git version control

### Tools Required
- Docker Desktop or Docker Engine 20.10+
- Docker Compose 2.0+
- PostgreSQL client tools (psql)
- Python 3.9+
- Node.js 18+ with npm
- curl or wget for HTTP testing

### Time Estimate
- Setup: 30-45 minutes
- Testing: 60-90 minutes
- 48-hour burn-in: Automated (manual monitoring 2-3 hours/day)
- Total before production: 50+ hours (most automated)

---

## Infrastructure Requirements

### Minimum Hardware (Single Machine)

```
CPU:    4 cores minimum (8+ recommended)
RAM:    8 GB minimum (16 GB recommended)
Disk:   50 GB SSD (100 GB for 48-hour burn-in data)
Network: Gigabit Ethernet (100 Mbps minimum)
```

### Infrastructure Stack

| Component | Version | Port | Purpose |
|-----------|---------|------|---------|
| PostgreSQL | 14+ | 5433 | Primary database |
| Redis | 7+ | 6380 | Cache and sessions |
| Kafka | 7.3+ | 9092/29092 | Event streaming |
| Zookeeper | 7.3+ | 22181 | Kafka coordination |
| OpenTelemetry | 0.68+ | 4318 | Observability |
| Prometheus | 2.40+ | 9090 | Metrics storage |
| Grafana | 9.2+ | 3050 | Visualization |

### Network Configuration

All services run on isolated Docker network `agentco-staging`:
- Services communicate via internal DNS (service name)
- External access via localhost:PORT mappings
- No internet access from containers (except for initial image pulls)

---

## Secrets Management

### Staging Secrets (NOT Real Production Secrets)

Staging secrets are **separate from production** and should be:
- ✅ Different from production secrets
- ✅ Stored in secure secret manager (Vault, AWS Secrets Manager, etc.)
- ✅ Rotated weekly
- ✅ Never committed to git

### Secret Generation

Generate all staging secrets using:

```bash
# API Key (32 bytes, hex)
openssl rand -hex 32

# JWT Secret (32 bytes, hex)
openssl rand -hex 32

# Service Identity Secret (32 bytes, hex)
openssl rand -hex 32

# Database Password (16+ characters)
openssl rand -base64 12
```

### Example Secrets (FOR TESTING ONLY - NEVER USE IN REAL STAGING)

```bash
# DO NOT USE THESE - They are examples only
AGENTCO_API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
JWT_SECRET=f7e6d5c4b3a2z9y8x7w6v5u4t3s2r1q0
API_KEY_SECRET=z1y2x3w4v5u6t7s8r9q0p1o2n3m4l5k6
SERVICE_IDENTITY_SECRET=q0p1o2n3m4l5k6j7i8h9g0f1e2d3c4b5
STAGING_DB_PASSWORD=StgPass2026!Temp
STAGING_VAULT_ROLE_ID=staging-role-8f5k2j9x
STAGING_VAULT_SECRET_ID=staging-secret-3k9m2l7p
```

---

## Environment Configuration

### Step 1: Create Staging Environment File

```bash
# Copy template
cp /Users/Zet/Agentco/.env.staging.example /Users/Zet/Agentco/.env.staging

# Edit with staging values
vim /Users/Zet/Agentco/.env.staging
```

### Step 2: Validate Configuration

```bash
# Verify all required variables are set
grep "REPLACE_ME" /Users/Zet/Agentco/.env.staging
# Should output: (empty - no REPLACE_ME placeholders)

# Verify mode
grep "AGENTCO_ENV" /Users/Zet/Agentco/.env.staging
# Should output: AGENTCO_ENV=staging

# Verify production mode
grep "NODE_ENV" /Users/Zet/Agentco/.env.staging
# Should output: NODE_ENV=production
```

### Step 3: Load Environment

```bash
cd /Users/Zet/Agentco
source .env.staging

# Verify critical variables
echo "Database: $DATABASE_URL"
echo "Kafka: $KAFKA_BROKERS"
echo "API Key: ${AGENTCO_API_KEY:0:8}***"
```

---

## Infrastructure Setup

### Step 1: Start Docker Compose Services

```bash
cd /Users/Zet/Agentco

# Start all staging services
docker-compose -f docker-compose.staging.yml up -d

# Verify services are starting
docker-compose -f docker-compose.staging.yml logs -f --tail=20
```

### Step 2: Wait for Healthchecks

Services have healthchecks. Allow 30-60 seconds for all to be healthy:

```bash
# Check status
docker-compose -f docker-compose.staging.yml ps

# All should show "healthy" in status. Example:
# NAME                           STATUS
# agentco-postgres-staging       Up 45s (healthy)
# agentco-redis-staging          Up 45s (healthy)
# agentco-kafka-staging          Up 45s (healthy)
# ...
```

### Step 3: Verify Connectivity

```bash
# Test PostgreSQL
psql "$DATABASE_URL" -c "SELECT version();"
# Should return PostgreSQL version

# Test Redis
redis-cli -p 6380 PING
# Should return: PONG

# Test Kafka
echo "" | nc -zv localhost 9092
# Should show: Connection succeeded

# Test Prometheus
curl -s http://localhost:9090/-/healthy
# Should return: 200 OK

# Test Grafana
curl -s http://localhost:3050/api/health | jq .
# Should return: {"status":"ok"}
```

**If any connectivity fails:** Check Docker logs with `docker-compose -f docker-compose.staging.yml logs [service-name]`

---

## Database Setup

### Step 1: Create Staging Database

PostgreSQL is started with database `agentco_staging` already created (via POSTGRES_DB).

Verify:
```bash
psql postgresql://agentco_staging:STAGING_PASSWORD_REQUIRED@localhost:5433/postgres -c "\l"
# Should list agentco_staging database
```

### Step 2: Run Migrations

```bash
cd /Users/Zet/Agentco/backend

# Run all migrations
python3 src/db/run_migrations.py

# Expected output:
# Running migration: 001_initial_schema.sql
# Running migration: 002_autonomy_foundation.sql
# ...
# [OK] All migrations completed successfully
```

### Step 3: Verify Schema

```bash
# Count tables
psql "$DATABASE_URL" -t -c \
  "SELECT count(*) as table_count 
   FROM information_schema.tables 
   WHERE table_schema = 'public';"
# Should show: 40+

# List critical tables
psql "$DATABASE_URL" -c "\dt" | head -20
# Should include:
# - autonomy_tasks
# - autonomy_episodes
# - learner_candidates
# - eval_scorecards
# - canary_plans
```

### Step 4: Create Backup

Before proceeding, create a clean baseline backup:

```bash
# Full database dump
pg_dump "$DATABASE_URL" > /tmp/agentco_staging_baseline.sql

# Verify
ls -lh /tmp/agentco_staging_baseline.sql
# Should be 5-20 MB (depending on schema size)
```

---

## Building the Backend

### Step 1: Install Dependencies

```bash
cd /Users/Zet/Agentco/backend

# Clean install
rm -rf node_modules package-lock.json
npm install

# Verify TypeScript compiler
npm run build --version
```

### Step 2: Compile Backend

```bash
cd /Users/Zet/Agentco/backend

# Build
npm run build

# Expected output:
# Successfully compiled X files
# dist/ directory created

# Verify compilation success
ls -la dist/ | head
# Should show: .js, .d.ts, .js.map files
```

### Step 3: Verify Build

```bash
# Check TypeScript errors
npx tsc --noEmit
# Should exit with code 0 (no errors)

# Test that backend can import modules
node -e "require('./dist/index.js')" && echo "✓ Backend loads"
```

---

## Deploying to Staging

### Step 1: Start Backend

```bash
cd /Users/Zet/Agentco/backend

# Set environment
export AGENTCO_ENV=staging
export NODE_ENV=production

# Source staging config
source ../.env.staging

# Start backend
npm run start

# Expected output:
# INFO  server.ts:123 Initializing backend...
# INFO  server.ts:156 Database connected
# INFO  server.ts:189 Kafka connected
# INFO  server.ts:203 OpenTelemetry initialized
# INFO  server.ts:245 🚀 Server listening on http://0.0.0.0:3001
```

### Step 2: Verify Backend Started

In a new terminal:

```bash
# Test health endpoint
curl -s http://localhost:3001/api/health | jq .
# Should return:
# {
#   "status": "ready",
#   "environment": "staging",
#   "timestamp": "2026-06-23T10:30:00Z"
# }

# Test database connectivity
curl -s http://localhost:3001/api/db-health | jq .
# Should return: {"status":"connected"}

# Test Kafka connectivity
curl -s http://localhost:3001/api/kafka-health | jq .
# Should return: {"status":"connected"}
```

### Step 3: Verify Governance Rules Are Enforced

```bash
# Check that RBAC is enforced
curl -X GET http://localhost:3001/api/admin/settings -H "Authorization: Bearer invalid" 
# Should return: 403 Forbidden

# Check that audit logging is active
curl -s http://localhost:3001/api/audit-logs?limit=1 | jq .
# Should return: Recent audit events

# Check that safety flags are active
curl -s http://localhost:3001/api/governance/status | jq '.safety_flags'
# Should show all flags as true
```

---

## Smoke Tests

### Step 1: Run Smoke Test Script

```bash
cd /Users/Zet/Agentco

# Run smoke test
python3 scripts/test_production_smoke.py

# Expected output:
# ✓ Health check passed
# ✓ Database connected
# ✓ Kafka connected
# ✓ Audit logging active
# ✓ Governance gates initialized
# ✓ All 7 safety rules verified
#
# SUMMARY: 6/6 tests passed ✓
```

### Step 2: Manual API Tests

```bash
# Create a simple autonomy task
curl -X POST http://localhost:3001/api/autonomy/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AGENTCO_API_KEY" \
  -d '{
    "goal_id": "test_goal_1",
    "description": "Test autonomy task",
    "level": 1
  }'

# Should return 201 Created with task_id

# List tasks
curl -s http://localhost:3001/api/autonomy/tasks | jq '.tasks | length'
# Should return: 1
```

### Step 3: Verify Audit Trail

```bash
# Get audit events
curl -s http://localhost:3001/api/audit-logs?limit=10 | jq '.events[] | {action, actor, timestamp}'

# Should show:
# {
#   "action": "task_created",
#   "actor": "cli_user",
#   "timestamp": "2026-06-23T10:35:20Z"
# }
```

---

## Security Gates

### Step 1: Run Security Gate

```bash
cd /Users/Zet/Agentco

# Run comprehensive security gate
python3 scripts/test_production_security_gate.py

# Expected output:
# ============================================================
# PRODUCTION SECURITY GATE
# ============================================================
#
# [1/7] RBAC Enforcement
#   ✓ Unauthenticated request denied
#   ✓ Insufficient privilege denied
#   ✓ Authorized request allowed
#
# [2/7] Protected Surface Enforcement
#   ✓ Calibration immutable
#   ✓ Resolver immutable
#   ✓ Audit log immutable
#
# [3/7] Evaluation Gate
#   ✓ Candidate without eval blocked
#   ✓ Failed eval blocks promotion
#   ✓ Passed eval allows promotion
#
# [4/7] No Self-Certification
#   ✓ Learner cannot approve own candidate
#   ✓ Eval service must approve
#
# [5/7] Audit Trail
#   ✓ All actions logged
#   ✓ Logs immutable
#   ✓ Actor identity verified
#
# [6/7] Emergency Stop
#   ✓ Emergency freeze activates
#   ✓ All actions blocked during freeze
#   ✓ Freeze logs recorded
#
# [7/7] Governance Gates
#   ✓ Trust policies enforced
#   ✓ Civilization changes gated
#   ✓ Rollback procedures verified
#
# SUMMARY: 7/7 security gates passed ✓
# Exit code: 0
```

### Step 2: Verify Each Rule

If any gate fails, investigate:

```bash
# Check logs for failure reason
docker-compose -f docker-compose.staging.yml logs agentco-backend | grep -i error | tail -20

# Check database for incomplete migrations
psql "$DATABASE_URL" -c "SELECT * FROM schema_migrations ORDER BY applied_at DESC LIMIT 5;"

# Check RBAC settings
psql "$DATABASE_URL" -c "SELECT * FROM rbac_roles LIMIT 5;"
```

---

## Load Testing

### Step 1: Run Load Test

```bash
cd /Users/Zet/Agentco

# Run load test (simulates 50 concurrent users, 300 seconds)
make staging-load-test

# OR manually:
python3 scripts/test_production_load.py \
  --users 50 \
  --duration-seconds 300 \
  --ramp-up-seconds 60

# Expected output:
# Load Test Results
# ================
# Duration: 300s
# Users: 50 (ramped up over 60s)
# Total Requests: 5,000+
# Success Rate: 99%+
# Avg Latency: <500ms
# P99 Latency: <2s
# Throughput: 15-20 req/s
# Memory: Stable at ~500MB
# Database Connections: Stable at 30-40
```

### Step 2: Monitor During Load Test

In a separate terminal:

```bash
# Watch metrics in real-time
watch -n 1 'curl -s http://localhost:9090/api/v1/query?query=rate(http_requests_total[1m]) | jq .'

# Monitor database
watch -n 2 "psql \"$DATABASE_URL\" -c \"SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;\""

# Monitor memory
watch -n 1 'docker stats --no-stream | grep -E "agentco|CONTAINER"'
```

### Step 3: Load Test Results

After test completes, check results:

```bash
# View detailed report
cat audit_artifacts/load_test_report_*.json | jq .summary

# Check for errors
cat audit_artifacts/load_test_report_*.json | jq '.failures[] | {endpoint, error, count}' | head -20
```

---

## Disaster Recovery

### Step 1: Test Backup and Restore

```bash
# Create backup
pg_dump "$DATABASE_URL" > /tmp/agentco_staging_test_backup.sql

# Verify backup
ls -lh /tmp/agentco_staging_test_backup.sql
file /tmp/agentco_staging_test_backup.sql

# Restore to test database
psql postgresql://agentco_staging:password@localhost:5433/postgres \
  -c "CREATE DATABASE agentco_staging_restore;"

psql postgresql://agentco_staging:password@localhost:5433/agentco_staging_restore \
  < /tmp/agentco_staging_test_backup.sql

# Verify restore
psql postgresql://agentco_staging:password@localhost:5433/agentco_staging_restore \
  -c "SELECT count(*) FROM autonomy_tasks;"
# Should match original count

# Cleanup
psql postgresql://agentco_staging:password@localhost:5433/postgres \
  -c "DROP DATABASE agentco_staging_restore;"
```

### Step 2: Test Failover Scenario

```bash
# Simulate crash: stop backend
pkill -f "npm run start"

# Verify failure detected
curl http://localhost:3001/api/health 2>&1 | grep -i "connection refused"

# Restart backend
cd /Users/Zet/Agentco/backend && npm run start &

# Verify recovery
sleep 5
curl -s http://localhost:3001/api/health | jq .status
# Should show: "ready"
```

### Step 3: Test Data Consistency After Recovery

```bash
# Count tasks before crash
TASK_COUNT_BEFORE=$(psql "$DATABASE_URL" -t -c "SELECT count(*) FROM autonomy_tasks;")

# After recovery, count again
TASK_COUNT_AFTER=$(psql "$DATABASE_URL" -t -c "SELECT count(*) FROM autonomy_tasks;")

# Should match
echo "Before: $TASK_COUNT_BEFORE, After: $TASK_COUNT_AFTER"
[ "$TASK_COUNT_BEFORE" = "$TASK_COUNT_AFTER" ] && echo "✓ Data consistent" || echo "✗ Data mismatch!"
```

---

## Rollback Procedures

### Step 1: Rollback Backend

```bash
# If backend has issues, rollback to previous version
git checkout HEAD~1 -- backend/

# Or rollback entire deployment
cd /Users/Zet/Agentco/backend
npm run build
npm run start
```

### Step 2: Rollback Database

```bash
# If migrations caused issues, restore from backup
psql postgresql://agentco_staging:password@localhost:5433/postgres \
  -c "DROP DATABASE agentco_staging;"

psql postgresql://agentco_staging:password@localhost:5433/postgres \
  -c "CREATE DATABASE agentco_staging;"

psql "$DATABASE_URL" < /tmp/agentco_staging_baseline.sql

# Verify restore
psql "$DATABASE_URL" -c "\dt" | wc -l
```

### Step 3: Verify Rollback Success

```bash
# Test health after rollback
curl -s http://localhost:3001/api/health | jq .

# Run smoke tests
python3 scripts/test_production_smoke.py
```

---

## Emergency Procedures

### Emergency Shutdown

When a critical incident requires immediate shutdown:

```bash
# Set emergency flag
curl -X POST http://localhost:3001/api/governance/emergency-shutdown \
  -H "Authorization: Bearer $AGENTCO_API_KEY" \
  -d '{"reason": "CRITICAL_INCIDENT"}'

# Verify flag is set
curl -s http://localhost:3001/api/governance/status | jq '.emergency_stop'
# Should show: true

# All subsequent requests will be blocked with 503 Service Unavailable
curl http://localhost:3001/api/autonomy/tasks
# Returns: 503 Service Unavailable (Emergency shutdown active)
```

### Emergency Trust Freeze

Block all trust-affecting operations:

```bash
# Activate trust freeze
curl -X POST http://localhost:3001/api/governance/trust-freeze \
  -H "Authorization: Bearer $AGENTCO_API_KEY" \
  -d '{"reason": "SUSPICIOUS_PATTERN_DETECTED"}'

# Verify freeze is active
curl -s http://localhost:3001/api/governance/status | jq '.trust_freeze'
# Should show: true

# Promotion attempts are blocked
curl -X POST http://localhost:3001/api/autonomy/promote \
  -H "Authorization: Bearer $AGENTCO_API_KEY" \
  -d '{"candidate_id": "test"}' 
# Returns: 403 Forbidden (Trust freeze active)
```

### Restart After Emergency

```bash
# Clear flags after incident resolved
curl -X POST http://localhost:3001/api/governance/resume \
  -H "Authorization: Bearer $AGENTCO_API_KEY" \
  -d '{"reason": "INCIDENT_RESOLVED_SAFE_RESTART"}'

# Verify flags cleared
curl -s http://localhost:3001/api/governance/status | jq '.emergency_stop, .trust_freeze'
# Should both show: false
```

---

## Observability Setup

### Step 1: Access Prometheus

```bash
# Prometheus UI
open http://localhost:9090

# Query example: Request rate
http_requests_total[5m]

# Query example: Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Step 2: Access Grafana

```bash
# Grafana UI
open http://localhost:3050

# Login: admin / admin

# Create dashboard or import existing:
# - Backend latency
# - Database connection pool
# - Message queue depth
# - Memory usage
# - Governance gate status
```

### Step 3: Set Up Alerts

Configure Prometheus alerting rules:

```yaml
groups:
  - name: agentco-staging
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        
      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        
      - alert: KafkaDown
        expr: kafka_up == 0
        for: 1m
```

---

## 48-Hour Burn-In Checklist

### Before Starting

- [ ] All security gates passed
- [ ] Load test passed
- [ ] Disaster recovery tested
- [ ] On-call team assigned
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Runbooks available
- [ ] Status page ready

### Every 4 Hours

- [ ] Check health dashboard
- [ ] Review error logs
- [ ] Verify all services healthy
- [ ] No unusual memory growth
- [ ] No connection pool exhaustion

### Every 8 Hours

- [ ] Run smoke tests
- [ ] Review Prometheus metrics
- [ ] Check disk space usage
- [ ] Verify backup jobs completed
- [ ] No database slow queries

### Daily (2 times)

- [ ] Full system check via `make autonomy-level4-full-test`
- [ ] Database statistics updated
- [ ] No unexpected audit events
- [ ] Governance gates verified
- [ ] Performance metrics stable

### Throughout 48 Hours

- [ ] Document any anomalies
- [ ] Log all configuration changes
- [ ] Record all test results
- [ ] Note any near-misses or warnings
- [ ] Collect evidence for promotion

---

## Production Promotion Criteria

### Data Stability
- [x] No data corruption events
- [x] All ACID properties maintained
- [x] Audit trail complete and immutable
- [x] Backup/restore successful

### Performance
- [x] P99 latency < 2 seconds
- [x] Error rate < 0.1%
- [x] Throughput stable
- [x] Memory/CPU stable (no leaks)

### Security
- [x] All 7 safety rules enforced
- [x] RBAC working correctly
- [x] Protected surfaces immutable
- [x] No unauthorized access attempts

### Governance
- [x] Emergency shutdown verified
- [x] Trust freeze verified
- [x] Evaluation gates blocking properly
- [x] Promotion pipeline working

### Operations
- [x] Alerts configured and tested
- [x] Logs aggregated and searchable
- [x] Metrics dashboard available
- [x] Runbooks completed
- [x] Team trained on procedures

### Testing
- [x] Smoke tests: 100% pass
- [x] Load test: 99%+ success
- [x] Security gate: 7/7 pass
- [x] Disaster recovery: Verified
- [x] Full regression: 100% pass

**Decision:** If all checkboxes pass → PRODUCTION_READY  
**Decision:** If any fail → Investigate and resolve before promotion

---

## Conditions That Block Production

### CRITICAL (Must Fix)
- ❌ Any safety rule not enforced
- ❌ RBAC enforcement disabled
- ❌ Protected surfaces mutable
- ❌ Audit trail incomplete
- ❌ Database integrity compromised
- ❌ Secrets in logs or version control

### HIGH (Must Address)
- ❌ P99 latency > 5 seconds
- ❌ Error rate > 1%
- ❌ Memory leak detected
- ❌ Database corruption event
- ❌ Unhandled exceptions in production code

### MEDIUM (Must Resolve)
- ❌ Security gates failing
- ❌ Load test < 95% success
- ❌ On-call team not trained
- ❌ Runbooks incomplete
- ❌ Monitoring gaps identified

### If ANY Blocker Found
1. **STOP:** Do not proceed to production
2. **INVESTIGATE:** Root cause analysis
3. **FIX:** Code fix or configuration change
4. **RETEST:** Re-run 48-hour burn-in
5. **DOCUMENT:** What failed, why, how fixed
6. **RETRY:** After all fixes verified

---

## Runbook: Incident Response

### Incident: High Error Rate (>1%)

**Detection:** Prometheus alert or manual check

**Response:**
```bash
# Step 1: Verify alert
curl -s http://localhost:9090/api/v1/query \
  "query=rate(http_requests_total{status=~'5..'}[5m])"

# Step 2: Check logs
docker-compose -f docker-compose.staging.yml logs --tail=100 agentco-backend | grep -i error

# Step 3: Check database
psql "$DATABASE_URL" -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;"

# Step 4: If database issue: restart connection pool
# (automatic - no action needed)

# Step 5: If application issue: check recent changes
git log --oneline -5

# Step 6: Rollback if necessary
git revert HEAD
npm run build && npm run start
```

### Incident: Database Unreachable

**Detection:** Health check fails or connection timeouts

**Response:**
```bash
# Step 1: Check database status
docker-compose -f docker-compose.staging.yml ps postgres-staging

# Step 2: If container stopped, restart it
docker-compose -f docker-compose.staging.yml restart postgres-staging

# Step 3: Verify connectivity
psql "$DATABASE_URL" -c "SELECT 1;"

# Step 4: If still fails, check logs
docker-compose -f docker-compose.staging.yml logs postgres-staging | tail -50

# Step 5: As last resort: restore from backup
# (See Disaster Recovery section)
```

### Incident: Kafka Not Available

**Detection:** Event streaming errors in logs

**Response:**
```bash
# Step 1: Check Kafka status
docker-compose -f docker-compose.staging.yml ps kafka-staging

# Step 2: Restart Kafka
docker-compose -f docker-compose.staging.yml restart kafka-staging zookeeper-staging

# Step 3: Wait for healthcheck
sleep 30 && docker-compose -f docker-compose.staging.yml ps

# Step 4: Verify topics exist
docker exec agentco-kafka-staging kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list

# Step 5: If needed, recreate topics
docker exec agentco-kafka-staging kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create \
  --topic autonomy-events \
  --partitions 3 \
  --replication-factor 1
```

### Incident: Safety Rule Violation Detected

**Detection:** Security gate failure or audit log anomaly

**Response:**
```bash
# Step 1: IMMEDIATELY activate emergency stop
curl -X POST http://localhost:3001/api/governance/emergency-shutdown \
  -H "Authorization: Bearer $AGENTCO_API_KEY" \
  -d '{"reason": "SAFETY_RULE_VIOLATION"}'

# Step 2: Get detailed logs
psql "$DATABASE_URL" -c \
  "SELECT * FROM audit_log WHERE created_at > now() - interval '1 hour' ORDER BY created_at DESC;"

# Step 3: Engage security team
# (Manual - notify security@example.com with logs)

# Step 4: Investigate root cause
git log --oneline --since="1 hour ago"
docker-compose -f docker-compose.staging.yml logs --since="1h" | grep -i "rule\|safety\|violation"

# Step 5: Fix and redeploy
# (Detailed fix depends on specific violation)

# Step 6: Re-run security gate
python3 scripts/test_production_security_gate.py

# Step 7: Clear emergency flag
curl -X POST http://localhost:3001/api/governance/resume \
  -H "Authorization: Bearer $AGENTCO_API_KEY" \
  -d '{"reason": "SAFETY_VIOLATION_FIXED_VERIFIED"}'
```

---

## Support & Escalation

### First Contact
**Problem:** General questions or clarification  
**Contact:** DevOps Lead  
**Response Time:** 30 minutes  

### Operations Issue
**Problem:** Service not starting, health checks failing  
**Contact:** SRE On-Call  
**Response Time:** 15 minutes  
**Escalation:** If not resolved in 1 hour, escalate to Infrastructure Team Lead  

### Security Issue
**Problem:** Authorization failure, audit anomaly, suspected breach  
**Contact:** Security Team (security@example.com)  
**Response Time:** 5 minutes  
**Escalation:** IMMEDIATE to CISO if safety rule violation confirmed  

### Database Issue
**Problem:** Migration failure, corruption, slowness  
**Contact:** Database Admin  
**Response Time:** 15 minutes  
**Escalation:** If not resolved in 30 minutes, activate Disaster Recovery

### Performance Issue
**Problem:** High latency, memory leak, CPU spike  
**Contact:** Platform Team  
**Response Time:** 30 minutes  
**Escalation:** If issue persists after 1 hour investigation, rollback to previous version

---

## Appendix A: Quick Reference

### Start All Services
```bash
cd /Users/Zet/Agentco
source .env.staging
docker-compose -f docker-compose.staging.yml up -d
cd backend && npm run start
```

### Stop All Services
```bash
docker-compose -f docker-compose.staging.yml down
pkill -f "npm run start"
```

### View Logs
```bash
# Backend
docker-compose -f docker-compose.staging.yml logs -f agentco-backend

# Database
docker-compose -f docker-compose.staging.yml logs -f postgres-staging

# All
docker-compose -f docker-compose.staging.yml logs -f
```

### Run All Tests
```bash
make staging-validation-gate
```

### Health Check
```bash
curl http://localhost:3001/api/health && echo "✓"
```

---

## Appendix B: Glossary

**Idempotency:** Operation produces same result whether run once or multiple times  
**RBAC:** Role-Based Access Control - permissions based on assigned roles  
**Protected Surface:** Core system data that cannot be modified (calibration, audit logs, etc.)  
**Safety Rule:** Non-negotiable enforcement that prevents unsafe operations  
**Burn-In:** Extended runtime to verify stability and uncover latent issues  
**Canary Deployment:** Gradual rollout to subset before full deployment  
**Rollback:** Reverting to previous known-good state  

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-06-23 | Production Team | Initial staging deployment guide |

---

**Last Updated:** 2026-06-23  
**Status:** APPROVED FOR STAGING DEPLOYMENT  
**Next Review:** After first 48-hour burn-in completes

