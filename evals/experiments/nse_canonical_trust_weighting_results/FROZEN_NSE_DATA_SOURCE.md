# Frozen NSE Dataset Source

Source: yfinance NSE tickers, previously fetched into committed local CSV files.

The canonical test uses raw `Close`, not adjusted close. Adjusted close can be retroactively rewritten after future splits/dividends, which is a lookahead vector for historical prediction tests.

Known limitations: yfinance can differ from official NSE records; raw close is not a total-return series; this fixed index/large-cap universe does not prove behavior on illiquid, delisted, options, crypto, or commodities markets.

| Instrument | Rows Used | First Date | Last Date | Invalid Rows Dropped |
|---|---:|---:|---:|---:|
| NIFTY 50 | 507 | 2024-06-03 | 2026-06-19 | 1 |
| BANK NIFTY | 506 | 2024-06-03 | 2026-06-19 | 1 |
| RELIANCE | 510 | 2024-06-03 | 2026-06-19 | 1 |
| HDFCBANK | 510 | 2024-06-03 | 2026-06-19 | 1 |
| TCS | 510 | 2024-06-03 | 2026-06-19 | 1 |
| INFY | 510 | 2024-06-03 | 2026-06-19 | 1 |
| ICICIBANK | 510 | 2024-06-03 | 2026-06-19 | 1 |
