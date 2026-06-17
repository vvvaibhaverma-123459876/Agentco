#!/usr/bin/env python3
"""
Epistemic Reserve — Reference Recomputer (standalone, no secret required).

Usage:
    python3 reserve/tools/recompute_credential.py <agent_id> [dsn]

Reads RAW resolved prediction_ledger rows from Postgres and recomputes the
Reserve score using ONLY the published deterministic scoring function.  The
resulting score can be compared field-for-field against any stored credential
to prove (or disprove) that the stored credential was produced honestly.

This script intentionally has ZERO dependency on RESERVE_SIGNING_KEY,
RESERVE_PRIVATE_KEY, or any private state held by the operator.  It proves
third-party recomputability: the score is determined solely by public ledger
rows + the published algorithm.

Exit codes:
    0  — recomputation succeeded (score printed to stdout)
    1  — usage error or Postgres connection failure
    2  — no eligible predictions found for agent_id
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Published algorithm (copy of reserve/scoring/scoring_function.py — kept
# deliberately self-contained so this script has no import-path dependency).
# ---------------------------------------------------------------------------
EPSILON = 1e-9
CONSEQUENCE_WEIGHT_MULTIPLIER = 2.0
ALGORITHM = "log_score+brier/hardness_weighted/v1"


def _hardness(p: float) -> float:
    return 2.0 * p * (1.0 - p)


def _weight(p: float, consequence: bool) -> float:
    cw = CONSEQUENCE_WEIGHT_MULTIPLIER if consequence else 1.0
    return _hardness(p) * cw


def _log_score(p: float, outcome: bool) -> float:
    p = max(min(p, 1.0 - EPSILON), EPSILON)
    return math.log(p) if outcome else math.log(1.0 - p)


def _brier_score(p: float, outcome: bool) -> float:
    o = 1.0 if outcome else 0.0
    return (p - o) ** 2


# ---------------------------------------------------------------------------
# Raw DB read — returns plain dicts, no ORM.
# ---------------------------------------------------------------------------
def _fetch_rows(dsn: str, agent_id: str) -> list[dict]:
    try:
        import psycopg2
    except ImportError:
        sys.exit("psycopg2 not installed — run: pip install psycopg2-binary")
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT prediction_id, probability, resolved_outcome,
                   domain, horizon_class,
                   COALESCE(consequence, FALSE) AS consequence,
                   resolved_at, post_hoc
            FROM prediction_ledger
            WHERE producing_agent_id = %s
              AND resolved = TRUE
              AND resolved_outcome IS NOT NULL
              AND (post_hoc IS NULL OR post_hoc = FALSE)
            ORDER BY resolved_at
            """,
            (agent_id,),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Pure recomputation — mirrors score_agent() using raw dicts.
# ---------------------------------------------------------------------------
def recompute(rows: list[dict]) -> dict:
    cells_map: dict[tuple, list] = {}
    for r in rows:
        key = (r["domain"], r["horizon_class"])
        cells_map.setdefault(key, []).append(r)

    cells = []
    for (domain, horizon_class), cell_rows in sorted(cells_map.items()):
        total_w = 0.0
        sum_wlog = 0.0
        sum_wbrier = 0.0
        sum_sharp = 0.0
        for r in cell_rows:
            p = float(r["probability"])
            o = bool(r["resolved_outcome"])
            c = bool(r.get("consequence", False))
            w = _weight(p, c)
            total_w += w
            sum_wlog += w * _log_score(p, o)
            sum_wbrier += w * _brier_score(p, o)
            sum_sharp += p * (1.0 - p)
        n = len(cell_rows)
        cells.append({
            "domain": domain,
            "horizon_class": horizon_class,
            "weighted_log_score": sum_wlog / total_w if total_w > 0 else 0.0,
            "weighted_brier_score": sum_wbrier / total_w if total_w > 0 else 0.0,
            "sharpness": sum_sharp / n if n > 0 else 0.0,
            "sample_count": n,
            "total_weight": total_w,
        })

    non_empty = [c for c in cells if c["sample_count"] > 0]
    overall_log = (
        sum(c["weighted_log_score"] for c in non_empty) / len(non_empty)
        if non_empty else 0.0
    )
    overall_brier = (
        sum(c["weighted_brier_score"] for c in non_empty) / len(non_empty)
        if non_empty else 0.0
    )
    return {
        "algorithm": ALGORITHM,
        "cells": cells,
        "overall_log_score": overall_log,
        "overall_brier_score": overall_brier,
        "total_sample_count": sum(c["sample_count"] for c in cells),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    agent_id = sys.argv[1]
    dsn = sys.argv[2] if len(sys.argv) > 2 else os.environ.get(
        "AGENTCO_TEST_DATABASE_URL",
        os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5433/agentco?host=/tmp"),
    )

    rows = _fetch_rows(dsn, agent_id)
    if not rows:
        print(f"No eligible resolved predictions found for agent_id={agent_id!r}", file=sys.stderr)
        sys.exit(2)

    score = recompute(rows)
    print(json.dumps({
        "agent_id": agent_id,
        "recomputed_at": datetime.now(timezone.utc).isoformat(),
        "source": "public prediction_ledger rows — no secret required",
        "score": score,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
