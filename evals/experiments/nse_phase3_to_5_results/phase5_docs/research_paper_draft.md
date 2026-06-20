# Fair Testing of Calibration-Weighted Decision-Making on Real Markets

## Abstract

AgentCo tested whether calibration-weighted decision-making improves paper-trading outcomes on frozen real NSE market data. Across pre-registered STOP 2, Phase 1, Phase 2, and Phase 3-4 tests, trust-weighting did not reliably outperform random-placebo weighting. The dominant diagnostic was persistent overconfidence: agents expressed confidence materially above realized hit rates.

## Method

The framework used frozen data, strict walk-forward feature construction, pre-registration before execution, random-placebo controls, and calibration curves as the primary diagnostic. Later phases added trained ML agents, chronological train/validation/test splits, transaction costs, and risk controls.

## Result

No deployable edge was found. Where paper improvements appeared in isolated windows, they failed the locked cross-market consistency criteria or were not robust after costs and risk controls.

## Interpretation

The result does not falsify calibration-weighted decision-making in general. It shows that on this frozen NSE sample, with these agents and limited data, calibration signal is not separable from market noise.
