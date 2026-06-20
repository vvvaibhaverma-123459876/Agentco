#!/usr/bin/env python3
"""
Legitimate code execution tests on varied goals.

Demonstrates that the sandbox now allows realistic generated code to execute
while maintaining security guarantees.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from selfcoding.sandbox.run_generated import run_generated_code, setup_sandbox


def test_legitimate_code(context, name: str, code: str) -> bool:
    """Test code for a legitimate goal."""
    result = run_generated_code(code, context)

    if result["success"]:
        return True
    else:
        print(f"✗ {name}: {result['error']}")
        return False


def main() -> int:
    """Run legitimate code on varied goals."""
    context = setup_sandbox()
    passed = 0

    # Test goals
    goals = [
        ("Momentum detector", """
import numpy as np
def momentum_agent(returns):
    avg = np.mean(returns)
    return {"direction": "up" if avg > 0 else "down", "confidence": min(abs(avg) * 10, 0.95)}
pred = momentum_agent([0.02, 0.015, 0.01])
r = score_prediction("NIFTY 50", "2024-10-21", pred["direction"], pred["confidence"])
result = {"agent": "momentum", "direction": pred["direction"], "score": float(r["score"])}
"""),
        ("Mean reversion detector", """
import numpy as np
def mean_rev(distances):
    avg = (distances[0] + distances[1]) / 2
    direction = "up" if avg < 0 else "down"
    confidence = min(abs(avg) * 0.05, 0.95)
    return {"direction": direction, "confidence": confidence}
pred = mean_rev([-50, -45])
r = score_prediction("NIFTY 50", "2024-10-21", pred["direction"], pred["confidence"])
result = {"agent": "mean_reversion", "score": float(r["score"])}
"""),
        ("Multi-agent comparison", """
import numpy as np
import pandas as pd
def agent_momentum(returns):
    avg = np.mean(returns)
    return {"direction": "up" if avg > 0 else "down", "confidence": min(abs(avg) * 5, 0.9)}
r1 = score_prediction("NIFTY 50", "2024-10-21", "up", 0.75)
r2 = score_prediction("NIFTY 50", "2024-10-21", "down", 0.65)
result = {"predictions": 2, "winner": "up" if r1["score"] > r2["score"] else "down"}
"""),
        ("Statistical analysis", """
import numpy as np
import statistics
data = [24956, 24900, 24950, 25000, 24850]
np_mean = float(np.mean(data))
py_mean = statistics.mean(data)
r = score_prediction("NIFTY 50", "2024-10-21", "up" if np_mean > 24900 else "down", 0.7)
result = {"np_mean": np_mean, "py_mean": py_mean, "score": float(r["score"])}
"""),
        ("Data processing", """
import pandas as pd
import numpy as np
dates = ["2024-10-21", "2024-10-22", "2024-10-23"]
closes = [24956, 24900, 24950]
df = pd.DataFrame({"date": dates, "close": closes})
df["returns"] = df["close"].pct_change()
avg_return = df["returns"].mean()
r = score_prediction("NIFTY 50", "2024-10-21", "up" if avg_return > 0 else "down", 0.7)
result = {"avg_return": float(avg_return), "rows": len(df), "score": float(r["score"])}
"""),
        ("Complex orchestration", """
import numpy as np
agents = [
    {"name": "a", "prediction": "up", "confidence": 0.8},
    {"name": "b", "prediction": "down", "confidence": 0.6},
]
up_votes = sum(a["confidence"] for a in agents if a["prediction"] == "up")
down_votes = sum(a["confidence"] for a in agents if a["prediction"] == "down")
direction = "up" if up_votes > down_votes else "down"
r = score_prediction("NIFTY 50", "2024-10-21", direction, 0.7)
result = {"agents": len(agents), "direction": direction, "score": float(r["score"])}
"""),
        ("JSON handling", """
import json
predictions_json = json.dumps([
    {"agent": "mom", "direction": "up", "score": 0.75},
    {"agent": "rev", "direction": "down", "score": 0.5}
])
parsed = json.loads(predictions_json)
r = score_prediction("NIFTY 50", "2024-10-21", parsed[0]["direction"], 0.8)
result = {"predictions": len(parsed), "score": float(r["score"])}
"""),
        ("Collections", """
import numpy as np
from collections import Counter
agent_outputs = ["up", "up", "down", "up", "down"]
vote_counts = Counter(agent_outputs)
winner = vote_counts.most_common(1)[0][0]
confidence = vote_counts[winner] / len(agent_outputs)
r = score_prediction("NIFTY 50", "2024-10-21", winner, float(confidence))
result = {"winner": winner, "score": float(r["score"])}
"""),
        ("Datetime handling", """
import datetime
today = datetime.datetime.now()
prediction_date = today.strftime("%Y-%m-%d")
month = today.month
direction = "up" if month % 2 == 0 else "down"
r = score_prediction("NIFTY 50", "2024-10-21", direction, 0.5)
result = {"date": prediction_date, "score": float(r["score"])}
"""),
        ("Math operations", """
import math
import numpy as np
values = [24956, 24900, 24950]
log_values = [math.log(v) for v in values]
mean_log = np.mean(log_values)
direction = "up" if mean_log > math.log(24900) else "down"
r = score_prediction("NIFTY 50", "2024-10-21", direction, 0.7)
result = {"mean_log": float(mean_log), "score": float(r["score"])}
"""),
    ]

    print("=" * 80)
    print("LEGITIMATE CODE EXECUTION TESTS")
    print("=" * 80)

    for name, code in goals:
        if test_legitimate_code(context, name, code):
            passed += 1
            print(f"✓ {name}")

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed}/{len(goals)} goals succeeded")
    print("=" * 80)

    return 0 if passed == len(goals) else 1


if __name__ == "__main__":
    sys.exit(main())
