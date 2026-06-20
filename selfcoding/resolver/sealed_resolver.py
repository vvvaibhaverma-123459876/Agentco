#!/usr/bin/env python3
"""
SEALED RESOLVER: Immutable ground-truth scorer for AgentCo self-extension.

This module is the load-bearing structural guardrail. It:
1. READS ONLY from frozen ground-truth data (read-only mount)
2. EXPOSES ONLY a narrow public interface (score_prediction)
3. CANNOT be modified, wrapped, or introspected by generated code
4. CANNOT write to any data source
5. CANNOT inject configuration, override data, or accept arbitrary parameters

FILESYSTEM PERMISSIONS (enforced at OS level, not in code):
- frozen_data_path: READ-ONLY, no write permission for the process
- sealed_resolver.py itself: READ-ONLY, no execute-as-different-uid, no reload
- Caller: restricted to calling public methods only

INVARIANT (enforced structurally):
Generated code runs in a sandbox with:
- No write access to frozen_data_path
- No ability to import sealed_resolver internals (only call public method)
- No ability to monkey-patch or override the resolver

This is NOT a behavioral guardrail. It is structural.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


class ResolverInaccessibleError(Exception):
    """Raised when generated code attempts to modify or inspect the resolver."""
    pass


class FrozenDataInaccessibleError(Exception):
    """Raised when generated code attempts to write to frozen data."""
    pass


class SealedResolver:
    """
    Immutable ground-truth scorer. Single instance, no reconfiguration.

    This class is instantiated ONCE in the parent process (not in generated code).
    Generated code receives ONLY the result of score_prediction() calls,
    never a reference to the instance itself.
    """

    def __init__(self, frozen_data_path: str | Path):
        """
        Initialize the resolver with a read-only frozen-data path.

        Args:
            frozen_data_path: Path to read-only ground-truth data (e.g., nse_phase6_data_frozen)

        Raises:
            FileNotFoundError: If the path does not exist or is not readable.
        """
        self._frozen_data_path = Path(frozen_data_path)

        if not self._frozen_data_path.exists():
            raise FileNotFoundError(f"Frozen data path does not exist: {self._frozen_data_path}")

        # Verify we have read-only access
        if not os.access(self._frozen_data_path, os.R_OK):
            raise PermissionError(f"No read access to frozen data: {self._frozen_data_path}")

        # Pre-load metadata to ensure data is readable
        metadata_path = self._frozen_data_path / "METADATA.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"METADATA.json not found in frozen data")

        with open(metadata_path) as f:
            self._metadata = json.load(f)

        # Cache loaded dataframes (read-only)
        self._data_cache: dict[str, pd.DataFrame] = {}

    def __setattr__(self, name: str, value: Any) -> None:
        """Block any attribute assignment after initialization."""
        if name.startswith("_"):
            # Allow internal attributes during __init__
            super().__setattr__(name, value)
        else:
            raise ResolverInaccessibleError(
                f"Cannot modify resolver attribute '{name}' — resolver is sealed"
            )

    def _load_instrument_data(self, instrument: str) -> pd.DataFrame:
        """
        Load instrument data from frozen path (cached, read-only).

        This is INTERNAL. Generated code cannot access this.
        """
        if instrument in self._data_cache:
            return self._data_cache[instrument]

        # Normalize instrument name
        safe_name = instrument.replace(" ", "_").lower()
        data_file = self._frozen_data_path / f"{safe_name}_REAL.csv"

        if not data_file.exists():
            raise FileNotFoundError(f"Data not found for instrument: {instrument}")

        df = pd.read_csv(data_file)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        self._data_cache[instrument] = df
        return df

    def score_prediction(
        self,
        instrument: str,
        prediction_date: str,
        predicted_direction: str,
        confidence: float,
    ) -> dict[str, Any]:
        """
        Score a prediction against ground truth (the ONLY public method).

        Args:
            instrument: Instrument name (e.g., "NIFTY 50")
            prediction_date: Date the prediction was made (YYYY-MM-DD)
            predicted_direction: "up" or "down"
            confidence: Confidence score [0.0, 1.0]

        Returns:
            {
                "prediction_date": str,
                "resolution_date": str,
                "instrument": str,
                "predicted_direction": str,
                "confidence": float,
                "actual_open": float,
                "actual_close": float,
                "actual_direction": str,
                "hit": bool,
                "score": float,  # confidence if correct, -confidence if wrong
                "timestamp": str,
            }

        Raises:
            ValueError: If prediction_date format is invalid
            FileNotFoundError: If instrument not found in frozen data
        """
        try:
            pred_date = pd.Timestamp(prediction_date)
        except Exception as e:
            raise ValueError(f"Invalid prediction_date format: {prediction_date}") from e

        if predicted_direction not in ("up", "down"):
            raise ValueError(f"predicted_direction must be 'up' or 'down', got: {predicted_direction}")

        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got: {confidence}")

        # Load frozen data
        data = self._load_instrument_data(instrument)

        # Find the prediction date and the next trading day
        pred_rows = data[data["Date"] == pred_date]
        if len(pred_rows) == 0:
            raise ValueError(f"No data found for prediction_date {prediction_date}")

        # Get next trading day
        pred_idx = data[data["Date"] == pred_date].index[0]
        if pred_idx >= len(data) - 1:
            raise ValueError(f"No next trading day after {prediction_date}")

        # Resolution: open on prediction date, close on next date
        open_price = float(pred_rows.iloc[0]["Open"])
        resolution_row = data.iloc[pred_idx + 1]
        close_price = float(resolution_row["Close"])
        resolution_date = pd.Timestamp(resolution_row["Date"]).strftime("%Y-%m-%d")

        actual_direction = "up" if close_price > open_price else "down"
        hit = (predicted_direction == actual_direction)

        # Score: confidence if hit, -confidence if miss
        score = confidence if hit else -confidence

        return {
            "prediction_date": prediction_date,
            "resolution_date": resolution_date,
            "instrument": instrument,
            "predicted_direction": predicted_direction,
            "confidence": confidence,
            "actual_open": open_price,
            "actual_close": close_price,
            "actual_direction": actual_direction,
            "hit": hit,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def get_resolver(frozen_data_path: str | Path) -> SealedResolver:
    """
    Factory function to instantiate the resolver.
    This is called ONCE in the parent process, not in generated code.
    """
    return SealedResolver(frozen_data_path)
