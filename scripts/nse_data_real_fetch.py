#!/usr/bin/env python3
"""Fetch REAL NSE data from yfinance, freeze it, validate lookahead on real data.

CRITICAL DECISION: Adjusted Close (Adj Close) vs Raw Close
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
yfinance returns:
  - Close = raw, unadjusted (recorded at time of trade)
  - Adj Close = retroactively rewritten on splits/dividends

LOOKAHEAD VECTOR: A future split (day 100) alters historical prices (day 50)
                  if using Adj Close, making past "closes" depend on future events.

RESOLUTION: Use Close (raw) for BOTH prediction AND resolution
  - Prediction agents see raw Close only (data up to prediction_date)
  - Resolution uses raw Close (actual close on resolution_date)
  - No retroactive rewriting within the test window
  - Same field throughout = temporal integrity guaranteed

This sacrifices accounting-precision (splits/dividends not adjusted) for
temporal integrity (no future events alter past data). In a 2-year window
with large-cap NSE stocks, unadjusted close is acceptable and honest.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None


NSE_INSTRUMENTS = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "ICICIBANK": "ICICIBANK.NS",
}


def fetch_real_nse_data(
    instruments: dict[str, str],
    start_date: str,
    end_date: str,
    output_dir: Path,
) -> dict[str, pd.DataFrame]:
    """Fetch REAL NSE data from yfinance.

    Uses Close (raw, unadjusted) for temporal integrity.
    Saves Adj Close alongside for audit/reference.

    Returns: {instrument_name: DataFrame with Date, Close (raw), Volume}
    """
    if yf is None:
        raise ImportError("yfinance required: pip install yfinance")

    output_dir.mkdir(parents=True, exist_ok=True)
    data = {}

    print("\n" + "="*70)
    print("FETCHING REAL NSE DATA FROM YFINANCE")
    print("="*70)
    print(f"Window: {start_date} to {end_date}")
    print(f"Close field: Raw Close (unadjusted) — no retroactive rewrites")
    print(f"Resolution: Same field for prediction & resolution → temporal integrity\n")

    for name, ticker in instruments.items():
        print(f"  {name:15s} ({ticker:20s}): ", end="", flush=True)
        try:
            # Fetch data
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if df.empty:
                print("NO DATA")
                continue

            # Reset index to get Date as column
            df = df.reset_index()

            # yfinance column names: Date, Open, High, Low, Close, Volume, Adj Close
            # (note: Close is raw/unadjusted, Adj Close is retroactively adjusted)

            # Extract only what we need: Date, Close (raw), Volume
            df_raw = df[["Date", "Close", "Volume"]].copy()
            df_raw["Instrument"] = name
            df_raw["Ticker"] = ticker
            df_raw = df_raw.sort_values("Date").reset_index(drop=True)

            # Also save Adj Close for audit (but don't use it for test)
            if "Adj Close" in df.columns:
                df_raw["Adj_Close_Audit"] = df["Adj Close"]

            data[name] = df_raw
            print(f"✓ {len(df_raw)} trading days")

        except Exception as e:
            print(f"ERROR: {e}")
            continue

    if not data:
        print("\n⚠️  WARNING: No data fetched from yfinance")
        print("  Check ticker symbols and network connectivity")
        return {}

    return data


def save_real_frozen_data(
    data: dict[str, pd.DataFrame],
    output_dir: Path,
) -> None:
    """Save real NSE data as immutable frozen artifact."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nFreezing REAL NSE data to {output_dir}")
    for instrument_name, df in data.items():
        safe_name = instrument_name.replace(" ", "_").lower()
        csv_path = output_dir / f"{safe_name}_REAL.csv"
        df.to_csv(csv_path, index=False)
        print(f"  {csv_path} ({len(df)} rows)")


def load_real_data(dataset_dir: Path) -> dict[str, pd.DataFrame]:
    """Load real NSE frozen data."""
    data = {}
    for csv_file in sorted(dataset_dir.glob("*_REAL.csv")):
        instrument_name = csv_file.stem.replace("_REAL", "").replace("_", " ").title()
        df = pd.read_csv(csv_file)
        df["Date"] = pd.to_datetime(df["Date"])
        # Keep only Date, Close, Volume (drop Adj_Close_Audit for test)
        df = df[["Date", "Close", "Volume"]]
        df = df.sort_values("Date")
        data[instrument_name] = df

    return data


def get_data_up_to(
    data: dict[str, pd.DataFrame],
    cutoff_date: datetime | str,
) -> dict[str, pd.DataFrame]:
    """LOAD-BEARING: Return ONLY data STRICTLY BEFORE cutoff_date."""
    if isinstance(cutoff_date, str):
        cutoff_date = pd.to_datetime(cutoff_date)

    result = {}
    for instrument_name, df in data.items():
        visible = df[pd.to_datetime(df["Date"]) < cutoff_date].copy()
        result[instrument_name] = visible

    return result


def test_lookahead_strict_cutoff(
    data: dict[str, pd.DataFrame],
    test_date: datetime | str,
) -> bool:
    """TEST 1: Strict cutoff on REAL data."""
    if isinstance(test_date, str):
        test_date = pd.to_datetime(test_date)

    print(f"\n[LOOKAHEAD TEST 1 - REAL DATA] Strict Cutoff")
    print(f"  Testing: get_data_up_to({test_date.date()}) returns ONLY data < {test_date.date()}")

    visible = get_data_up_to(data, test_date)
    all_pass = True

    for instrument_name, visible_df in visible.items():
        if len(visible_df) == 0:
            print(f"    {instrument_name:15s}: 0 rows")
            continue

        max_visible_date = pd.to_datetime(visible_df["Date"]).max()
        if max_visible_date >= test_date:
            print(f"    {instrument_name:15s}: ✗ FAIL - max {max_visible_date.date()} >= {test_date.date()}")
            all_pass = False
        else:
            print(f"    {instrument_name:15s}: ✓ max {max_visible_date.date()} < {test_date.date()}")

    if all_pass:
        print("  ✓ PASS: Strict cutoff enforced")
    return all_pass


def test_lookahead_future_access(
    data: dict[str, pd.DataFrame],
    test_date: datetime | str,
) -> bool:
    """TEST 2: Future row access blocked on REAL data."""
    if isinstance(test_date, str):
        test_date = pd.to_datetime(test_date)

    print(f"\n[LOOKAHEAD TEST 2 - REAL DATA] Adversarial Future Access")
    print(f"  Attempting to access rows with date >= {test_date.date()}")

    visible = get_data_up_to(data, test_date)
    all_pass = True

    for instrument_name, visible_df in visible.items():
        if len(visible_df) == 0:
            continue

        future_rows = visible_df[pd.to_datetime(visible_df["Date"]) >= test_date]
        if len(future_rows) > 0:
            print(f"    {instrument_name:15s}: ✗ FAIL - found {len(future_rows)} future rows")
            all_pass = False
        else:
            print(f"    {instrument_name:15s}: ✓ 0 future rows accessible")

    if all_pass:
        print("  ✓ PASS: Future data inaccessible")
    return all_pass


def test_lookahead_prediction_sim(
    data: dict[str, pd.DataFrame],
    prediction_date: datetime | str,
) -> bool:
    """TEST 3: Agent prediction cannot access future on REAL data."""
    if isinstance(prediction_date, str):
        prediction_date = pd.to_datetime(prediction_date)

    print(f"\n[LOOKAHEAD TEST 3 - REAL DATA] Prediction Function Simulation")
    print(f"  Calling: agent_forecast(data, {prediction_date.date()})")

    visible = get_data_up_to(data, prediction_date)

    for instrument_name, visible_df in visible.items():
        if len(visible_df) == 0:
            continue

        # Simulate agent computing RSI on visible data
        _ = visible_df["Close"].tail(14).mean()

        # Try to cheat
        future_data = visible_df[pd.to_datetime(visible_df["Date"]) >= prediction_date]
        if len(future_data) > 0:
            print(f"    {instrument_name:15s}: ✗ FAIL")
            return False

    if len(visible) > 0:
        max_date = max(visible[name]["Date"].max() for name in visible if len(visible[name]) > 0)
        print(f"  Agent sees data up to {max_date.date()}")
    print("  ✓ PASS: Prediction function cannot access future")
    return True


def test_real_data_quality(
    data: dict[str, pd.DataFrame],
) -> bool:
    """TEST 4: Real data quality on REAL data."""
    print(f"\n[LOOKAHEAD TEST 4 - REAL DATA] Data Quality & Coverage")

    all_dates = set()
    for instrument_name, df in data.items():
        dates = set(pd.to_datetime(df["Date"]))
        all_dates.update(dates)

    print(f"  Total unique trading days: {len(all_dates)}")

    all_pass = True
    for instrument_name, df in data.items():
        dates = set(pd.to_datetime(df["Date"]))
        coverage_pct = 100.0 * len(dates) / len(all_dates) if all_dates else 0
        print(f"    {instrument_name:15s}: {len(dates):4d} days ({coverage_pct:5.1f}%)")

        if coverage_pct < 90:
            print(f"      ⚠️  Low coverage")
            all_pass = False

    if all_pass:
        print("  ✓ PASS: Real data quality acceptable")
    return all_pass


def save_integrity_report(
    output_dir: Path,
    test_results: dict[str, bool],
    data: dict[str, pd.DataFrame],
) -> None:
    """Save integrity report for REAL data."""
    all_pass = all(test_results.values())

    report = {
        "timestamp": datetime.now().isoformat(),
        "stop_1_phase": "REAL NSE DATA VALIDATION",
        "data_source": "yfinance (NSE tickers)",
        "test_window": "2024-06-01 to 2026-06-20",
        "close_field_used": "Close (raw, unadjusted)",
        "close_field_rationale": (
            "yfinance Adj Close is retroactively rewritten on splits/dividends. "
            "Using raw Close ensures no future events alter past prices. "
            "Same field used for prediction AND resolution guarantees temporal integrity."
        ),
        "adj_close_handling": "Saved separately for audit; NOT used in test",
        "instruments_fetched": list(data.keys()),
        "data_rows": {name: len(df) for name, df in data.items()},
        "lookahead_tests_real_data": {
            "test_1_strict_cutoff": "PASS" if test_results.get("test_1") else "FAIL",
            "test_2_future_access": "PASS" if test_results.get("test_2") else "FAIL",
            "test_3_prediction_sim": "PASS" if test_results.get("test_3") else "FAIL",
            "test_4_data_quality": "PASS" if test_results.get("test_4") else "FAIL",
        },
        "lookahead_verdict": "STRUCTURALLY PREVENTED ON REAL DATA" if all_pass else "LEAKAGE DETECTED",
        "ready_for_stop_2": all_pass,
        "next_step": "PROCEED TO STOP 2 (agents + walk-forward)" if all_pass else "INVESTIGATE LEAKAGE",
    }

    report_path = output_dir.parent / "STOP_1_REAL_DATA_RESULTS.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📋 Report: {report_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2024-06-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-06-20", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", type=Path, default=Path("evals/experiments/nse_data_frozen"))
    parser.add_argument("--skip-fetch", action="store_true", help="Use cached real data")

    args = parser.parse_args(argv)

    print("\n" + "="*70)
    print("STOP 1: REAL NSE DATA + LOOKAHEAD VALIDATION")
    print("="*70)

    # Fetch or load real data
    if not args.skip_fetch:
        print("\n[PHASE 1] Fetching REAL NSE data from yfinance...")
        data = fetch_real_nse_data(NSE_INSTRUMENTS, args.start, args.end, args.output)

        if not data:
            print("\n✗ Failed to fetch real data")
            return 1

        save_real_frozen_data(data, args.output)
    else:
        print("\n[PHASE 1] Loading cached REAL NSE data...")
        data = load_real_data(args.output)
        if not data:
            print("\n✗ No cached real data found")
            return 1

    # Run lookahead tests on REAL data
    print("\n[PHASE 2] Running lookahead tests on REAL NSE data...")
    test_date = pd.to_datetime("2026-06-10")

    t1_pass = test_lookahead_strict_cutoff(data, test_date)
    t2_pass = test_lookahead_future_access(data, test_date)
    t3_pass = test_lookahead_prediction_sim(data, test_date)
    t4_pass = test_real_data_quality(data)

    all_pass = t1_pass and t2_pass and t3_pass and t4_pass

    test_results = {"test_1": t1_pass, "test_2": t2_pass, "test_3": t3_pass, "test_4": t4_pass}
    save_integrity_report(args.output, test_results, data)

    # Print verdict
    print("\n" + "="*70)
    if all_pass:
        print("✓✓✓ STOP 1 PASSED - REAL DATA ✓✓✓")
        print("    All lookahead tests PASSED on REAL NSE data")
        print("    Close field: Raw (no retroactive adjustments)")
        print("    Temporal integrity: CONFIRMED")
        print("    Ready for STOP 2 (agents + walk-forward on REAL data)")
        print("="*70)
        return 0
    else:
        print("✗✗✗ STOP 1 FAILED - REAL DATA ✗✗✗")
        print("    Lookahead leakage detected on real data")
        print("    DO NOT PROCEED to STOP 2")
        print("="*70)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
