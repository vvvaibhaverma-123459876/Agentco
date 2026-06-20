"""Institutional economy over abstract resources."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


class EconomyError(ValueError):
    pass


RESOURCES = {"compute_budget", "review_credits", "authority_credits", "experiment_budget", "risk_budget"}


def allocate_budget(entity_type: str, entity_id: str, resource_type: str, amount: float, allocated_by: str, db) -> str:
    if allocated_by == entity_id:
        raise EconomyError("unauthorized budget allocation rejected")
    if resource_type not in RESOURCES:
        raise EconomyError("unknown resource type")
    account_id = _account(entity_type, entity_id, resource_type, db)
    with db.cursor() as cur:
        cur.execute("UPDATE resource_accounts SET balance = balance + %s, updated_at = %s WHERE id = %s", (amount, datetime.now(timezone.utc), account_id))
        cur.execute(
            "INSERT INTO budget_allocations (id, entity_type, entity_id, resource_type, amount, allocated_by) VALUES (%s, %s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), entity_type, entity_id, resource_type, amount, allocated_by),
        )
        cur.execute(
            "INSERT INTO resource_transactions (id, account_id, transaction_type, amount, reason) VALUES (%s, %s, 'allocation', %s, 'governance allocation')",
            (str(uuid.uuid4()), account_id, amount),
        )
    return account_id


def create_output(entity_type: str, entity_id: str, output_id: str, cost: float, db) -> None:
    account_id = _account(entity_type, entity_id, "compute_budget", db)
    with db.cursor() as cur:
        cur.execute("SELECT balance, locked FROM resource_accounts WHERE id = %s", (account_id,))
        balance, locked = cur.fetchone()
        if float(balance) - float(locked) < cost:
            raise EconomyError("insufficient budget")
        cur.execute("UPDATE resource_accounts SET locked = locked + %s, updated_at = %s WHERE id = %s", (cost, datetime.now(timezone.utc), account_id))
        cur.execute(
            "INSERT INTO resource_transactions (id, account_id, transaction_type, amount, reason) VALUES (%s, %s, 'lock', %s, %s)",
            (str(uuid.uuid4()), account_id, -cost, f"output:{output_id}"),
        )


def resolve_output(entity_type: str, entity_id: str, output_id: str, cost: float, success: bool, db) -> None:
    account_id = _account(entity_type, entity_id, "compute_budget", db)
    with db.cursor() as cur:
        if success:
            cur.execute("UPDATE resource_accounts SET locked = GREATEST(locked - %s, 0), balance = balance - %s WHERE id = %s", (cost, cost, account_id))
        else:
            cur.execute("UPDATE resource_accounts SET locked = GREATEST(locked - %s, 0), balance = balance - %s WHERE id = %s", (cost, cost * 1.5, account_id))


def reward_review(entity_type: str, entity_id: str, amount: float, db) -> None:
    account_id = _account(entity_type, entity_id, "review_credits", db)
    _credit(account_id, amount, "valid_review", db)


def reward_challenge(entity_type: str, entity_id: str, amount: float, db) -> None:
    account_id = _account(entity_type, entity_id, "review_credits", db)
    _credit(account_id, amount, "valid_challenge", db)


def penalize_false_challenge(entity_type: str, entity_id: str, amount: float, db) -> None:
    account_id = _account(entity_type, entity_id, "review_credits", db)
    _credit(account_id, -abs(amount), "false_challenge", db)


def repeated_failure_reduces_budget(entity_type: str, entity_id: str, amount: float, db) -> None:
    account_id = _account(entity_type, entity_id, "risk_budget", db)
    _credit(account_id, -abs(amount), "repeated_failure", db)


def balance(entity_type: str, entity_id: str, resource_type: str, db) -> dict:
    account_id = _account(entity_type, entity_id, resource_type, db)
    with db.cursor() as cur:
        cur.execute("SELECT balance, locked FROM resource_accounts WHERE id = %s", (account_id,))
        row = cur.fetchone()
    return {"balance": float(row[0]), "locked": float(row[1])}


def _account(entity_type: str, entity_id: str, resource_type: str, db) -> str:
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM resource_accounts WHERE entity_type = %s AND entity_id = %s AND resource_type = %s",
            (entity_type, entity_id, resource_type),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        account_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO resource_accounts (id, entity_type, entity_id, resource_type) VALUES (%s, %s, %s, %s)",
            (account_id, entity_type, entity_id, resource_type),
        )
        return account_id


def _credit(account_id: str, amount: float, reason: str, db) -> None:
    with db.cursor() as cur:
        cur.execute("UPDATE resource_accounts SET balance = balance + %s, updated_at = %s WHERE id = %s", (amount, datetime.now(timezone.utc), account_id))
        cur.execute(
            "INSERT INTO resource_transactions (id, account_id, transaction_type, amount, reason) VALUES (%s, %s, 'credit', %s, %s)",
            (str(uuid.uuid4()), account_id, amount, reason),
        )
