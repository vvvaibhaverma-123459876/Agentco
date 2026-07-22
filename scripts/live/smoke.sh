#!/usr/bin/env bash
# End-to-end smoke test for the local live stack (docker-compose.live.yml).
#
# Proves the running product works, not merely that containers started:
#   - backend liveness + readiness (readiness transitively proves Postgres,
#     Kafka, and real-provider posture),
#   - API auth posture (401 without key, 200 with),
#   - frontend up AND its server-side proxy actually reaching the backend,
#   - a real write: registers a smoke-test actor through the public API,
#   - civilization state readable (operator overview),
#   - LLM endpoint reachability from inside the backend container (reported,
#     but a down LLM does not fail the smoke — the product boots without it).
set -uo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -f .env.live ]]; then
  echo "FATAL: .env.live not found — run 'make live-up' first" >&2
  exit 1
fi
API_KEY="$(grep '^AGENTCO_API_KEY=' .env.live | cut -d= -f2-)"
LLM_BASE_URL="$(grep '^LLM_BASE_URL=' .env.live | cut -d= -f2-)"

PASS=0
FAIL=0
declare -a RESULTS

check() { # name, expected, actual
  if [[ "$2" == "$3" ]]; then
    RESULTS+=("PASS  $1"); PASS=$((PASS+1))
  else
    RESULTS+=("FAIL  $1 (expected $2, got $3)"); FAIL=$((FAIL+1))
  fi
}

code() { curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$@" 2>/dev/null || echo "000"; }

check "backend /health/live"  "200" "$(code http://localhost:3001/health/live)"
check "backend /health/ready" "200" "$(code http://localhost:3001/health/ready)"
check "API rejects missing key (401)" "401" "$(code http://localhost:3001/api/agents)"
check "API accepts real key" "200" "$(code -H "x-api-key: ${API_KEY}" http://localhost:3001/api/agents)"
check "frontend /api/health" "200" "$(code http://localhost:3000/api/health)"
check "frontend proxy reaches backend" "200" "$(code http://localhost:3000/api/agents)"

# Real write through the public API: register a uniquely named smoke actor.
SMOKE_NAME="live-smoke-$(date +%s)"
REGISTER_CODE="$(curl -s -o /tmp/live-smoke-register.json -w '%{http_code}' --max-time 15 \
  -X POST http://localhost:3001/identity/actors \
  -H "x-api-key: ${API_KEY}" -H 'Content-Type: application/json' \
  -d "{\"actor_type\":\"human\",\"name\":\"${SMOKE_NAME}\"}" 2>/dev/null || echo 000)"
if [[ "$REGISTER_CODE" == "200" || "$REGISTER_CODE" == "201" ]]; then
  check "identity write (register actor)" "ok" "ok"
else
  check "identity write (register actor)" "ok" "http:${REGISTER_CODE}"
fi

check "civilization operator overview" "200" \
  "$(code -H "x-api-key: ${API_KEY}" http://localhost:3001/api/civilization/operator/overview)"

# LLM reachability — authenticated probe from inside the backend container,
# using the container's own credentials. Informational, never fails the smoke.
LLM_CODE="$(docker exec agentco-live-backend sh -c \
  'curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "Authorization: Bearer ${LLM_API_KEY}" "${LLM_BASE_URL%/}/models"' 2>/dev/null || echo 000)"
if [[ "$LLM_CODE" == "200" ]]; then
  RESULTS+=("INFO  LLM endpoint reachable and key accepted (${LLM_BASE_URL})")
elif [[ "$LLM_CODE" == "401" || "$LLM_CODE" == "403" ]]; then
  RESULTS+=("INFO  LLM endpoint reachable but key REJECTED (${LLM_BASE_URL}, http:${LLM_CODE})")
else
  RESULTS+=("INFO  LLM endpoint NOT reachable (${LLM_BASE_URL}, http:${LLM_CODE}) — agents cannot think until it is up")
fi

echo
echo "=== live smoke results ==="
printf '%s\n' "${RESULTS[@]}"
echo "=========================="
echo "passed ${PASS}, failed ${FAIL}"
[[ "$FAIL" -eq 0 ]]
