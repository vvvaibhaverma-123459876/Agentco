# Verifiable Calibration Demo

## What was claimed
Python 3.12.0 was released on October 2, 2023.

## How it was checked
The claim was sourced from `https://www.python.org/downloads/release/python-3120/` and resolved against independent source `https://docs.python.org/3/whatsnew/3.12.html`.

## What happened
Prediction `cc57d9d2-0d19-4c14-bcd5-e369e4088b2c` resolved TRUE. Trust moved from `0.7280` to `0.7644`.

## Why this matters
The same-source circular check was deliberately attempted and rejected before it could count as verification.

## Credential
Credential `fe8b51cb-f6ae-4aac-bf27-84f548c50376` was issued. Recompute it with:

`python3 reserve/tools/recompute_credential.py demo-calibration-agent`

Circular check status: flagged as unverifiable: circular resolution rejected: claim source and resolution source are the same URL (https://www.python.org/downloads/release/python-3120)
