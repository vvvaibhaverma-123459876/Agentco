from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from runtime.evaluation.schema import EvaluationRecord


def calibration_metrics(records: tuple[EvaluationRecord, ...]) -> dict[str, Any]:
    if not records:
        raise ValueError("cannot compute calibration metrics without evaluation records")
    total = len(records)
    brier_score = sum(record.brier_score for record in records) / total
    abstentions = sum(1 for record in records if record.abstained)
    unsupported = sum(1 for record in records if record.failure_category == "unsupported_claim")
    disagreements = sum(1 for record in records if record.failure_category == "evaluator_disagreement")
    buckets: dict[str, dict[str, float | int]] = {}
    ece = 0.0
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        upper = round(lower + 0.2, 1)
        label = f"{lower:.1f}-{upper:.1f}"
        bucket_records = [
            record for record in records
            if lower <= record.predicted_confidence <= upper and (upper == 1.0 or record.predicted_confidence < upper)
        ]
        if not bucket_records:
            buckets[label] = {"count": 0, "accuracy": 0.0, "avg_confidence": 0.0}
            continue
        accuracy = sum(record.correctness_score for record in bucket_records) / len(bucket_records)
        avg_confidence = sum(record.predicted_confidence for record in bucket_records) / len(bucket_records)
        ece += (len(bucket_records) / total) * abs(avg_confidence - accuracy)
        buckets[label] = {
            "count": len(bucket_records),
            "accuracy": round(accuracy, 6),
            "avg_confidence": round(avg_confidence, 6),
        }
    by_failure = Counter(record.failure_category for record in records)
    return {
        "record_count": total,
        "brier_score": round(brier_score, 6),
        "expected_calibration_error": round(ece, 6),
        "accuracy_by_confidence_bucket": buckets,
        "abstention_rate": round(abstentions / total, 6),
        "unsupported_claim_rate": round(unsupported / total, 6),
        "evaluator_disagreement_rate": round(disagreements / total, 6),
        "failure_categories": dict(sorted(by_failure.items())),
    }


def records_as_dicts(records: tuple[EvaluationRecord, ...]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]
