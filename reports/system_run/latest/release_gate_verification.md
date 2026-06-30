# Release Gate Verification

Generated: 2026-06-30T09:07:48Z

| Gate | Status | Evidence |
|---|---|---|
| reachability | partial | backend HTTP route registration check; scope is partial, not full L14 graph |
| firewall | green | `/Users/Zet/anaconda3/bin/python3.13 -m pytest calibration/tests/test_ledger_immutability.py::TestFirewall -q` |
| sandbox_breach | green | `/Users/Zet/anaconda3/bin/python3.13 selfcoding/tests/test_wall_holds.py` |
| credential_key_independence | green | `/Users/Zet/anaconda3/bin/python3.13 -m pytest reserve/tests/test_ed25519_signing.py reserve/tests/test_key_independence_safe.py -q` |

## Reachability Scope

This proves enabled backend route clusters and the core L14 runtime reachability endpoints are registered. It does not prove full L14 coordinator reachability for every internal service.

Registered route files: 14

Missing route registrations: none

## Result

The release-blocking safety gates above are based on real commands. Reachability remains `partial` until a full L14 coordinator service graph and runtime trace are implemented.
