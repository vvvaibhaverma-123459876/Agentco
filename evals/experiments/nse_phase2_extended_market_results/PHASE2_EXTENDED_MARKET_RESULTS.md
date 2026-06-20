# NSE Phase 2 Extended Market Results

**Date:** 2026-06-20
**Pre-registration commit hash:** `6374dbc4d85511377ca9f79a57069ea979d45539`
**Executable code commit hash:** `f0fe7178ab57acde256b9ca3b65055969acd688b`
**Frozen data:** `evals/experiments/nse_data_frozen`

## Verdict

The STOP 2 null generalizes across the currently frozen NSE spot/large-cap set.

## Scope Limitations

- No frozen 2020-2024 real data present; older-window tests not run.
- No frozen options, crypto, or commodities data present; alternative-asset tests not run.
- No 1,500+ trading-day frozen sample present; longer-sample test not run.

## Aggregate

- Eligible market-window cells: `49`
- Original B beats P: `16` cells (`32.6%`)
- Median B-P return: `-0.0388%`
- Phase 1 candidate beats P: `19` cells (`38.8%`)
- Median candidate-P return: `-0.0769%`

## Market-Window Cells

| Instrument | Window | Days | B-P | Candidate-P | B Beats P |
|---|---:|---:|---:|---:|---:|
| BANK NIFTY | full | 505 | -0.1496% | -0.1932% | False |
| BANK NIFTY | first_half | 252 | -0.1736% | -0.1701% | False |
| BANK NIFTY | second_half | 253 | -0.0298% | -0.0769% | False |
| BANK NIFTY | block_01 | 126 | -0.0974% | -0.0859% | False |
| BANK NIFTY | block_02 | 126 | 0.0117% | 0.0037% | True |
| BANK NIFTY | block_03 | 126 | 0.0953% | 0.1054% | True |
| BANK NIFTY | block_04 | 126 | -0.1274% | -0.1848% | False |
| HDFCBANK | full | 509 | -0.2004% | -0.3042% | False |
| HDFCBANK | first_half | 254 | -0.0358% | -0.0855% | False |
| HDFCBANK | second_half | 255 | 0.2059% | 0.1518% | True |
| HDFCBANK | block_01 | 126 | -0.1760% | -0.2925% | False |
| HDFCBANK | block_02 | 126 | 0.1008% | 0.1787% | True |
| HDFCBANK | block_03 | 126 | 0.1278% | 0.0934% | True |
| HDFCBANK | block_04 | 126 | 0.4745% | 0.4405% | True |
| ICICIBANK | full | 509 | -0.5877% | -0.3750% | False |
| ICICIBANK | first_half | 254 | -0.1463% | -0.0671% | False |
| ICICIBANK | second_half | 255 | -0.2100% | -0.0765% | False |
| ICICIBANK | block_01 | 126 | -0.3740% | -0.2913% | False |
| ICICIBANK | block_02 | 126 | -0.0904% | -0.0884% | False |
| ICICIBANK | block_03 | 126 | 0.1249% | 0.1985% | True |
| ICICIBANK | block_04 | 126 | 0.2900% | 0.3454% | True |
| INFY | full | 509 | 0.0953% | 0.1332% | True |
| INFY | first_half | 254 | 0.4028% | 0.4711% | True |
| INFY | second_half | 255 | -0.1248% | -0.1551% | False |
| INFY | block_01 | 126 | -0.2059% | -0.1561% | False |
| INFY | block_02 | 126 | -0.0022% | -0.0058% | False |
| INFY | block_03 | 126 | 0.0113% | 0.0161% | True |
| INFY | block_04 | 126 | -0.1124% | -0.1619% | False |
| NIFTY 50 | full | 506 | -0.2799% | -0.2327% | False |
| NIFTY 50 | first_half | 253 | -0.1092% | -0.1162% | False |
| NIFTY 50 | second_half | 253 | 0.0533% | 0.1075% | True |
| NIFTY 50 | block_01 | 126 | -0.0262% | -0.0323% | False |
| NIFTY 50 | block_02 | 126 | -0.0760% | -0.0769% | False |
| NIFTY 50 | block_03 | 126 | 0.2257% | 0.2378% | True |
| NIFTY 50 | block_04 | 126 | -0.0388% | 0.0003% | False |
| RELIANCE | full | 509 | -0.1475% | -0.2191% | False |
| RELIANCE | first_half | 254 | -0.0124% | 0.0302% | False |
| RELIANCE | second_half | 255 | 0.2104% | 0.0962% | True |
| RELIANCE | block_01 | 126 | -0.0127% | -0.0148% | False |
| RELIANCE | block_02 | 126 | -0.3134% | -0.2681% | False |
| RELIANCE | block_03 | 126 | 0.0664% | 0.0508% | True |
| RELIANCE | block_04 | 126 | 0.1098% | 0.0217% | True |
| TCS | full | 509 | -0.2196% | -0.4226% | False |
| TCS | first_half | 254 | -0.0326% | 0.0119% | False |
| TCS | second_half | 255 | -0.2017% | -0.4491% | False |
| TCS | block_01 | 126 | -0.2658% | -0.1645% | False |
| TCS | block_02 | 126 | -0.0947% | -0.1555% | False |
| TCS | block_03 | 126 | -0.0323% | -0.0832% | False |
| TCS | block_04 | 126 | -0.4723% | -0.6581% | False |

## Overall Calibration

| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |
|---|---:|---:|---:|---:|
| MeanReversion | 3556 | 44.5% | 63.0% | 18.5% |
| Regime | 3556 | 46.4% | 67.3% | 20.9% |
| Technical | 3556 | 37.0% | 64.7% | 27.8% |

Calibration curves by instrument and agent are in `phase2_extended_market_results.json`.
