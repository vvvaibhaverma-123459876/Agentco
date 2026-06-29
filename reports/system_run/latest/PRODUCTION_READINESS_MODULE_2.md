# Production Readiness Module 2

Date: 2026-06-26

## Scope

Closed blocker: specialist workers were served with Flask's development server.

## Result

`COMPLETE_FOR_WORKER_SERVING`

Specialist workers now default to Waitress, a production WSGI server. Flask development serving is available only by explicit `AGENTCO_SPECIALIST_SERVER=flask-dev` opt-in outside production. Production mode refuses Flask development serving.

## Evidence

Commands run:

```text
python3.13 -m pip install 'waitress>=3.0.0'
python3.13 -m pytest agents/tests/test_specialist_server_runtime.py -q
cd backend && DATABASE_URL=<local-native-postgres-dsn> npm test -- tests/team-activation.test.ts --runInBand --forceExit
```

Results:

| Check | Result |
|---|---|
| specialist runtime tests | 3 passed |
| real team activation suite | 13 passed |
| specialist subprocess startup | real Waitress-backed HTTP workers |
| Flask dev server in production | fail-closed |

## Files

| File | Change |
|---|---|
| `agents/autonomy/specialist_agent.py` | default Waitress serving; production guard against Flask dev server |
| `agents/requirements.txt` | added `waitress>=3.0.0` |
| `requirements-runtime.txt` | added `waitress>=3.0.0` |
| `agents/tests/test_specialist_server_runtime.py` | added server backend contract tests |

## Remaining Production Blockers

1. Production secret posture is still blocked by missing/dev-default secrets.
2. Local Vault is still dev-mode and must not be claimed as production Vault.
3. Researcher/fetcher specialist actions still contain simulated web-search/fetch behavior that must be replaced with real adapters or fail closed.
4. North-star benchmark remains deterministic smoke/skeleton.
5. Live web/source discovery remains dependent on external search APIs and can fail closed.
