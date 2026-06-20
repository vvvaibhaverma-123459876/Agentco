# Financial Calibration Toolkit

Reusable modules live under `evals/financial_calibration_toolkit`:

- `nse_data_loader.py`: frozen data loading and strict past-only slicing
- `calibration_analyzer.py`: confidence-bin calibration summaries
- `trust_scoring.py`: trust score snapshots
- `walk_forward_engine.py`: P&L and position helpers

The toolkit is intentionally small and dependency-light so future experiments can reuse the integrity structure without inheriting NSE-specific scripts.
