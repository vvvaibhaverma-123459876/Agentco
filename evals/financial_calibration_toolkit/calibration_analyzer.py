"""Calibration diagnostics."""
from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any


def calibration_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize hit rate, confidence, and confidence-bin calibration by agent."""
    output = {}
    for agent in sorted({r["agent"] for r in records}):
        subset = [r for r in records if r["agent"] == agent]
        hit_rate = sum(1 for r in subset if r["hit"]) / len(subset)
        avg_confidence = statistics.mean(r["confidence"] for r in subset)
        output[agent] = {
            "predictions": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "calibration_error": round(avg_confidence - hit_rate, 4),
            "confidence_bins": confidence_bins(subset),
        }
    return output


def confidence_bins(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        confidence = record["confidence"]
        if confidence < 0.55:
            bucket = "0.45-0.55"
        elif confidence < 0.65:
            bucket = "0.55-0.65"
        elif confidence < 0.75:
            bucket = "0.65-0.75"
        else:
            bucket = "0.75-1.00"
        buckets[bucket].append(record)

    rows = []
    for bucket, subset in sorted(buckets.items()):
        hit_rate = sum(1 for r in subset if r["hit"]) / len(subset)
        avg_confidence = statistics.mean(r["confidence"] for r in subset)
        rows.append({
            "bucket": bucket,
            "n": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "calibration_error": round(avg_confidence - hit_rate, 4),
        })
    return rows

