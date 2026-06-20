# NSE Phases 3-5 Results

**Date:** 2026-06-20
**Pre-registration commit hash:** `5464d2df1fd3f27f7aec943c959171ef5b9b5cec`
**Executable code commit hash:** `ce7f0d4ba61b4594ad7e8eceb2e1beafc0d6f807`
**Frozen data:** `evals/experiments/nse_data_frozen`

## Verdict

Improved ML agents did not rescue the calibration edge on the available frozen NSE data.

## Aggregate

- Trust ML beats random: `2/7` instruments (`28.6%`)
- Median trust-random return: `-0.0344%`
- Costed risk-managed trust beats random: `0/7` instruments (`0.0%`)
- Median costed-risk-random return: `-0.7071%`

## Instrument Results

| Instrument | Test Days | Trust-Random | Costed Risk-Random | Trust Return | Random Return | Costed Risk Return |
|---|---:|---:|---:|---:|---:|---:|
| BANK NIFTY | 112 | -0.1320% | -0.8711% | 0.2345% | 0.3665% | -0.5046% |
| HDFCBANK | 113 | -0.0233% | -0.8013% | 0.0860% | 0.1093% | -0.6920% |
| ICICIBANK | 113 | -0.0617% | -0.7037% | 0.3234% | 0.3851% | -0.3186% |
| INFY | 113 | -0.1835% | -0.8330% | -0.5329% | -0.3494% | -1.1824% |
| NIFTY 50 | 112 | 0.1066% | -0.5503% | 0.0151% | -0.0915% | -0.6418% |
| RELIANCE | 113 | 0.0422% | -0.4917% | 0.5490% | 0.5068% | 0.0151% |
| TCS | 113 | -0.0344% | -0.7071% | -0.4753% | -0.4409% | -1.1480% |

## Test Calibration

| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |
|---|---:|---:|---:|---:|
| GradientBoosting | 789 | 50.3% | 53.5% | 3.2% |
| LogisticRegression | 789 | 47.0% | 52.4% | 5.3% |
| RegimeSpecificGradientBoosting | 789 | 48.2% | 53.5% | 5.3% |

## Blocked Items

- Paper-to-live and small-capital trading were not executed; they require brokerage integration and user authorization.
- Alternative data signals were not added because no frozen sentiment/options-flow datasets exist in the repo.
- LSTM was not implemented because the frozen sample is too small for a defensible sequence model evaluation.

Full calibration curves and per-instrument policy summaries are in `phase3_to_5_results.json`.
