from __future__ import annotations

from datetime import datetime, timezone

from calibration.ledger.prediction_ledger import PredictionRecord
from reserve.scoring.scoring_function import score_agent
from reserve.tools.recompute_credential import recompute


def test_public_raw_row_recomputation_matches_runtime_scoring_without_keys():
    agent_id = "key-independence-safe-agent"
    rows = [
        {
            "prediction_id": "p1",
            "probability": 0.75,
            "resolved_outcome": True,
            "domain": "testing",
            "horizon_class": "short",
            "consequence": False,
            "resolved_at": datetime.now(timezone.utc),
            "post_hoc": False,
        },
        {
            "prediction_id": "p2",
            "probability": 0.60,
            "resolved_outcome": False,
            "domain": "testing",
            "horizon_class": "short",
            "consequence": True,
            "resolved_at": datetime.now(timezone.utc),
            "post_hoc": False,
        },
    ]
    records = [
        PredictionRecord(
            prediction_id=row["prediction_id"],
            claim=f"claim {row['prediction_id']}",
            probability=row["probability"],
            confidence_basis={"basis": "safe-key-independence-test"},
            producing_agent_id=agent_id,
            producing_prompt_version="test",
            resolution_criterion="external outcome",
            resolution_date=row["resolved_at"],
            ground_truth_source="external_test",
            horizon_class=row["horizon_class"],
            domain=row["domain"],
            claim_type="forecast",
            created_at=row["resolved_at"],
            post_hoc=row["post_hoc"],
            resolved=True,
            resolved_outcome=row["resolved_outcome"],
            resolved_at=row["resolved_at"],
            resolved_by_service="resolution_service",
        )
        for row in rows
    ]
    for row, record in zip(rows, records):
        setattr(record, "consequence", row["consequence"])

    runtime_score = score_agent(records, agent_id)
    public_score = recompute(rows)

    assert public_score["algorithm"] == runtime_score.algorithm
    assert public_score["total_sample_count"] == runtime_score.total_sample_count
    assert abs(public_score["overall_log_score"] - runtime_score.overall_log_score) < 1e-12
    assert abs(public_score["overall_brier_score"] - runtime_score.overall_brier_score) < 1e-12
    assert len(public_score["cells"]) == len(runtime_score.cells)

    public_cell = public_score["cells"][0]
    runtime_cell = runtime_score.cells[0]
    assert public_cell["domain"] == runtime_cell.domain
    assert public_cell["horizon_class"] == runtime_cell.horizon_class
    assert abs(public_cell["weighted_log_score"] - runtime_cell.weighted_log_score) < 1e-12
    assert abs(public_cell["weighted_brier_score"] - runtime_cell.weighted_brier_score) < 1e-12
    assert public_cell["sample_count"] == runtime_cell.sample_count
