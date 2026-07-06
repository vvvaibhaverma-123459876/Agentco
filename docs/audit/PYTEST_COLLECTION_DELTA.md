# Pytest Collection Delta

Phase 1 added root `pytest.ini` testpaths. This report accounts for the review baseline of
`741` pre-fix collected tests with `4` collection errors versus the current clean default
collection of `562` tests.

## Commands Run

```bash
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest --collect-only -q
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest --collect-only -q scripts archive provenance
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest --collect-only -q -c /dev/null
```

Current default collection exits `0` and reports `562 tests collected`.

Explicit excluded-root collection reports `176 tests collected, 1 error` when run as
`scripts archive provenance`; the error is the known import-file mismatch between:

- `scripts/test_civilization_integration.py`
- `archive/evals_regression_theater/test_civilization_integration.py`

Current no-config collection on this branch reports `742` unique node ids, not `741`.
The extra node id is explained by Phase 1's import-safety change:
`scripts/test_governance_rbac.py::test_governance_rbac` is now collectable, but it was
behind one of the original script import-time Postgres failures in the review baseline.
It remains intentionally excluded as a direct-run script probe.

## Delta Table

| directory | tests collected pre-fix | post-fix | delta | disposition |
|---|---:|---:|---:|---|
| `archive/evals_regression_theater` | 65 | 0 | 65 | INTENTIONAL-ARCHIVE (historical/theater regression artifacts; includes the conflicting `test_civilization_integration.py` basename) |
| `scripts` | 114 | 0 | 114 | INTENTIONAL-SCRIPT (direct-run governance/calibration/probe scripts; original import-time side effects caused three of the four collection errors) |
| `provenance` | 0 | 0 | 0 | INTENTIONAL-SCRIPT (excluded root checked explicitly; no pytest node ids collected) |
| **Total** | **179** | **0** | **179** |  |

## Excluded But Newly Collectable After Phase 1

| test id | reason not counted in 741 -> 562 delta | disposition |
|---|---|---|
| `scripts/test_governance_rbac.py::test_governance_rbac` | Phase 1 moved the module-level Postgres connection under direct execution, so current no-config collection sees this node id; the review baseline did not. | INTENTIONAL-SCRIPT |

## Wrongly Excluded Directories

None found. No `WRONGLY-EXCLUDED` directory was added back to `pytest.ini`.

