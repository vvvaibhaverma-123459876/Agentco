# NSE Phase 1 Root Cause Investigation Results

**Date:** 2026-06-20
**Pre-registration commit hash:** `cbfbb85808d195ae6a25031925f83bc02f5fc170`
**Executable code commit hash:** `c9e5a441bcec1646c5fdcc6f044cdf8603ac6b15`
**Frozen data:** `evals/experiments/nse_data_frozen`

## Verdict

No robust held-out calibration edge was found. The STOP 2 null remains the honest interpretation: agent overconfidence and market noise dominate reasonable trust-score and weighting-curve changes.

## Overall Calibration

| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |
|---|---:|---:|---:|---:|
| MeanReversion | 506 | 46.4% | 59.7% | 13.2% |
| Regime | 506 | 47.6% | 68.8% | 21.2% |
| Technical | 506 | 36.4% | 65.2% | 28.8% |

## Held-Out Policy Screen

| Policy | Test Return | Test vs Random | Test Sharpe | Positive Days |
|---|---:|---:|---:|---:|
| random | 0.1937% | 0.0000% | 0.1216 | 72/125 |
| recency_weighted+sigmoid | 0.1712% | -0.0225% | 0.1464 | 70/125 |
| recency_weighted+dynamic_clipped | 0.1678% | -0.0259% | 0.1523 | 72/125 |
| recency_weighted+linear | 0.1596% | -0.0341% | 0.1591 | 72/125 |
| equal | 0.1531% | -0.0406% | 0.1415 | 69/125 |
| confidence_adjusted+linear | 0.1420% | -0.0517% | 0.1433 | 69/125 |
| confidence_adjusted+dynamic_clipped | 0.1397% | -0.0540% | 0.1452 | 67/125 |
| confidence_adjusted+sigmoid | 0.1357% | -0.0580% | 0.1378 | 69/125 |
| original+linear | 0.1293% | -0.0644% | 0.1245 | 69/125 |
| regime_adjusted+linear | 0.1289% | -0.0648% | 0.1355 | 69/125 |
| original+dynamic_clipped | 0.1270% | -0.0667% | 0.1283 | 69/125 |
| regime_adjusted+dynamic_clipped | 0.1249% | -0.0688% | 0.1388 | 69/125 |
| regime_adjusted+sigmoid | 0.1077% | -0.0860% | 0.1146 | 69/125 |
| original+sigmoid | 0.1033% | -0.0904% | 0.0978 | 69/125 |

## Primary Diagnostic

Calibration curves and indicator/regime buckets are in `phase1_root_cause_results.json`. The policy screen is secondary and should not be reinterpreted as a trading result.
