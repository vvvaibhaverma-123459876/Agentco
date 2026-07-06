# Release Gate Verification

Generated: 2026-07-06T04:45:11Z

| Gate | Status | Evidence |
|---|---|---|
| reachability | green | backend route registration plus real L14 runtime service/Fastify reachability tests |
| firewall | green | `/Users/Zet/anaconda3/bin/python3.13 -m pytest calibration/tests/test_ledger_immutability.py::TestFirewall -q` |
| sandbox_breach | green | `/Users/Zet/anaconda3/bin/python3.13 -m pytest selfcoding/tests/test_wall_holds.py -q` |
| credential_key_independence | green | `/Users/Zet/anaconda3/bin/python3.13 -m pytest reserve/tests/test_ed25519_signing.py reserve/tests/test_key_independence_safe.py -q` |

## Reachability Scope

Static route coverage is combined with runtime tests that persist L14 coordinator reachability ticks through Postgres.

Registered route files: 15

Missing route registrations: none

## Result

The release-blocking safety gates above are based on real commands. Reachability is green only when route registration and the L14 runtime trace both pass.
