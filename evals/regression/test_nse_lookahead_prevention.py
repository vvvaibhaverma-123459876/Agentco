from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from scripts.nse_canonical_trust_weighting_test import load_frozen_real_data, visible_data
from scripts.nse_phase6_better_agents import compute_rsi


def test_visible_data_excludes_prediction_date_and_future_rows() -> None:
    data = load_frozen_real_data(Path("evals/experiments/nse_data_frozen"))
    prediction_date = pd.Timestamp("2026-01-15")

    for instrument, frame in data.items():
        visible = visible_data(frame, instrument, prediction_date)
        assert len(visible.frame[visible.frame["Date"] >= prediction_date]) == 0
        if len(visible.frame) > 0:
            assert visible.frame["Date"].max() < prediction_date


def test_visible_data_rejects_future_contaminated_frame() -> None:
    data = load_frozen_real_data(Path("evals/experiments/nse_data_frozen"))
    instrument, frame = next(iter(data.items()))
    prediction_date = pd.Timestamp(frame.iloc[len(frame) // 2]["Date"])
    contaminated = frame[frame["Date"] <= prediction_date].copy()

    try:
        # Bypass the slicing helper intentionally to prove the guard detects contamination.
        from scripts.nse_canonical_trust_weighting_test import VisibleMarketData

        VisibleMarketData(instrument=instrument, prediction_date=prediction_date, frame=contaminated)
    except AssertionError as exc:
        assert "LOOKAHEAD DETECTED" in str(exc)
    else:
        raise AssertionError("future-contaminated market data was accepted")


def test_rsi_flat_series_returns_neutral() -> None:
    flat_closes = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
    rsi = compute_rsi(flat_closes)
    assert rsi == 50.0, f"RSI of flat series should be 50.0 (neutral), got {rsi}"
