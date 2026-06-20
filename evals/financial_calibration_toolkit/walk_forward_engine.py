"""Small walk-forward accounting helpers."""
from __future__ import annotations

import statistics


def summarize_pnl(pnl: list[float], capital: float) -> dict[str, float | int]:
    if not pnl:
        return {"days": 0, "return_pct": 0.0, "sharpe": 0.0, "positive_days": 0}
    returns = [value / capital for value in pnl]
    std = statistics.stdev(returns) if len(returns) > 1 else 0.0
    sharpe = statistics.mean(returns) / std if std > 0 else 0.0
    return {
        "days": len(pnl),
        "return_pct": round(100.0 * sum(pnl) / capital, 4),
        "sharpe": round(sharpe, 4),
        "positive_days": sum(1 for value in pnl if value > 0),
    }


def position_from_weighted_signal(weighted_signal: float, capital: float, max_gross_pct: float = 0.05) -> float:
    raw_position = capital * weighted_signal * max_gross_pct
    return max(-max_gross_pct * capital, min(max_gross_pct * capital, raw_position))

