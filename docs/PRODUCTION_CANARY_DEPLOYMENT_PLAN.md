# Production Canary Deployment Plan

**Release:** v0.1.0-agentco-civilization-production  
**Date:** 2026-06-23  
**Method:** Blue-Green with 5-Stage Canary Rollout

---

## EXECUTIVE SUMMARY

AgentCo will be rolled out to production using a 5-stage canary approach (1% → 5% → 25% → 50% → 100%). Each stage lasts 5-30 minutes with continuous monitoring. At any stage, if metrics exceed thresholds, immediate rollback is triggered. Procedure is automated with manual decision gates at each stage.

**Status:** ✅ READY FOR CANARY ROLLOUT

---

## CANARY DEPLOYMENT OVERVIEW

**Total Duration:** ~2 hours  
**Stages:** 5 (1% → 5% → 25% → 50% → 100%)  
**Monitoring Frequency:** Every 30-60 seconds per stage  
**Decision Points:** 5 (one per stage)  
**Rollback Capability:** Available at all times  
**Rollback Method:** Blue-Green instant switch (< 5 min)

---

## STAGE 1: CANARY DEPLOYMENT (1% TRAFFIC)

**Duration:** 5-10 minutes  
**Traffic:** 1% of production load  
**Replicas Deployed:** 1-2 out of 50+  
**Expected Requests:** ~100 req/min (estimated)

### Deployment Steps

1. **Pre-Deployment Verification** (1 min)
   - [ ] Load balancer configured
   - [ ] Previous version (Blue) running and healthy
   - [ ] New version (Green) built and ready
   - [ ] Database connection string verified
   - [ ] Environment variables loaded
   - [ ] Health check endpoint configured

2. **Start New Instances** (1 min)
   - [ ] Launch 1-2 new instances with Green image
   - [ ] Wait for instances to start
   - [ ] Verify container health
   - [ ] Check application logs
   - [ ] Verify no startup errors

3. **Add to Load Balancer** (1 min)
   - [ ] Register new instances with load balancer
   - [ ] Set traffic weight: 1%
   - [ ] Verify traffic is being routed
   - [ ] Check initial request logs

4. **Monitor** (3-5 min)
   - [ ] Every 30 seconds: Check error rate
   - [ ] Every 30 seconds: Check latency
   - [ ] Every 60 seconds: Check logs
   - [ ] Every 60 seconds: Check metrics
   - [ ] Watch for any anomalies

### Success Criteria (All Must Pass)

| Metric | Threshold | Target | Status |
|--------|-----------|--------|--------|
| Error Rate | < 1% | < 0.1% | ⏳ |
| P99 Latency | < 2000ms | < 100ms | ⏳ |
| P95 Latency | < 1000ms | < 50ms | ⏳ |
| Memory Usage | < 500MB | < 300MB | ⏳ |
| CPU Usage | < 70% | < 40% | ⏳ |
| DB Connections | < 20 | < 10 | ⏳ |
| RBAC Denials | Normal | Normal | ⏳ |
| Protected Surface Blocks | Normal | Normal | ⏳ |
| Audit Write Failures | 0 | 0 | ⏳ |
| Emergency Controls | Responsive | < 5s | ⏳ |
| Calibration Mutations | 0 | 0 | ⏳ |

### Decision Gate 1

**GO Criteria:**
- ✅ Error rate < 1%
- ✅ P99 latency < 2000ms
- ✅ No RBAC bypasses detected
- ✅ Protected surfaces protected
- ✅ Audit logging working
- ✅ No calibration mutations
- ✅ Emergency controls responsive
- ✅ No critical logs

**NO-GO Criteria (Trigger Rollback):**
- ❌ Error rate > 1%
- ❌ P99 latency > 5000ms
- ❌ RBAC bypass detected
- ❌ Protected surface violation
- ❌ Audit write failure
- ❌ Emergency controls unresponsive
- ❌ Out of memory
- ❌ Database connection error

**Stage 1 Result:**
- If GO → Proceed to Stage 2
- If NO-GO → Rollback to Blue, investigate, retry

---

## STAGE 2: EARLY ADOPTION (5% TRAFFIC)

**Duration:** 10-15 minutes  
**Traffic:** 5% of production load  
**Replicas Deployed:** 3-5 out of 50+  
**Expected Requests:** ~500 req/min

### Deployment Steps

1. **Increase Traffic Weight** (1 min)
   - [ ] Update load balancer: Green weight = 5%
   - [ ] Blue weight = 95%
   - [ ] Verify traffic shift
   - [ ] Monitor error rate for spike

2. **Add More Instances** (1 min)
   - [ ] Launch 2-3 additional Green instances
   - [ ] Wait for health checks to pass
   - [ ] Verify startup logs clean
   - [ ] Add to load balancer

3. **Monitor** (5-10 min)
   - [ ] Every 30 seconds: Error rate, latency, resource usage
   - [ ] Every 60 seconds: Logs, metrics
   - [ ] Watch for cascading failures
   - [ ] Check database query performance
   - [ ] Verify memory not growing unbounded

### Success Criteria (Same as Stage 1, Plus Additional)

**Additional Checks:**
- [ ] No error spike at 5% traffic point
- [ ] P99 latency didn't increase > 50%
- [ ] Memory usage stable (not growing)
- [ ] CPU usage proportional to traffic increase
- [ ] Database query performance acceptable
- [ ] No connection pool exhaustion
- [ ] Replicas healthy and responsive

### Decision Gate 2

**GO Criteria:**
- ✅ All Stage 1 criteria still met
- ✅ No issues observed during traffic increase
- ✅ Performance proportional to load
- ✅ No resource exhaustion
- ✅ Stability maintained

**NO-GO Criteria (Trigger Rollback):**
- ❌ Error rate increased > 0.5% from baseline
- ❌ Latency increased > 100% from baseline
- ❌ Any Stage 1 NO-GO condition occurs
- ❌ Memory leak detected (growth > 50MB)
- ❌ Cascading failures detected

**Stage 2 Result:**
- If GO → Proceed to Stage 3
- If NO-GO → Rollback, investigate

---

## STAGE 3: RAMP (25% TRAFFIC)

**Duration:** 15-20 minutes  
**Traffic:** 25% of production load  
**Replicas Deployed:** 10-15 out of 50+  
**Expected Requests:** ~2,500 req/min  
**Load Type:** Mix of GET/POST/real patterns

### Deployment Steps

1. **Increase Traffic Weight** (2 min)
   - [ ] Update load balancer: Green weight = 25%
   - [ ] Blue weight = 75%
   - [ ] Monitor traffic flow
   - [ ] Check for load imbalance

2. **Scale Out** (2 min)
   - [ ] Launch 5-10 additional Green instances
   - [ ] Stagger launches (1 per 10 seconds)
   - [ ] Monitor startup sequence
   - [ ] Verify health checks

3. **Monitor Intensively** (10-15 min)
   - [ ] Every 30 seconds: All metrics
   - [ ] Every 60 seconds: Detailed logs
   - [ ] Watch for resource contention
   - [ ] Monitor database locks
   - [ ] Check connection pools
   - [ ] Verify no cascading failures
   - [ ] Monitor Redis cache hit rate
   - [ ] Check Kafka message lag

### Critical Monitoring Points at 25%

- **Database Performance:** Query times, connection pool, locks
- **Cache Performance:** Hit rate, memory usage
- **Message Queue:** Lag, throughput, error rate
- **Resource Usage:** CPU trending, memory growth, disk I/O
- **Application Metrics:** Request/response patterns, exception rates
- **Safety Rules:** All 7 non-negotiable rules still enforced

### Decision Gate 3

**GO Criteria:**
- ✅ All previous criteria met
- ✅ Performance scales linearly
- ✅ No resource bottlenecks
- ✅ Database performing well
- ✅ Cache hit rate stable
- ✅ Message queue lag minimal
- ✅ Stability at 25% load

**NO-GO Criteria:**
- ❌ Nonlinear performance degradation
- ❌ Resource exhaustion detected
- ❌ Database query time > 100ms (avg)
- ❌ Any Stage 2 NO-GO condition
- ❌ Cascading failures or cascade risk

**Stage 3 Result:**
- If GO → Proceed to Stage 4
- If NO-GO → Rollback, investigate

---

## STAGE 4: MAJORITY (50% TRAFFIC)

**Duration:** 20-30 minutes  
**Traffic:** 50% of production load  
**Replicas Deployed:** 25 out of 50+  
**Expected Requests:** ~5,000 req/min

### Deployment Steps

1. **Increase to 50%** (2 min)
   - [ ] Update load balancer: Green weight = 50%
   - [ ] Blue weight = 50%
   - [ ] Monitor traffic split
   - [ ] Verify even distribution

2. **Deploy Remaining Instances** (5 min)
   - [ ] Launch 10-15 more Green instances
   - [ ] Monitor deployment progress
   - [ ] Verify health checks
   - [ ] Check startup sequence

3. **Extended Monitoring** (15-25 min)
   - [ ] Every 30 seconds: All critical metrics
   - [ ] Every 2 minutes: Detailed analysis
   - [ ] Monitor for edge cases
   - [ ] Check concurrent user handling
   - [ ] Verify rate limiting working
   - [ ] Check timeout handling
   - [ ] Monitor for memory leaks
   - [ ] Check database transaction throughput

### Extended Success Criteria

- [ ] 50% traffic handled without issues
- [ ] No memory leaks (memory stable over time)
- [ ] No connection pool exhaustion
- [ ] Timeout handling correct
- [ ] Rate limiting working properly
- [ ] Error rate still < 0.5%
- [ ] Latency still acceptable (< 500ms P99)
- [ ] All safety rules enforced
- [ ] No cascading failures risk

### Decision Gate 4

**GO Criteria:**
- ✅ All previous criteria met
- ✅ Sustained stability at 50% load
- ✅ No memory growth over 10 minutes
- ✅ No connection issues
- ✅ Performance acceptable
- ✅ Safety rules maintained
- ✅ Confidence high for 100%

**NO-GO Criteria:**
- ❌ Memory growth detected
- ❌ Connection pool issues
- ❌ Stability degradation
- ❌ Any critical alert
- ❌ Safety rule violation

**Stage 4 Result:**
- If GO → Proceed to Stage 5 (Final)
- If NO-GO → Rollback, fix issue, retry from Stage 1

---

## STAGE 5: FULL DEPLOYMENT (100% TRAFFIC)

**Duration:** 30-60 minutes  
**Traffic:** 100% of production load  
**Replicas Deployed:** All 50+  
**All Traffic Shifted to Green**

### Deployment Steps

1. **Final Traffic Shift** (2 min)
   - [ ] Update load balancer: Green weight = 100%
   - [ ] Blue weight = 0%
   - [ ] Verify all traffic on Green
   - [ ] Monitor for any disruption

2. **Deploy Remaining Instances** (5 min)
   - [ ] Launch final batch of instances
   - [ ] Ensure all instances healthy
   - [ ] Monitor startup sequence
   - [ ] Verify no startup errors

3. **Sustained Monitoring** (30-50 min)
   - [ ] Every 30 seconds: Critical metrics
   - [ ] Every 5 minutes: Detailed analysis
   - [ ] Watch for edge cases at scale
   - [ ] Monitor for slow degradation
   - [ ] Check for resource exhaustion
   - [ ] Verify safety rules continuously
   - [ ] Monitor emergency controls
   - [ ] Check for data inconsistencies
   - [ ] Monitor audit trail
   - [ ] Verify observability working

### Full Load Criteria

- [ ] Error rate < 0.5%
- [ ] P99 latency < 500ms
- [ ] Memory stable (no unbounded growth)
- [ ] Database healthy
- [ ] Cache performing well
- [ ] Message queue lag minimal
- [ ] All 7 safety rules enforced
- [ ] Audit logging working
- [ ] Emergency controls responsive
- [ ] No cascading failures

### Decision Gate 5 - Final

**DEPLOYMENT SUCCESS Criteria:**
- ✅ 100% traffic processed without critical issues
- ✅ Error rate < 1% (0% critical)
- ✅ Performance acceptable
- ✅ All safety rules enforced
- ✅ Audit trail functional
- ✅ Observability complete
- ✅ No data loss or corruption
- ✅ Emergency controls operational

**ROLLBACK Criteria:**
- ❌ Error rate > 5%
- ❌ P99 latency > 5000ms
- ❌ Safety rule violation
- ❌ Data corruption detected
- ❌ Cascading failures
- ❌ Emergency controls unresponsive

**Final Result:**
- If SUCCESS → Proceed to Step 9 (Smoke Tests)
- If FAILURE → Rollback, fix issue

---

## ROLLBACK PROCEDURE (Available at All Stages)

**Trigger:** Automatic on threshold breach OR manual approval

**Rollback Steps:**
1. Stop traffic to Green instances (1 min)
2. Verify Blue still healthy (30 sec)
3. Route 100% traffic back to Blue (1 min)
4. Monitor Blue for recovery (1 min)
5. Verify application health (1 min)
6. Total rollback time: < 5 minutes

**Post-Rollback:**
1. Keep Green instances running for investigation
2. Gather logs and metrics from Green
3. Analyze failure cause
4. Update deployment plan
5. Schedule retry for next window

---

## CANARY DEPLOYMENT SUCCESS METRICS

| Metric | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Stage 5 |
|--------|---------|---------|---------|---------|---------|
| Error Rate | < 1% | < 0.5% | < 0.5% | < 0.5% | < 0.5% |
| P99 Latency | < 2s | < 1.5s | < 1s | < 500ms | < 500ms |
| CPU Usage | < 70% | < 60% | < 60% | < 60% | < 60% |
| Memory Usage | < 500MB | < 1GB | < 2GB | < 3GB | < 4GB |
| DB Connections | < 20 | < 40 | < 80 | < 150 | < 250 |
| Audit Writes/min | > 10 | > 50 | > 250 | > 500 | > 1000 |
| Safety Rules | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 |

---

## MONITORING DASHBOARD

**Key Metrics to Display:**
- Real-time error rate (%)
- P99 latency (ms)
- Throughput (req/sec)
- CPU usage (%)
- Memory usage (MB)
- Database connections (#)
- Cache hit rate (%)
- Message queue lag (sec)
- Safety rule violations (#)
- Emergency control status (OK/WARN)

---

## ABORT SCENARIOS

**Immediate Rollback (No Questions Asked):**
1. Error rate > 5%
2. P99 latency > 5000ms
3. RBAC bypass detected
4. Protected surface violation
5. Out of memory condition
6. Database connection failure
7. Audit logging failure
8. Emergency controls unresponsive
9. Data corruption detected
10. Cascading failures

---

## EXPECTED TIMELINE

```
Stage 1: 1%   | 05m | 16:25-16:30 | GO
Stage 2: 5%   | 10m | 16:30-16:40 | GO
Stage 3: 25%  | 15m | 16:40-16:55 | GO
Stage 4: 50%  | 25m | 16:55-17:20 | GO
Stage 5: 100% | 30m | 17:20-17:50 | SUCCESS
```

**Total Canary Duration:** ~2 hours (16:25-18:30)

---

## NEXT PHASE

After Stage 5 completes successfully:
- ✅ Step 9: Post-Deploy Smoke Tests
- ✅ Step 10: Production Observability Check
- ✅ Step 11: Production Safety Check
- ✅ Step 12: Release Monitoring Window (2h)
- ✅ Step 13: Final Status Report
- ✅ Step 14: Final Go/No-Go Decision

---

**Document:** PRODUCTION_CANARY_DEPLOYMENT_PLAN.md  
**Version:** 1.0  
**Status:** READY FOR CANARY ROLLOUT
