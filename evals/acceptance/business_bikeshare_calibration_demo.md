# Business Bikeshare Calibration Demo

## Dataset
- Source: `https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip`
- Cached file: `data/external/bike_sharing/hour.csv`
- File used: `hour.csv`
- Historical data: Capital Bikeshare hourly rentals from 2011-2012 with weather and calendar fields.

## Business Scenario
A bike-rental operator must decide before a target hour whether demand will be high enough to justify extra bikes or staff.

## Time Split
- Target timestamp: `2012-09-12 17:00:00`
- Training/history rows: `14772` rows strictly earlier than the target timestamp.
- Held-out row: exactly the target timestamp row, with `cnt` read only during resolution.

## Pre-Registered Claim
- Prediction id: `cdc75d16-b3db-4a66-8c1e-743735454788`
- Ledger hash: `032afb9afa6abace9af2126bec8cb6cf390160411ad57391a6025f7dab6d753a`
- Claim source: `uci-bike-sharing-history://data/external/bike_sharing/hour.csv?rows=before-target`
- Independent resolution source: `uci-bike-sharing-heldout://data/external/bike_sharing/hour.csv?row=target`
- Claim: total rentals `cnt` at `2012-09-12 17:00:00` will be >= `589`.
- Predicted confidence: `0.4158`
- Baseline stratum: `same hour, workingday, holiday, and weather situation`
- Comparable history rows: `301`

## Resolution
- Actual `cnt`: `925`
- Outcome: `True`
- Trust/calibration update: `0.3326` -> `0.3493`

## Circular Verification Test
- Status: rejected as unverifiable: circular resolution rejected: claim source and resolution source are the same URL (uci-bike-sharing-history://data/external/bike_sharing/hour.csv?rows=before-target)

## Credential
- Proof/credential id: `ef766227-ce04-4fbb-a136-5f598d5d69ad`
- Recompute command: `python3 reserve/tools/recompute_credential.py business-bikeshare-calibration-demo-agent`
