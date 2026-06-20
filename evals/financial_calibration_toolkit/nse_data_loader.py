"""Frozen NSE data loading helpers."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_frozen_real_instruments(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Load `*_REAL.csv` files without network access."""
    instruments = {}
    for csv_path in sorted(data_dir.glob("*_REAL.csv")):
        name = csv_path.stem.replace("_REAL", "").replace("_", " ").upper()
        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"])
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
        df = df[["Date", "Close", "Volume"]].dropna(subset=["Date", "Close"])
        instruments[name] = df.sort_values("Date").reset_index(drop=True)
    return instruments


def visible_before(df: pd.DataFrame, prediction_date: pd.Timestamp) -> pd.DataFrame:
    """Return data strictly before `prediction_date` and assert no leakage."""
    visible = df[df["Date"] < prediction_date].copy()
    if len(visible) > 0:
        assert visible["Date"].max() < prediction_date, "LOOKAHEAD DETECTED"
    return visible

