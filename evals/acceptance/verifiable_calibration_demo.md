# Verifiable Calibration Demo

## What was claimed
Python 3.12.0 was released on October 2, 2023.

## How it was checked
The claim was sourced from `https://www.python.org/downloads/release/python-3120/` and resolved against independent source `https://docs.python.org/3/whatsnew/3.12.html`.

## What happened
Prediction `cd7eb19b-1cbb-472e-85c5-043c0db8db1a` resolved TRUE. Trust moved from `0.7280` to `0.7644`.

## Why this matters
The same-source circular check was deliberately attempted and rejected before it could count as verification.

## Credential
Credential `495b0cdb-ded3-43ea-948a-864b8ed6e4cc` was issued. Recompute it with:

`python3 reserve/tools/recompute_credential.py demo-calibration-agent`

Circular check status: flagged as unverifiable: circular resolution rejected: claim source and resolution source are the same URL (https://www.python.org/downloads/release/python-3120)
