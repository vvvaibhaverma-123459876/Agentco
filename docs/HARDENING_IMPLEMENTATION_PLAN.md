> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# Production Hardening Implementation Plan
**AgentCo Autonomy System**

---

## Priority 1: Critical Fixes (Must do before any deployment)

### 1.1 Database Connection Pooling

**Current Issue**: Creates new connection per persist call → connection exhaustion at 20+ specialists

**Fix Location**: `agents/autonomy/specialist_agent.py`

```python
# BEFORE:
def get_db_connection():
    if not db_url:
        return None
    conn = psycopg2.connect(db_url)  # ← NEW CONNECTION EVERY TIME!
    return conn

# AFTER:
import psycopg2.pool

# Initialize at module load
_connection_pool = None

def init_db_pool():
    global _connection_pool
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return
    
    _connection_pool = psycopg2.pool.SimpleConnectionPool(
        1, 5,  # min=1, max=5
        db_url,
        connect_timeout=5,
        options="-c statement_timeout=10000"  # 10s query timeout
    )

def get_db_connection():
    global _connection_pool
    if not _connection_pool:
        init_db_pool()
    
    try:
        return _connection_pool.getconn()
    except psycopg2.pool.PoolError:
        raise RuntimeError("Database connection pool exhausted")

def return_db_connection(conn):
    global _connection_pool
    if _connection_pool:
        _connection_pool.putconn(conn)

# Usage:
def persist_evidence(self, url, content):
    evidence_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO autonomy_evidence ...")
        conn.commit()
        return evidence_id
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Failed to persist evidence: {e}")
    finally:
        return_db_connection(conn)
```

**Expected Improvement**: 
- Connection reuse: 200ms per operation → 50ms
- Concurrent specialists: 5 max → 20+ sustainable
- Connection exhaustion errors: Eliminated for reasonable loads

**Testing**:
```python
# Test connection pool
pool = init_db_pool()
connections = [get_db_connection() for _ in range(5)]
# 6th call should raise PoolError
try:
    get_db_connection()
    assert False, "Should have raised PoolError"
except RuntimeError:
    pass  # Expected
for conn in connections:
    return_db_connection(conn)
```

---

### 1.2 Python Subprocess Output Capture & Logging

**Current Issue**: Subprocess stderr/stdout ignored → failures invisible

**Fix Location**: `backend/src/services/team-activation.service.ts`

```typescript
// BEFORE:
const childProcess = spawn('python3', args, {
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe'],
});

// AFTER:
const childProcess = spawn('python3', args, {
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe'],
});

const logFile = `/tmp/specialist_${specialistId}.log`;
const logStream = fs.createWriteStream(logFile, { flags: 'a' });

// Capture and log stdout/stderr
childProcess.stdout?.on('data', (data) => {
    const timestamp = new Date().toISOString();
    logStream.write(`[${timestamp}] [INFO] ${data.toString()}\n`);
    console.log(`[Specialist ${specialistId}] ${data.toString().trim()}`);
});

childProcess.stderr?.on('data', (data) => {
    const timestamp = new Date().toISOString();
    logStream.write(`[${timestamp}] [ERROR] ${data.toString()}\n`);
    console.error(`[Specialist ${specialistId}] ERROR: ${data.toString().trim()}`);
    
    // Alert on errors
    if (data.toString().includes('exception') || data.toString().includes('failed')) {
        // Send alert (will implement in metrics section)
        console.error(`[ALERT] Specialist error detected: ${specialistId}`);
    }
});

childProcess.on('exit', (code) => {
    const timestamp = new Date().toISOString();
    logStream.write(`[${timestamp}] [INFO] Process exited with code ${code}\n`);
    logStream.end();
    
    if (code !== 0) {
        console.error(`[ALERT] Specialist ${specialistId} exited with error code ${code}`);
    }
});

// Store log path in database
await db.query(
    `UPDATE autonomy_team_activations SET metadata = jsonb_set(metadata, '{log_file}', to_jsonb($1))
     WHERE specialist_id = $2`,
    [logFile, specialistId]
);
```

**Expected Improvement**:
- Visibility into specialist failures
- Can debug issues post-mortem
- Detect patterns (e.g., "always fails after 5 iterations")

---

### 1.3 Graceful Shutdown & Process Cleanup

**Current Issue**: Orphaned processes on Node crash

**Fix Location**: `backend/src/services/team-activation.service.ts`

```typescript
export class TeamActivationService {
    private activeSpecialists = new Map<string, SpecialistInstance>();
    private activeProcesses = new Map<string, ChildProcess>();

    constructor() {
        // Graceful shutdown handler
        process.on('SIGTERM', () => {
            console.log('[TeamActivation] SIGTERM received, shutting down specialists...');
            this.gracefulShutdown().catch(err => {
                console.error('[TeamActivation] Error during shutdown:', err);
                process.exit(1);
            });
        });

        process.on('SIGINT', () => {
            console.log('[TeamActivation] SIGINT received, shutting down specialists...');
            this.gracefulShutdown().catch(err => {
                console.error('[TeamActivation] Error during shutdown:', err);
                process.exit(1);
            });
        });
    }

    private async gracefulShutdown(): Promise<void> {
        const timeout = 10000; // 10 seconds
        const startTime = Date.now();

        // Step 1: Signal all specialists to terminate
        for (const [specialistId, process] of this.activeProcesses) {
            try {
                process.kill('SIGTERM');
                console.log(`[TeamActivation] Sent SIGTERM to ${specialistId}`);
            } catch (err) {
                console.warn(`[TeamActivation] Failed to kill ${specialistId}:`, err);
            }
        }

        // Step 2: Wait for graceful termination
        while (this.activeProcesses.size > 0 && Date.now() - startTime < timeout) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        // Step 3: Force kill any remaining processes
        for (const [specialistId, process] of this.activeProcesses) {
            if (!process.killed) {
                try {
                    process.kill('SIGKILL');
                    console.log(`[TeamActivation] Force-killed ${specialistId}`);
                } catch (err) {
                    console.warn(`[TeamActivation] Failed to SIGKILL ${specialistId}:`, err);
                }
            }
        }

        // Step 4: Cleanup database records
        for (const [specialistId] of this.activeSpecialists) {
            try {
                await this.terminateSpecialist(specialistId, {
                    artifacts: [],
                    evidence: [],
                    claims: [],
                    error: 'Process killed during shutdown',
                });
            } catch (err) {
                console.warn(`[TeamActivation] Error terminating ${specialistId}:`, err);
            }
        }

        console.log('[TeamActivation] Graceful shutdown complete');
    }

    async terminateSpecialist(...) {
        // ... existing code ...
        
        // Kill subprocess
        const childProcess = this.activeProcesses.get(specialistId);
        if (childProcess && !childProcess.killed) {
            try {
                childProcess.kill('SIGTERM');
                
                // Wait 2 seconds for graceful exit
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // If still running, force kill
                if (!childProcess.killed) {
                    childProcess.kill('SIGKILL');
                    console.warn(`[TeamActivation] Force-killed specialist ${specialistId}`);
                }
            } catch (err) {
                console.error(`[TeamActivation] Error killing process:`, err);
            }
        }
        
        // ... existing cleanup code ...
    }
}
```

**Expected Improvement**:
- No orphaned processes on crash
- Graceful resource cleanup
- Data consistency maintained

---

### 1.4 Python Error Handling & Retries

**Current Issue**: Silent data loss when database operations fail

**Fix Location**: `agents/autonomy/specialist_agent.py`

```python
def persist_evidence(self, url: str, content: str = '', ...) -> str:
    """Persist evidence with retry logic"""
    evidence_id = str(uuid.uuid4())
    
    # Retry logic: exponential backoff
    for attempt in range(3):
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO autonomy_evidence
                (id, source_id, url, title, snippet, content_hash, ...)
                VALUES (%s, %s, %s, %s, %s, %s, ...)
            """, (evidence_id, source_id, url, title, snippet, content_hash, ...))
            
            conn.commit()
            print(f"[Evidence] Persisted: {evidence_id}")
            return evidence_id
            
        except psycopg2.errors.UniqueViolation as e:
            # UUID collision (extremely rare), generate new ID
            evidence_id = str(uuid.uuid4())
            if attempt < 2:
                continue
            raise RuntimeError(f"Evidence ID collision after 3 attempts: {e}")
            
        except psycopg2.errors.OperationalError as e:
            # Connection error, retry with backoff
            if conn:
                conn.rollback()
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            if attempt < 2:
                print(f"[Evidence] DB connection failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
                continue
            raise RuntimeError(f"Database unavailable after 3 attempts: {e}")
            
        except psycopg2.errors.InsufficientPrivilege as e:
            # Permissions issue, don't retry
            raise RuntimeError(f"Database permission denied: {e}")
            
        except Exception as e:
            # Unexpected error, retry
            if conn:
                conn.rollback()
            if attempt < 2:
                print(f"[Evidence] Unexpected error, retrying: {e}")
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Failed to persist evidence after 3 attempts: {e}")
            
        finally:
            if conn:
                return_db_connection(conn)
    
    # Should never reach here
    raise RuntimeError(f"Unexpected: Evidence persist failed")
```

**Expected Improvement**:
- Handles transient database failures
- No silent data loss
- Orchestrator knows when persistence fails
- Retries with exponential backoff

---

### 1.5 Request Validation in Specialist

**Current Issue**: Invalid actions cause specialist crashes

**Fix Location**: `agents/autonomy/specialist_agent.py`

```python
class SpecialistAgent(BaseAgent):
    def __init__(self, specialist_id: str, role: str, budget: Dict[str, int]):
        # ... existing code ...
        self.allowed_actions = self.get_allowed_actions()
    
    def get_allowed_actions(self) -> set:
        """Return allowed action types for this specialist"""
        # Map roles to allowed actions (from backend spec)
        role_actions = {
            'researcher': {'WEB_SEARCH', 'FETCH_PAGE', 'EXTRACT_EVIDENCE', 'UPDATE_MEMORY', 'EVALUATE_PROGRESS'},
            'fetcher': {'FETCH_PAGE', 'EVALUATE_PROGRESS'},
            'data_analyst': {'EXTRACT_EVIDENCE', 'GENERATE_CLAIM', 'UPDATE_MEMORY', 'EVALUATE_PROGRESS'},
            # ... etc
        }
        return role_actions.get(self.role, set())
    
    def setup_routes(self):
        @self.app.route('/execute', methods=['POST'])
        def execute_action():
            try:
                action_spec = request.json
                if not action_spec:
                    return jsonify({
                        'status': 'failed',
                        'errors': ['No action spec provided']
                    }), 400
                
                # VALIDATION: Check budget FIRST
                try:
                    self.check_budget()
                except RuntimeError as e:
                    return jsonify({
                        'status': 'failed',
                        'errors': [f'Budget exceeded: {str(e)}']
                    }), 429
                
                # VALIDATION: Check action type is allowed
                action_type = action_spec.get('actionType', '').lower()
                if action_type not in self.allowed_actions:
                    return jsonify({
                        'status': 'failed',
                        'errors': [f'Action {action_type} not allowed for role {self.role}']
                    }), 400
                
                # VALIDATION: Check required arguments
                if action_type in ['web_search', 'fetch_page'] and 'args' not in action_spec:
                    return jsonify({
                        'status': 'failed',
                        'errors': [f'Missing required args for action {action_type}']
                    }), 400
                
                # VALIDATION: Bounds check on string lengths
                objective = action_spec.get('objective', '')
                if len(objective) > 1000:
                    return jsonify({
                        'status': 'failed',
                        'errors': ['Objective too long (max 1000 chars)']
                    }), 400
                
                # Now execute
                result = self.handle_action(action_spec)
                
                return jsonify({
                    'status': 'completed',
                    'observations': result.get('observations', {}),
                    'artifacts': result.get('artifacts', []),
                    'tokens_used': self.tokens_used,
                    'errors': result.get('errors')
                }), 200
                
            except Exception as e:
                return jsonify({
                    'status': 'failed',
                    'errors': [f'Unexpected error: {str(e)}']
                }), 500
```

**Expected Improvement**:
- Clear error messages for invalid actions
- Prevents crashes from bad input
- Allows orchestrator to handle errors appropriately

---

## Priority 2: Security Hardening (Week 2)

### 2.1 Request Signing with HMAC

**Concept**: Orchestrator signs each request, specialist verifies signature

```typescript
// ORCHESTRATOR: Sign request
import crypto from 'crypto';

const secret = process.env.SPECIALIST_SHARED_SECRET || generateSecretKey();

function signRequest(payload: object): { signature: string; timestamp: number } {
    const timestamp = Math.floor(Date.now() / 1000);
    const message = JSON.stringify(payload) + ':' + timestamp;
    const signature = crypto
        .createHmac('sha256', secret)
        .update(message)
        .digest('hex');
    
    return { signature, timestamp };
}

// Send request:
const actionSpec = { ... };
const { signature, timestamp } = signRequest(actionSpec);

const response = await fetch(specialist.httpEndpoint + '/execute', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-Signature': signature,
        'X-Timestamp': timestamp.toString(),
    },
    body: JSON.stringify(actionSpec),
});
```

```python
# SPECIALIST: Verify signature
import hashlib
import hmac
import time
import json

secret = os.environ.get('SPECIALIST_SHARED_SECRET', 'default-insecure')

def verify_request(payload_str: str, signature: str, timestamp: str) -> bool:
    # Verify timestamp is recent (within 30 seconds)
    request_time = int(timestamp)
    current_time = int(time.time())
    if abs(current_time - request_time) > 30:
        return False  # Reject old/future-dated requests
    
    # Verify signature
    message = payload_str + ':' + timestamp
    expected_signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected_signature)

# In Flask route:
@self.app.route('/execute', methods=['POST'])
def execute_action():
    signature = request.headers.get('X-Signature')
    timestamp = request.headers.get('X-Timestamp')
    
    if not signature or not timestamp:
        return jsonify({'status': 'failed', 'errors': ['Missing auth headers']}), 401
    
    payload_str = request.data.decode('utf-8')
    
    if not verify_request(payload_str, signature, timestamp):
        return jsonify({'status': 'failed', 'errors': ['Invalid signature']}), 401
    
    # Continue with action execution...
```

---

## Priority 3: Observability (Week 3)

### 3.1 Structured Logging

```typescript
// TypeScript logger setup
import winston from 'winston';

const logger = winston.createLogger({
    level: 'info',
    format: winston.format.json(),
    defaultMeta: { service: 'autonomy-orchestrator' },
    transports: [
        new winston.transports.File({ filename: '/var/log/autonomy-error.log', level: 'error' }),
        new winston.transports.File({ filename: '/var/log/autonomy-combined.log' }),
        new winston.transports.Console({
            format: winston.format.simple(),
        }),
    ],
});

// Usage:
logger.info('Specialist spawned', {
    specialistId,
    role,
    port,
    traceId,  // Add trace ID for correlation
});

logger.error('Specialist failed', {
    specialistId,
    role,
    error: error.message,
    traceId,
});
```

### 3.2 Prometheus Metrics

```typescript
import prometheus from 'prom-client';

// Define metrics
const specialistSpawnCounter = new prometheus.Counter({
    name: 'specialist_spawn_total',
    help: 'Total specialists spawned',
    labelNames: ['role', 'status'],
});

const specialistExecutionDuration = new prometheus.Histogram({
    name: 'specialist_execution_duration_seconds',
    help: 'Specialist execution time',
    labelNames: ['role'],
    buckets: [0.1, 0.5, 1, 2, 5, 10, 30],
});

const specialistErrors = new prometheus.Counter({
    name: 'specialist_errors_total',
    help: 'Total specialist errors',
    labelNames: ['role', 'error_type'],
});

// Usage:
specialistSpawnCounter.inc({ role, status: 'success' });
specialistExecutionDuration.labels(role).observe(elapsedSeconds);
specialistErrors.labels(role, errorType).inc();

// Expose metrics endpoint
app.get('/metrics', (req, res) => {
    res.set('Content-Type', prometheus.register.contentType);
    res.end(prometheus.register.metrics());
});
```

---

## Summary: Hardening Effort Estimates

| Item | Effort | Priority | Impact |
|------|--------|----------|--------|
| Connection pooling | 4h | 🔴 CRITICAL | Eliminates connection exhaustion |
| Process logging | 3h | 🔴 CRITICAL | Visibility into failures |
| Graceful shutdown | 4h | 🔴 CRITICAL | Prevents resource leaks |
| Error handling + retries | 6h | 🔴 CRITICAL | Eliminates silent data loss |
| Request validation | 4h | 🔴 CRITICAL | Prevents crash-causing bad input |
| HMAC signing | 6h | 🟠 HIGH | Prevents auth bypass |
| Structured logging | 4h | 🟠 HIGH | Enables debugging |
| Prometheus metrics | 6h | 🟠 HIGH | Enables monitoring |
| **Total** | **37h** | — | **Moves from 47% → 80% production-ready** |

---

## Success Criteria

After hardening:

- [ ] Can support 20+ concurrent specialists without connection exhaustion
- [ ] All specialist failures logged and visible
- [ ] No orphaned processes on restart
- [ ] Data persistence has retry logic (no silent loss)
- [ ] Invalid requests fail cleanly (return errors, don't crash)
- [ ] Requests authenticated with HMAC
- [ ] All operations have structured logs with trace IDs
- [ ] Prometheus metrics available
- [ ] Can debug issues post-mortem from logs
- [ ] Load test: 20 concurrent specialists complete successfully

---

**Next Step**: Pick first item (connection pooling) and implement.
