"""
Specialist Agent Base Class
============================
Foundation for all specialist agents.
Handles HTTP server, budget tracking, and action execution.
"""

from agents.base_agent import BaseAgent
from flask import Flask, request, jsonify
import threading
import json
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import hashlib
import os
import hmac
import time
from collections import defaultdict

# Database connection pooling (optional - only if env vars present)
try:
    import psycopg2
    import psycopg2.pool
    from psycopg2.extras import RealDictCursor
    HAS_DB = True
except ImportError:
    HAS_DB = False

_connection_pool = None

def init_db_pool():
    """Initialize database connection pool once at startup"""
    global _connection_pool
    if _connection_pool is not None:
        return  # Already initialized

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return

    try:
        _connection_pool = psycopg2.pool.SimpleConnectionPool(
            1,  # min connections
            5,  # max connections
            db_url,
            connect_timeout=5,
            options="-c statement_timeout=10000"  # 10s query timeout
        )
        print(f"[DB] Connection pool initialized: min=1, max=5")
    except Exception as e:
        print(f"[DB] Pool initialization failed: {e}")
        _connection_pool = None

def get_db_connection():
    """Get connection from pool if available"""
    global _connection_pool
    if not HAS_DB:
        return None

    # Initialize pool on first use
    if _connection_pool is None:
        init_db_pool()

    if _connection_pool is None:
        return None

    try:
        return _connection_pool.getconn()
    except psycopg2.pool.PoolError:
        print("[DB] Connection pool exhausted (all connections in use)")
        return None
    except Exception as e:
        print(f"[DB] Failed to get connection from pool: {e}")
        return None

def return_db_connection(conn):
    """Return connection to pool"""
    global _connection_pool
    if conn and _connection_pool:
        try:
            _connection_pool.putconn(conn)
        except Exception as e:
            print(f"[DB] Failed to return connection to pool: {e}")
            try:
                conn.close()
            except:
                pass


def verify_request_signature(payload_bytes: bytes, signature: str, timestamp: str) -> bool:
    """
    Verify HMAC-SHA256 signature of request.

    Args:
        payload_bytes: Raw request body bytes
        signature: X-Signature header value
        timestamp: X-Timestamp header value

    Returns:
        True if signature is valid and timestamp is recent
    """
    # Get shared secret from environment
    secret = os.environ.get('SPECIALIST_SHARED_SECRET', 'default-insecure-secret')

    # Check timestamp is recent (within 30 seconds to prevent replay attacks)
    try:
        request_time = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - request_time) > 30:
            print(f"[Auth] Signature timestamp too old: {abs(current_time - request_time)}s")
            return False
    except (ValueError, TypeError):
        print(f"[Auth] Invalid timestamp format: {timestamp}")
        return False

    # Compute expected signature
    message = payload_bytes + b':' + timestamp.encode()
    expected_signature = hmac.new(
        secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(signature, expected_signature)

    if not is_valid:
        print(f"[Auth] Signature verification failed")

    return is_valid


class SpecialistAgent(BaseAgent):
    """Base specialist agent with HTTP server for orchestrator communication"""

    # Rate limiting: max requests per second (per specialist instance)
    REQUEST_RATE_LIMIT = 10  # Allow 10 requests/sec

    def __init__(self, specialist_id: str, role: str, budget: Dict[str, int]):
        """
        Initialize specialist agent

        Args:
            specialist_id: Unique identifier for this specialist instance
            role: Specialist role (researcher, fetcher, etc.)
            budget: {"tokens": int, "iterations": int, "seconds": int}
        """
        super().__init__(name=f"{role}_specialist_{specialist_id}")
        self.specialist_id = specialist_id
        self.role = role
        self.budget = budget  # {tokens, iterations, seconds}

        self.tokens_used = 0
        self.iterations_used = 0
        self.start_time = datetime.now()

        # Rate limiting with token bucket algorithm
        self.request_tokens = self.REQUEST_RATE_LIMIT
        self.last_token_refill = datetime.now()

        # Flask app for HTTP communication
        self.app = Flask(f"specialist_{specialist_id}")
        self.setup_routes()

    def setup_routes(self):
        """Register HTTP endpoints for orchestrator communication"""

        @self.app.route('/execute', methods=['POST'])
        def execute_action():
            """Execute action spec and return result"""
            try:
                # RATE LIMIT: Check request rate FIRST
                allowed, rate_info = self.check_rate_limit()
                if not allowed:
                    return jsonify({
                        'status': 'failed',
                        'errors': ['Rate limit exceeded'],
                        'rate_limit': rate_info
                    }), 429  # 429 Too Many Requests

                # SECURITY: Verify HMAC signature if headers present
                signature = request.headers.get('X-Signature')
                timestamp = request.headers.get('X-Timestamp')

                if signature and timestamp:
                    # Signature provided, verify it
                    payload = request.get_data()
                    if not verify_request_signature(payload, signature, timestamp):
                        return jsonify({
                            'status': 'failed',
                            'errors': ['Invalid request signature']
                        }), 401  # 401 Unauthorized

                # VALIDATION: Check request body
                action_spec = request.json
                if not action_spec:
                    return jsonify({
                        'status': 'failed',
                        'errors': ['No action spec provided']
                    }), 400

                # VALIDATION: Check budget FIRST (before any execution)
                try:
                    self.check_budget()
                except RuntimeError as e:
                    return jsonify({
                        'status': 'failed',
                        'errors': [f'Budget exceeded: {str(e)}']
                    }), 429  # 429 Too Many Requests

                # VALIDATION: Check action type is allowed for this specialist
                action_type = action_spec.get('actionType', '').upper()
                if not action_type:
                    return jsonify({
                        'status': 'failed',
                        'errors': ['Missing actionType field']
                    }), 400

                allowed_actions = self.get_allowed_actions()
                if action_type not in allowed_actions:
                    return jsonify({
                        'status': 'failed',
                        'errors': [f'Action {action_type} not allowed for specialist role {self.role}. Allowed: {", ".join(sorted(allowed_actions))}']
                    }), 403  # 403 Forbidden

                # VALIDATION: Check required arguments
                if action_type in ['WEB_SEARCH', 'FETCH_PAGE'] and 'args' not in action_spec:
                    return jsonify({
                        'status': 'failed',
                        'errors': [f'Missing required args field for action {action_type}']
                    }), 400

                # VALIDATION: Bounds check on string fields
                objective = action_spec.get('objective', '')
                if len(objective) > 1000:
                    return jsonify({
                        'status': 'failed',
                        'errors': ['Objective field exceeds maximum length of 1000 characters']
                    }), 400

                # Now execute the action
                result = self.handle_action(action_spec)

                response_data = {
                    'status': 'completed',
                    'observations': result.get('observations', {}),
                    'artifacts': result.get('artifacts', []),
                    'tokens_used': self.tokens_used,
                    'errors': result.get('errors'),
                    'rate_limit': rate_info,
                }

                return jsonify(response_data), 200

            except RuntimeError as e:
                # Budget exceeded or constraint violation
                return jsonify({
                    'status': 'failed',
                    'errors': [str(e)]
                }), 429

            except Exception as e:
                # Unexpected error
                print(f"[{self.role}] Unexpected error in /execute: {e}")
                return jsonify({
                    'status': 'failed',
                    'errors': [f'Unexpected error: {str(e)}']
                }), 500

        @self.app.route('/status', methods=['GET'])
        def status():
            """Return specialist status and budget usage"""
            elapsed = (datetime.now() - self.start_time).total_seconds()
            return jsonify({
                'specialist_id': self.specialist_id,
                'role': self.role,
                'status': 'running',
                'tokens_used': self.tokens_used,
                'iterations_used': self.iterations_used,
                'elapsed_seconds': elapsed,
                'budget': self.budget
            }), 200

        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({'status': 'healthy'}), 200

    def check_rate_limit(self) -> tuple[bool, Dict[str, int]]:
        """
        Check rate limit using token bucket algorithm.
        Returns (allowed, rate_limit_info)
        """
        now = datetime.now()
        time_since_refill = (now - self.last_token_refill).total_seconds()

        # Refill tokens based on elapsed time
        tokens_to_add = time_since_refill * self.REQUEST_RATE_LIMIT
        if tokens_to_add > 0:
            self.request_tokens = min(
                self.REQUEST_RATE_LIMIT,
                self.request_tokens + tokens_to_add
            )
            self.last_token_refill = now

        # Check if we can serve this request
        if self.request_tokens >= 1:
            self.request_tokens -= 1
            return (True, {
                'limit': self.REQUEST_RATE_LIMIT,
                'remaining': int(self.request_tokens),
                'reset_in_seconds': int(1.0 / self.REQUEST_RATE_LIMIT),
            })
        else:
            # Rate limited
            return (False, {
                'limit': self.REQUEST_RATE_LIMIT,
                'remaining': 0,
                'retry_after_seconds': int(1.0 / self.REQUEST_RATE_LIMIT),
            })

    def get_allowed_actions(self) -> set:
        """
        Return set of allowed action types for this specialist role.
        Subclasses can override to restrict actions.

        Default: All action types are allowed.
        Overrides in subclasses define role-specific restrictions.
        """
        return {
            'WEB_SEARCH',
            'FETCH_PAGE',
            'EXTRACT_EVIDENCE',
            'GENERATE_CLAIM',
            'UPDATE_MEMORY',
            'EVALUATE_PROGRESS',
            'SYNTHESIZE_FINDINGS',
            'VALIDATE_CLAIM'
        }

    def handle_action(self, action_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an action based on its spec.
        Must be implemented by subclasses.

        Args:
            action_spec: ActionSpec from orchestrator

        Returns:
            {
                'observations': dict,
                'artifacts': list of artifact IDs,
                'errors': optional error list
            }
        """
        raise NotImplementedError(f"handle_action not implemented for {self.role}")

    def check_budget(self):
        """Check if any budget is exceeded, raise if so"""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if elapsed > self.budget['seconds']:
            raise RuntimeError(
                f"Time budget exceeded: {elapsed:.1f}s > {self.budget['seconds']}s"
            )

        if self.tokens_used > self.budget['tokens']:
            raise RuntimeError(
                f"Token budget exceeded: {self.tokens_used} > {self.budget['tokens']}"
            )

        if self.iterations_used > self.budget['iterations']:
            raise RuntimeError(
                f"Iteration budget exceeded: {self.iterations_used} > {self.budget['iterations']}"
            )

    def record_token_usage(self, tokens: int):
        """Record token usage and check budget"""
        self.tokens_used += tokens
        self.check_budget()

    def record_iteration(self):
        """Record action iteration and check budget"""
        self.iterations_used += 1
        self.check_budget()

    def run_server(self, port: int):
        """
        Run Flask server in background thread

        Args:
            port: Port number to listen on

        Returns:
            Thread reference
        """
        def run():
            self.app.run(host='127.0.0.1', port=port, debug=False, threaded=True)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread

    def get_status(self) -> Dict[str, Any]:
        """Get current specialist status"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            'specialist_id': self.specialist_id,
            'role': self.role,
            'tokens_used': self.tokens_used,
            'iterations_used': self.iterations_used,
            'elapsed_seconds': elapsed,
            'budget': self.budget
        }

    def persist_evidence(
        self,
        url: str,
        content: str = '',
        source_type: str = 'specialist_output',
        title: str = '',
        snippet: str = ''
    ) -> str:
        """Persist evidence to database with retry logic"""
        import time

        evidence_id = str(uuid.uuid4())
        content_hash = hashlib.md5(content.encode()).hexdigest() if content else ''

        # Retry logic with exponential backoff
        for attempt in range(3):
            conn = None
            try:
                conn = get_db_connection()
                if not conn:
                    if attempt < 2:
                        wait_time = 2 ** attempt
                        print(f"[Evidence] No connection available, retrying in {wait_time}s (attempt {attempt + 1}/3)")
                        time.sleep(wait_time)
                        continue
                    print(f"[Evidence] DB unavailable after 3 attempts, returning stub ID: {evidence_id}")
                    return evidence_id

                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO autonomy_evidence
                    (id, source_id, url, title, snippet, content_hash, source_type, is_public_access, retrieved_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    evidence_id,
                    str(uuid.uuid4()),  # source_id
                    url,
                    title,
                    snippet,
                    content_hash,
                    source_type,
                    True  # is_public_access
                ))
                conn.commit()
                print(f"[Evidence] Persisted: {evidence_id}")
                return evidence_id

            except Exception as e:
                if conn:
                    conn.rollback()

                # Handle specific psycopg2 errors if available
                if HAS_DB:
                    if isinstance(e, psycopg2.errors.UniqueViolation):
                        # UUID collision (extremely rare), generate new ID
                        evidence_id = str(uuid.uuid4())
                        if attempt < 2:
                            print(f"[Evidence] UUID collision, retrying with new ID")
                            continue
                        raise RuntimeError(f"Evidence ID collision after 3 attempts: {e}")

                    elif isinstance(e, psycopg2.errors.OperationalError):
                        # Connection error, retry with backoff
                        if attempt < 2:
                            wait_time = 2 ** attempt
                            print(f"[Evidence] DB operational error, retrying in {wait_time}s: {e}")
                            time.sleep(wait_time)
                            continue
                        raise RuntimeError(f"Database unavailable after 3 attempts: {e}")

                    elif isinstance(e, psycopg2.errors.InsufficientPrivilege):
                        # Permissions issue, don't retry
                        raise RuntimeError(f"Database permission denied: {e}")

                # Generic error handling
                if attempt < 2:
                    print(f"[Evidence] Unexpected error, retrying: {e}")
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Failed to persist evidence after 3 attempts: {e}")

            finally:
                if conn:
                    return_db_connection(conn)

        # Should never reach here
        raise RuntimeError(f"Evidence persistence failed unexpectedly")

    def persist_claim(
        self,
        claim_text: str,
        support_source_ids: list,
        confidence: float = 0.7,
        status: str = 'supported'
    ) -> str:
        """Persist claim to database with retry logic"""
        import time

        claim_id = str(uuid.uuid4())

        if not support_source_ids:
            print(f"[Claim] No sources provided, returning stub ID: {claim_id}")
            return claim_id

        # Retry logic with exponential backoff
        for attempt in range(3):
            conn = None
            try:
                conn = get_db_connection()
                if not conn:
                    if attempt < 2:
                        wait_time = 2 ** attempt
                        print(f"[Claim] No connection available, retrying in {wait_time}s (attempt {attempt + 1}/3)")
                        time.sleep(wait_time)
                        continue
                    print(f"[Claim] DB unavailable after 3 attempts, returning stub ID: {claim_id}")
                    return claim_id

                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO autonomy_claims
                    (id, claim_id, text, status, confidence, support_source_ids, generated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    claim_id,
                    claim_id,
                    claim_text,
                    status,
                    confidence,
                    json.dumps(support_source_ids)  # JSONB array
                ))
                conn.commit()
                print(f"[Claim] Persisted: {claim_id}")
                return claim_id

            except Exception as e:
                if conn:
                    conn.rollback()

                # Handle specific psycopg2 errors if available
                if HAS_DB:
                    if isinstance(e, psycopg2.errors.UniqueViolation):
                        # UUID collision, generate new ID
                        claim_id = str(uuid.uuid4())
                        if attempt < 2:
                            continue
                        raise RuntimeError(f"Claim ID collision after 3 attempts: {e}")

                    elif isinstance(e, psycopg2.errors.OperationalError):
                        # Connection error, retry with backoff
                        if attempt < 2:
                            wait_time = 2 ** attempt
                            print(f"[Claim] DB operational error, retrying in {wait_time}s: {e}")
                            time.sleep(wait_time)
                            continue
                        raise RuntimeError(f"Database unavailable after 3 attempts: {e}")

                    elif isinstance(e, psycopg2.errors.InsufficientPrivilege):
                        # Permissions issue
                        raise RuntimeError(f"Database permission denied: {e}")

                # Generic error handling
                if attempt < 2:
                    print(f"[Claim] Unexpected error, retrying: {e}")
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Failed to persist claim after 3 attempts: {e}")

            finally:
                if conn:
                    return_db_connection(conn)

        # Should never reach here
        raise RuntimeError(f"Claim persistence failed unexpectedly")
