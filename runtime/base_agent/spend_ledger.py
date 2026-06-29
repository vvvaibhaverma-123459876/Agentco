from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any


class SpendLedgerUnavailable(RuntimeError):
    pass


class SpendLedgerBlocked(RuntimeError):
    pass


def _stable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    return value


def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(_stable(value), separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True)
class SpendReservation:
    reservation_id: str
    account_id: str
    amount: int


class PostgresSpendLedger:
    def __init__(
        self,
        *,
        dsn: str,
        agent_id: str,
        model_name: str = "unknown",
        max_tokens: int,
    ) -> None:
        if not dsn:
            raise SpendLedgerUnavailable("DATABASE_URL or AGENTCO_TEST_DATABASE_URL is required when spend ledger is enabled")
        self._dsn = dsn
        self._agent_id = agent_id
        self._model_name = model_name
        self._max_tokens = max_tokens
        self.actor_id: str | None = None
        self.account_id: str | None = None

    def initialize(self) -> None:
        psycopg2 = self._psycopg2()
        conn = psycopg2.connect(self._dsn)
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                actor_id = self._ensure_actor(cur)
                account_id = self._ensure_account(cur, actor_id)
            conn.commit()
            self.actor_id = actor_id
            self.account_id = account_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def allocate(self, amount: int, *, idempotency_key: str, reason: str = "llm token allocation") -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._require_initialized()
        psycopg2 = self._psycopg2()
        conn = psycopg2.connect(self._dsn)
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                existing = self._find_transaction(cur, idempotency_key)
                if existing:
                    conn.commit()
                    return
                self._lock_account(cur)
                event_id = self._write_event_and_audit(
                    cur,
                    event_type="resource.credited",
                    object_type="resource_account",
                    object_id=self.account_id,
                    payload={
                        "account_id": self.account_id,
                        "actor_id": self.actor_id,
                        "transaction_type": "credit",
                        "amount": amount,
                        "reason": reason,
                        "idempotency_key": idempotency_key,
                    },
                    input_summary=f"credit llm_tokens amount={amount}",
                    output_summary="credit recorded",
                )
                cur.execute(
                    """
                    UPDATE civilization_resource_accounts
                       SET balance = balance + %s,
                           updated_at = now()
                     WHERE id = %s
                    RETURNING balance
                    """,
                    [amount, self.account_id],
                )
                balance_after = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO civilization_resource_transactions
                      (account_id, actor_id, transaction_type, amount, balance_after, reason, idempotency_key, event_log_id)
                    VALUES (%s,%s,'credit',%s,%s,%s,%s,%s)
                    """,
                    [self.account_id, self.actor_id, amount, balance_after, reason, idempotency_key, event_id],
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def reserve(self, amount: int, *, idempotency_key: str, ttl_seconds: int) -> SpendReservation:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._require_initialized()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        psycopg2 = self._psycopg2()
        conn = psycopg2.connect(self._dsn)
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, account_id, amount
                      FROM civilization_resource_reservations
                     WHERE idempotency_key = %s
                    """,
                    [idempotency_key],
                )
                row = cur.fetchone()
                if row:
                    conn.commit()
                    return SpendReservation(str(row[0]), str(row[1]), int(row[2]))

                account = self._lock_account(cur)
                available = Decimal(account["balance"]) - Decimal(account["reserved_balance"])
                if available < amount:
                    raise SpendLedgerBlocked(f"insufficient available llm_tokens balance: available={available}, requested={amount}")
                reservation_id = str(uuid.uuid4())
                event_id = self._write_event_and_audit(
                    cur,
                    event_type="resource.reserved",
                    object_type="resource_reservation",
                    object_id=reservation_id,
                    payload={
                        "reservation_id": reservation_id,
                        "account_id": self.account_id,
                        "actor_id": self.actor_id,
                        "amount": amount,
                        "available_before": available,
                        "idempotency_key": idempotency_key,
                        "expires_at": expires_at.isoformat(),
                    },
                    input_summary=f"reserve llm_tokens amount={amount}",
                    output_summary=f"reservation_id={reservation_id}",
                )
                cur.execute(
                    """
                    UPDATE civilization_resource_accounts
                       SET reserved_balance = reserved_balance + %s,
                           updated_at = now()
                     WHERE id = %s
                    """,
                    [amount, self.account_id],
                )
                cur.execute(
                    """
                    INSERT INTO civilization_resource_reservations
                      (id, account_id, actor_id, amount, status, reason, idempotency_key, expires_at, event_log_id)
                    VALUES (%s,%s,%s,%s,'reserved','llm call reservation',%s,%s,%s)
                    """,
                    [reservation_id, self.account_id, self.actor_id, amount, idempotency_key, expires_at, event_id],
                )
            conn.commit()
            return SpendReservation(reservation_id, self.account_id or "", amount)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def settle(self, reservation_id: str, actual_tokens: int, *, idempotency_key: str) -> None:
        if actual_tokens < 0:
            raise ValueError("actual_tokens must be non-negative")
        self._require_initialized()
        psycopg2 = self._psycopg2()
        conn = psycopg2.connect(self._dsn)
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                existing = self._find_transaction(cur, idempotency_key)
                if existing:
                    conn.commit()
                    return
                reservation = self._lock_reservation(cur, reservation_id)
                if reservation["status"] == "settled":
                    conn.commit()
                    return
                if reservation["status"] != "reserved":
                    raise SpendLedgerBlocked(f"reservation is not reserved: {reservation['status']}")
                reserved_amount = int(reservation["amount"])
                if actual_tokens > reserved_amount:
                    raise SpendLedgerBlocked(f"actual token usage {actual_tokens} exceeds reserved amount {reserved_amount}")
                account = self._lock_account(cur)
                next_balance = Decimal(account["balance"]) - Decimal(actual_tokens)
                next_reserved = Decimal(account["reserved_balance"]) - Decimal(reserved_amount)
                if next_balance < 0 or next_reserved < 0:
                    raise SpendLedgerBlocked("ledger balance would become negative during settlement")
                event_id = self._write_event_and_audit(
                    cur,
                    event_type="resource.reservation_settled",
                    object_type="resource_reservation",
                    object_id=reservation_id,
                    payload={
                        "reservation_id": reservation_id,
                        "account_id": self.account_id,
                        "actor_id": self.actor_id,
                        "reserved_amount": reserved_amount,
                        "actual_tokens": actual_tokens,
                        "balance_after": next_balance,
                        "reserved_balance_after": next_reserved,
                        "idempotency_key": idempotency_key,
                    },
                    input_summary=f"settle llm_tokens actual={actual_tokens}",
                    output_summary=f"balance_after={next_balance}",
                )
                cur.execute(
                    """
                    UPDATE civilization_resource_accounts
                       SET balance = %s,
                           reserved_balance = %s,
                           updated_at = now()
                     WHERE id = %s
                    """,
                    [next_balance, next_reserved, self.account_id],
                )
                cur.execute(
                    """
                    INSERT INTO civilization_resource_transactions
                      (account_id, actor_id, transaction_type, amount, balance_after, reason, idempotency_key, event_log_id)
                    VALUES (%s,%s,'debit',%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    [self.account_id, self.actor_id, actual_tokens, next_balance, f"settled spend reservation {reservation_id}", idempotency_key, event_id],
                )
                transaction_id = cur.fetchone()[0]
                cur.execute(
                    """
                    UPDATE civilization_resource_reservations
                       SET status = 'settled',
                           settled_transaction_id = %s,
                           updated_at = now()
                     WHERE id = %s
                    """,
                    [transaction_id, reservation_id],
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def release(self, reservation_id: str) -> None:
        self._require_initialized()
        psycopg2 = self._psycopg2()
        conn = psycopg2.connect(self._dsn)
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                reservation = self._lock_reservation(cur, reservation_id)
                if reservation["status"] != "reserved":
                    conn.commit()
                    return
                account = self._lock_account(cur)
                amount = int(reservation["amount"])
                next_reserved = Decimal(account["reserved_balance"]) - Decimal(amount)
                if next_reserved < 0:
                    raise SpendLedgerBlocked("ledger reserved balance would become negative during release")
                self._write_event_and_audit(
                    cur,
                    event_type="resource.reservation_released",
                    object_type="resource_reservation",
                    object_id=reservation_id,
                    payload={
                        "reservation_id": reservation_id,
                        "account_id": self.account_id,
                        "actor_id": self.actor_id,
                        "amount": amount,
                        "reserved_balance_after": next_reserved,
                    },
                    input_summary=f"release llm_tokens amount={amount}",
                    output_summary=f"reserved_balance_after={next_reserved}",
                )
                cur.execute(
                    """
                    UPDATE civilization_resource_accounts
                       SET reserved_balance = %s,
                           updated_at = now()
                     WHERE id = %s
                    """,
                    [next_reserved, self.account_id],
                )
                cur.execute(
                    """
                    UPDATE civilization_resource_reservations
                       SET status = 'released',
                           updated_at = now()
                     WHERE id = %s
                    """,
                    [reservation_id],
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_actor(self, cur: Any) -> str:
        cur.execute(
            """
            SELECT id FROM actors
             WHERE actor_type = 'agent' AND name = %s AND status = 'active'
            """,
            [self._agent_id],
        )
        row = cur.fetchone()
        if row:
            actor_id = str(row[0])
        else:
            actor_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO actors (id, actor_type, name, metadata_json)
                VALUES (%s,'agent',%s,%s::jsonb)
                """,
                [actor_id, self._agent_id, json.dumps({"created_by": "SpendGuardrail"})],
            )
        cur.execute(
            """
            INSERT INTO agent_identities (actor_id, agent_key, model_name, version)
            VALUES (%s,%s,%s,'spend-guardrail')
            ON CONFLICT (actor_id) DO NOTHING
            """,
            [actor_id, self._agent_id, self._model_name],
        )
        return actor_id

    def _ensure_account(self, cur: Any, actor_id: str) -> str:
        cur.execute(
            """
            INSERT INTO civilization_resource_accounts (owner_actor_id, resource_type, unit)
            VALUES (%s,'llm_tokens','tokens')
            ON CONFLICT (owner_actor_id, resource_type)
            DO UPDATE SET updated_at = civilization_resource_accounts.updated_at
            RETURNING id
            """,
            [actor_id],
        )
        return str(cur.fetchone()[0])

    def _lock_account(self, cur: Any) -> dict[str, Any]:
        cur.execute(
            """
            SELECT id, balance, reserved_balance, status
              FROM civilization_resource_accounts
             WHERE id = %s
             FOR UPDATE
            """,
            [self.account_id],
        )
        row = cur.fetchone()
        if not row:
            raise SpendLedgerUnavailable("spend ledger account does not exist")
        if row[3] != "active":
            raise SpendLedgerBlocked(f"spend ledger account is not active: {row[3]}")
        return {"id": str(row[0]), "balance": row[1], "reserved_balance": row[2], "status": row[3]}

    def _lock_reservation(self, cur: Any, reservation_id: str) -> dict[str, Any]:
        cur.execute(
            """
            SELECT id, account_id, amount, status
              FROM civilization_resource_reservations
             WHERE id = %s
             FOR UPDATE
            """,
            [reservation_id],
        )
        row = cur.fetchone()
        if not row:
            raise SpendLedgerBlocked(f"reservation not found: {reservation_id}")
        if str(row[1]) != self.account_id:
            raise SpendLedgerBlocked("reservation belongs to a different spend account")
        return {"id": str(row[0]), "account_id": str(row[1]), "amount": row[2], "status": row[3]}

    def _find_transaction(self, cur: Any, idempotency_key: str) -> bool:
        cur.execute(
            "SELECT 1 FROM civilization_resource_transactions WHERE idempotency_key = %s",
            [idempotency_key],
        )
        return cur.fetchone() is not None

    def _write_event_and_audit(
        self,
        cur: Any,
        *,
        event_type: str,
        object_type: str,
        object_id: str | None,
        payload: dict[str, Any],
        input_summary: str,
        output_summary: str,
    ) -> str:
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        correlation_id = str(uuid.uuid4())
        cur.execute("SELECT event_hash FROM event_log ORDER BY occurred_at DESC, id DESC LIMIT 1")
        previous_event = cur.fetchone()
        prev_event_hash = previous_event[0] if previous_event else "0" * 64
        event_fields = {
            "id": event_id,
            "event_type": event_type,
            "actor_id": self.actor_id,
            "institution_id": None,
            "object_type": object_type,
            "object_id": object_id,
            "occurred_at": timestamp,
            "payload": payload,
            "correlation_id": correlation_id,
            "causation_id": None,
            "signature": None,
            "prev_hash": prev_event_hash,
        }
        event_hash = hashlib.sha256((prev_event_hash + _canonical(event_fields)).encode()).hexdigest()
        cur.execute(
            """
            INSERT INTO event_log
              (id, event_type, actor_id, object_type, object_id, occurred_at,
               payload, correlation_id, prev_hash, event_hash)
            VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
            """,
            [
                event_id,
                event_type,
                self.actor_id,
                object_type,
                object_id,
                timestamp,
                json.dumps(_stable(payload), sort_keys=True),
                correlation_id,
                prev_event_hash,
                event_hash,
            ],
        )

        cur.execute("SELECT chain_hash FROM decision_log WHERE chain_hash <> '' ORDER BY timestamp DESC, log_id DESC LIMIT 1")
        previous_audit = cur.fetchone()
        prev_audit_hash = previous_audit[0] if previous_audit else "0" * 64
        log_id = str(uuid.uuid4())
        audit_fields = {
            "log_id": log_id,
            "timestamp": timestamp,
            "prev_hash": prev_audit_hash,
            "agent_id": self.actor_id,
            "action_type": "event_published",
            "input_summary": input_summary,
            "output_summary": output_summary,
            "confidence_score": 1,
            "risk_level": "low",
            "human_approved": False,
            "human_approver_id": None,
            "downstream_events": [event_id],
            "session_id": correlation_id,
        }
        chain_hash = hashlib.sha256((prev_audit_hash + json.dumps(audit_fields, separators=(",", ":"))).encode()).hexdigest()
        cur.execute(
            """
            INSERT INTO decision_log
              (log_id, agent_id, action_type, input_summary, output_summary,
               confidence_score, risk_level, human_approved, downstream_events,
               session_id, timestamp, chain_hash, prev_hash)
            VALUES (%s,%s,'event_published',%s,%s,1.0,'low',false,%s::uuid[],%s,%s,%s,%s)
            """,
            [log_id, self.actor_id, input_summary, output_summary, [event_id], correlation_id, timestamp, chain_hash, prev_audit_hash],
        )
        return event_id

    def _require_initialized(self) -> None:
        if not self.actor_id or not self.account_id:
            raise SpendLedgerUnavailable("spend ledger has not been initialized")

    @staticmethod
    def _psycopg2() -> Any:
        try:
            import psycopg2
        except Exception as exc:
            raise SpendLedgerUnavailable("psycopg2 is required when spend ledger is enabled") from exc
        return psycopg2


def configured_spend_ledger(agent_id: str, model_name: str, max_tokens: int) -> PostgresSpendLedger | None:
    if os.environ.get("AGENTCO_SPEND_LEDGER_ENABLED") != "1":
        return None
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("AGENTCO_TEST_DATABASE_URL")
    ledger = PostgresSpendLedger(dsn=dsn or "", agent_id=agent_id, model_name=model_name, max_tokens=max_tokens)
    ledger.initialize()
    return ledger
