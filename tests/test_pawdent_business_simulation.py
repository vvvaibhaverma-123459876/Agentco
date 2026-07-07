import argparse
import csv
import json
from pathlib import Path

import pytest

from calibration.resolution.source_independence import CircularResolutionError, validate_independent_sources
import scripts.run_pawdent_business_simulation as pawdent
from scripts.run_pawdent_business_simulation import MarketOracle, ProductState, run_simulation


@pytest.fixture(autouse=True)
def pawdent_output_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(pawdent, "ACCEPTANCE_DIR", tmp_path)
    monkeypatch.setattr(pawdent, "REPORT_PATH", tmp_path / "pawdent_business_run.md")
    monkeypatch.setattr(pawdent, "DECISIONS_PATH", tmp_path / "pawdent_agent_decisions.jsonl")
    monkeypatch.setattr(pawdent, "FINANCIALS_PATH", tmp_path / "pawdent_monthly_financials.csv")
    monkeypatch.setattr(pawdent, "CALIBRATION_PATH", tmp_path / "pawdent_calibration_ledger.csv")
    monkeypatch.setattr(pawdent, "SUMMARY_PATH", tmp_path / "pawdent_summary.json")


def _run_fast_simulation():
    args = argparse.Namespace(duration_seconds=30.0, months=36, seed=7319, no_sleep=True, no_db=True)
    return run_simulation(args)


def test_market_simulator_is_deterministic_for_same_seed():
    state = ProductState()
    oracle_a = MarketOracle(seed=123)
    oracle_b = MarketOracle(seed=123)
    signal_a = oracle_a.pre_decision_signal(7, state)
    signal_b = oracle_b.pre_decision_signal(7, state)
    assert signal_a == signal_b


def test_pre_decision_signal_excludes_future_actuals():
    signal = MarketOracle(seed=123).pre_decision_signal(4, ProductState())
    future_actual_keys = {
        "gross_revenue",
        "operating_profit",
        "cash_balance",
        "CAC",
        "active_subscribers",
        "trial_orders",
    }
    assert future_actual_keys.isdisjoint(signal)


def test_circular_verification_is_rejected():
    with pytest.raises(CircularResolutionError):
        validate_independent_sources(
            "market_oracle_pre_decision_signal:seed=1:month=1",
            "market_oracle_pre_decision_signal:seed=1:month=1",
        )


def test_no_sleep_run_produces_36_months_and_source_ids():
    summary = _run_fast_simulation()
    assert summary["months"] == 36
    assert pawdent.SUMMARY_PATH.exists()
    financial_lines = pawdent.FINANCIALS_PATH.read_text().splitlines()
    assert len(financial_lines) == 37
    assert all("market_oracle_monthly_actual:" in line for line in financial_lines[1:])


def test_decision_events_have_required_agent_fields():
    _run_fast_simulation()
    rows = [json.loads(line) for line in pawdent.DECISIONS_PATH.read_text().splitlines()]
    assert rows
    assert all(row["agent"] and row["team"] and row["call_type"] for row in rows)
    assert any(row["circular_verification_flag"] for row in rows)


def test_business_sim_writes_all_required_artifacts():
    _run_fast_simulation()
    for path in [pawdent.REPORT_PATH, pawdent.DECISIONS_PATH, pawdent.FINANCIALS_PATH, pawdent.CALIBRATION_PATH, pawdent.SUMMARY_PATH]:
        assert Path(path).exists()
        assert Path(path).stat().st_size > 0


def test_false_prediction_never_increases_trust_and_explanation_matches_real_row():
    _run_fast_simulation()
    with pawdent.CALIBRATION_PATH.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    row = next(
        r for r in rows
        if r["month"] == "1" and r["agent"] == "Growth Marketer"
    )
    assert row["outcome"] == "False"
    assert float(row["trust_after"]) <= float(row["trust_before"])
    assert row["claim"] == "Month 1 CAC will be <= 38.68."
    assert row["explanation"] == "CAC actual 56.6 > 38.68"
