"""
Epistemic Reserve — public API.

Single entry point for the Reserve layer. AgentCo agents are the first
participants; any external system with access to the prediction_ledger
can call the same functions to recompute any credential independently.

Usage:
    from reserve import create_reserve_engine

    engine = create_reserve_engine(ledger=cal["ledger"], db=conn)
    cred   = engine.refresh_credential("cfo-agent")
    weight = engine.stake_weight(cred, domain="finance", horizon="short")
"""
from __future__ import annotations

from reserve.credentials.proof_of_calibration import (
    ProofOfCalibration,
    build_last_contacts,
    issue_credential,
    load_credential,
    persist_credential,
    verify_credential,
)
from reserve.decisions.weighted_decision import (
    WeightedDecision,
    persist_decision,
    resolve_question,
)
from reserve.oracle.oracle_layer import (
    MECHANICAL_AUTHORITY,
    ORACLE_MIN_WEIGHT,
    get_current_standing,
    is_qualified_oracle,
    resolve_as_mechanical,
    resolve_as_oracle,
)
from reserve.scoring.scoring_function import ReserveScore, score_agent
from reserve.staking.staking import (
    StakeRecord,
    compute_stake_weight,
    place_stake,
    register_question,
)


class ReserveEngine:
    """
    Wires the Reserve layer to a live prediction_ledger connection.

    All credential computations read directly from the DB-backed ledger,
    so they reflect the current state of resolved predictions — the same
    data any independent party would use to recompute.
    """

    def __init__(self, ledger, db):
        self._ledger = ledger
        self._db = db

    def refresh_credential(self, agent_id: str) -> ProofOfCalibration:
        """
        Recompute and persist a fresh Proof-of-Calibration credential for
        agent_id from their current resolved prediction_ledger rows.

        Returns the newly issued credential (also persisted to DB).
        """
        records = self._ledger.list_by_agent(agent_id)
        score = score_agent(records, agent_id)
        contacts = build_last_contacts(records)
        cred = issue_credential(score, contacts)
        persist_credential(cred, self._db)
        return cred

    def score(self, agent_id: str) -> ReserveScore:
        """Compute the current ReserveScore for agent_id without persisting."""
        return score_agent(self._ledger.list_by_agent(agent_id), agent_id)

    def stake_weight(
        self,
        credential: ProofOfCalibration,
        domain: str,
        horizon: str,
    ) -> float:
        """Return the stake weight for one (domain × horizon) cell."""
        return compute_stake_weight(credential, domain, horizon)

    def is_oracle(
        self,
        credential: ProofOfCalibration,
        domain: str,
        horizon: str,
    ) -> bool:
        return is_qualified_oracle(credential, domain, horizon)

    def oracle_standing(self, agent_id: str, domain: str, horizon: str) -> dict:
        return get_current_standing(agent_id, domain, horizon, self._db)

    def verify(self, credential: ProofOfCalibration) -> bool:
        return verify_credential(credential)


def create_reserve_engine(ledger, db) -> ReserveEngine:
    """
    Create a Reserve engine bound to an existing PredictionLedger and DB connection.

    Typical AgentCo wiring:
        cal    = create_calibration_engine(db=conn)
        reserve = create_reserve_engine(ledger=cal["ledger"], db=conn)
    """
    return ReserveEngine(ledger=ledger, db=db)


__all__ = [
    "ReserveEngine", "create_reserve_engine",
    "score_agent", "ReserveScore",
    "ProofOfCalibration", "issue_credential", "verify_credential",
    "persist_credential", "load_credential", "build_last_contacts",
    "StakeRecord", "compute_stake_weight", "place_stake", "register_question",
    "WeightedDecision", "resolve_question", "persist_decision",
    "resolve_as_oracle", "resolve_as_mechanical",
    "is_qualified_oracle", "get_current_standing",
    "ORACLE_MIN_WEIGHT", "MECHANICAL_AUTHORITY",
]
