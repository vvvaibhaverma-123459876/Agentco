#!/usr/bin/env bash
# Frontend auth smoke for local development.
#
# Proves:
# - Backend protects non-public API routes when AGENTCO_API_KEY is configured.
# - Frontend can start with NEXT_PUBLIC_AGENTCO_API_KEY and NEXT_PUBLIC_API_URL.
# - The API dependencies used by the dashboard, audit, and autonomy pages respond
#   when called with the same auth headers the frontend client adds.
#
# Does not prove:
# - Browser JavaScript execution, hydration, or visual correctness.
# - User login/session behavior; this is API-key header auth only.
# - Production deployment posture.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-3101}"
FRONTEND_PORT="${FRONTEND_PORT:-3100}"
API_KEY="${AGENTCO_API_KEY:-phase5-smoke-key}"
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"
BACKEND_LOG="${TMPDIR:-/tmp}/agentco_frontend_auth_backend_${BACKEND_PORT}.log"
FRONTEND_LOG="${TMPDIR:-/tmp}/agentco_frontend_auth_frontend_${FRONTEND_PORT}.log"

backend_pid=""
frontend_pid=""

cleanup() {
  if [[ -n "${frontend_pid}" ]] && kill -0 "${frontend_pid}" 2>/dev/null; then
    kill "${frontend_pid}" 2>/dev/null || true
  fi
  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" 2>/dev/null; then
    kill "${backend_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"
  for _ in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "ready: ${label} ${url}"
      return 0
    fi
    sleep 1
  done
  echo "ERROR: timed out waiting for ${label} at ${url}" >&2
  return 1
}

expect_status() {
  local expected="$1"
  local url="$2"
  shift 2
  local status
  status="$(curl -sS -o /tmp/agentco_smoke_response.$$ -w '%{http_code}' "$@" "${url}" || true)"
  if [[ "${status}" != "${expected}" ]]; then
    echo "ERROR: ${url} expected HTTP ${expected}, got ${status}" >&2
    echo "response:" >&2
    sed -n '1,40p' /tmp/agentco_smoke_response.$$ >&2 || true
    return 1
  fi
  echo "ok ${expected}: ${url}"
}

auth_headers=(-H "x-api-key: ${API_KEY}" -H "x-agentco-api-key: ${API_KEY}" -H "Accept: application/json")

echo "starting backend on ${BACKEND_URL}"
(
  cd "${ROOT}/backend"
  AGENTCO_API_KEY="${API_KEY}" \
  PORT="${BACKEND_PORT}" \
  HOST="127.0.0.1" \
  FRONTEND_URL="${FRONTEND_URL}" \
  npm run dev
) >"${BACKEND_LOG}" 2>&1 &
backend_pid="$!"

wait_for_url "${BACKEND_URL}/health" "backend"

echo "starting frontend on ${FRONTEND_URL}"
(
  cd "${ROOT}/frontend"
  NEXT_PUBLIC_AGENTCO_API_KEY="${API_KEY}" \
  NEXT_PUBLIC_API_URL="${BACKEND_URL}" \
  npm run dev -- --hostname 127.0.0.1 --port "${FRONTEND_PORT}"
) >"${FRONTEND_LOG}" 2>&1 &
frontend_pid="$!"

wait_for_url "${FRONTEND_URL}/dashboard" "frontend dashboard page"
expect_status 200 "${FRONTEND_URL}/audit"
expect_status 200 "${FRONTEND_URL}/autonomy"

echo "checking protected API routes reject missing key"
for endpoint in \
  "/api/agents" \
  "/api/audit" \
  "/api/audit/integrity" \
  "/api/autonomy/runs?limit=5" \
  "/api/autonomy/tasks?limit=5" \
  "/api/autonomy/dashboard/overview"
do
  expect_status 401 "${BACKEND_URL}${endpoint}"
done

echo "checking frontend API dependencies with auth headers"
for endpoint in \
  "/api/agents" \
  "/api/audit?limit=5" \
  "/api/audit/integrity" \
  "/api/autonomy/runs?limit=5" \
  "/api/autonomy/tasks?limit=5" \
  "/api/autonomy/candidates?limit=5" \
  "/api/autonomy/evals/scorecards?limit=5" \
  "/api/autonomy/dashboard/overview"
do
  expect_status 200 "${BACKEND_URL}${endpoint}" "${auth_headers[@]}"
done

echo "frontend auth smoke passed"
echo "backend log: ${BACKEND_LOG}"
echo "frontend log: ${FRONTEND_LOG}"
