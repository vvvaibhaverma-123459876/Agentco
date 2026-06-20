#!/usr/bin/env python3
"""Fetch and freeze NSE historical data as the external verifier dataset.

Design principles:
- Data is frozen locally as git-committed artifact (immutable)
- Train/test split is TEMPORAL, never random
- Lookahead prevention: agents can only see data up to prediction date
- Source is documented; limitations stated honestly
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None


# NSE tickers with .NS suffix for yfinance
NSE_INSTRUMENTS = {
    "NIFTY 50": "^NSEI",  # Index
    "BANK NIFTY": "^NSEBANK",  # Index
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "ICICIBANK": "ICICIBANK.NS",
}

# NSE holidays (sample; would need full holiday calendar in production)
NSE_HOLIDAYS_2024_2025 = {
    "2025-01-26",  # Republic Day
    "2025-03-08",  # Maha Shivaratri
    "2025-03-25",  # Holi
    "2025-03-29",  # Good Friday
    "2025-04-11",  # Eid ul-Fitr
    "2025-04-17",  # Ram Navami
    "2025-04-21",  # Mahavir Jayanti
    "2025-05-23",  # Buddha Purnima
    "2025-07-17",  # Muharram
    "2025-08-15",  # Independence Day
    "2025-08-27",  # Janmashtami
    "2025-09-16",  # Milad un-Nabi
    "2025-10-02",  # Gandhi Jayanti
    "2025-10-12",  # Dussehra
    "2025-11-01",  # Diwali
    "2025-11-05",  # Diwali (Day 2, normally open but reduced hours)
    "2025-11-25",  # Guru Nanak Jayanti
    "2025-12-25",  # Christmas
}


def fetch_nse_data(
    instruments: dict[str, str],
    start_date: str,
    end_date: str,
    output_dir: Path,
) -> dict[str, pd.DataFrame]:
    """Fetch historical NSE data and save locally.

    Args:
        instruments: {name: ticker} mapping
        start_date: "YYYY-MM-DD" format
        end_date: "YYYY-MM-DD" format
        output_dir: directory to save frozen data

    Returns:
        {instrument_name: DataFrame} with columns [Date, Open, High, Low, Close, Volume]
    """
    if yf is None:
        raise ImportError("yfinance not installed. Install with: pip install yfinance")

    output_dir.mkdir(parents=True, exist_ok=True)
    data = {}

    print(f"Fetching NSE data from {start_date} to {end_date}")
    print("Source: yfinance (NSE tickers with .NS suffix)")
    print("Limitations: yfinance data may have small discrepancies from NSE official source")
    print("Production use: validate against NSE official site periodically\n")

    for name, ticker in instruments.items():
        print(f"  Fetching {name} ({ticker})...", end=" ", flush=True)
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df.empty:
                print(f"EMPTY (ticker may not exist or no data for period)")
                continue

            # Standardize columns
            df = df.reset_index()
            if "Date" not in df.columns:
                df.columns = ["Date"] + list(df.columns[1:])

            df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
            df["Instrument"] = name
            df["Ticker"] = ticker
            df = df.sort_values("Date").reset_index(drop=True)

            data[name] = df
            print(f"✓ {len(df)} trading days")

        except Exception as e:
            print(f"ERROR: {e}")

    return data


def save_frozen_dataset(
    data: dict[str, pd.DataFrame],
    output_dir: Path,
    metadata: dict[str, Any],
) -> Path:
    """Save frozen dataset as CSV files + metadata JSON.

    Each instrument gets its own CSV. Metadata records source, fetch date, limitations.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save each instrument
    for instrument_name, df in data.items():
        safe_name = instrument_name.replace(" ", "_").lower()
        csv_path = output_dir / f"{safe_name}.csv"
        df.to_csv(csv_path, index=False)
        print(f"Saved {csv_path}")

    # Save metadata
    metadata["frozen_at"] = datetime.now().isoformat()
    metadata["instruments"] = {
        name: {
            "rows": len(df),
            "date_range": f"{df['Date'].min()} to {df['Date'].max()}",
        }
        for name, df in data.items()
    }

    metadata_path = output_dir / "METADATA.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved {metadata_path}")

    return output_dir


def load_frozen_dataset(dataset_dir: Path) -> dict[str, pd.DataFrame]:
    """Load frozen dataset from committed files.

    Returns: {instrument_name: DataFrame}
    """
    data = {}
    for csv_file in dataset_dir.glob("*.csv"):
        instrument_name = csv_file.stem.replace("_", " ").title()
        df = pd.read_csv(csv_file)
        df["Date"] = pd.to_datetime(df["Date"])
        data[instrument_name] = df.sort_values("Date")

    return data


def get_trading_days_up_to(
    data: dict[str, pd.DataFrame],
    cutoff_date: datetime | str,
) -> list[datetime]:
    """Get list of trading days on or before cutoff date.

    Used for lookahead prevention: agents can only "see" data up to cutoff.
    """
    if isinstance(cutoff_date, str):
        cutoff_date = pd.to_datetime(cutoff_date)

    # Collect all trading days from all instruments
    all_dates = set()
    for df in data.values():
        dates = pd.to_datetime(df["Date"])
        all_dates.update(dates[dates <= cutoff_date])

    return sorted(list(all_dates))


def get_data_up_to(
    data: dict[str, pd.DataFrame],
    cutoff_date: datetime | str,
) -> dict[str, pd.DataFrame]:
    """Extract data visible to an agent at cutoff_date.

    LOOKAHEAD PREVENTION: Agents can ONLY see data strictly before cutoff.
    Data ON cutoff_date is excluded (can't predict today using today's data).
    """
    if isinstance(cutoff_date, str):
        cutoff_date = pd.to_datetime(cutoff_date)

    result = {}
    for instrument_name, df in data.items():
        # Strictly before cutoff
        visible = df[pd.to_datetime(df["Date"]) < cutoff_date].copy()
        result[instrument_name] = visible

    return result


def test_lookahead_prevention(
    data: dict[str, pd.DataFrame],
    test_date: datetime | str,
) -> bool:
    """Test that lookahead is prevented: data at test_date is NOT visible.

    This is the critical integrity test.
    """
    if isinstance(test_date, str):
        test_date = pd.to_datetime(test_date)

    visible = get_data_up_to(data, test_date)

    for instrument_name, visible_df in visible.items():
        if len(visible_df) == 0:
            continue

        max_visible_date = pd.to_datetime(visible_df["Date"]).max()
        if max_visible_date >= test_date:
            print(f"LOOKAHEAD LEAK DETECTED in {instrument_name}:")
            print(f"  test_date: {test_date}")
            print(f"  max visible: {max_visible_date}")
            return False

    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2024-06-01",
                       help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-06-20",
                       help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", type=Path,
                       default=Path("evals/experiments/nse_data/frozen"),
                       help="Output directory for frozen dataset")
    parser.add_argument("--test-lookahead", action="store_true",
                       help="Run lookahead prevention test")

    args = parser.parse_args(argv)

    # Fetch data
    data = fetch_nse_data(NSE_INSTRUMENTS, args.start, args.end, args.output)

    if not data:
        print("No data fetched. Exiting.")
        return 1

    # Save frozen dataset
    metadata = {
        "source": "yfinance (NSE tickers with .NS suffix)",
        "source_limitations": [
            "yfinance data may have small timing discrepancies vs NSE official",
            "Adjusted close vs raw close handling may differ from NSE",
            "For production: validate against NSE official site",
        ],
        "test_window_start": args.start,
        "test_window_end": args.end,
        "instruments_fetched": list(NSE_INSTRUMENTS.keys()),
    }

    save_frozen_dataset(data, args.output, metadata)

    # Test lookahead prevention
    if args.test_lookahead:
        print(f"\nTesting lookahead prevention...")
        test_date = pd.to_datetime("2026-06-15")
        if test_lookahead_prevention(data, test_date):
            print(f"✓ Lookahead prevention test PASSED")
            print(f"  Data strictly before {test_date} is isolated correctly")
        else:
            print(f"✗ Lookahead prevention test FAILED")
            return 1

    print("\n✓ Frozen dataset ready for walk-forward testing")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
