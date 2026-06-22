#!/usr/bin/env bash
set -u

REPO_DIR="${REPO_DIR:-$HOME/Agentco}"
SLEEP_SECONDS="${SLEEP_SECONDS:-3600}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-12}"
PROMPT_FILE="${PROMPT_FILE:-prompts/agentco_resume_prompt.txt}"

cd "$REPO_DIR" || {
  echo "Repo not found: $REPO_DIR"
  exit 1
}

if [ ! -d ".git" ]; then
  echo "This is not a Git repository. Stop."
  exit 1
fi

mkdir -p logs/codex
mkdir -p docs/refoundation

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found. Install/login to Codex CLI first."
  exit 1
fi

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Prompt file missing: $PROMPT_FILE"
  exit 1
fi

echo "Starting hourly Codex resume loop"
echo "Repo: $REPO_DIR"
echo "Sleep seconds: $SLEEP_SECONDS"
echo "Max attempts: $MAX_ATTEMPTS"

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
  LOG_FILE="logs/codex/hourly_resume_${attempt}_${TIMESTAMP}.log"

  echo ""
  echo "===== Codex resume attempt $attempt / $MAX_ATTEMPTS ====="
  date
  echo "Log: $LOG_FILE"

  codex exec resume --last --sandbox workspace-write - < "$PROMPT_FILE" 2>&1 | tee "$LOG_FILE"
  STATUS=${PIPESTATUS[0]}

  if [ "$STATUS" -eq 0 ]; then
    echo ""
    echo "Codex command completed successfully."
    echo "Review changes now:"
    echo "  git status"
    echo "  git diff --stat"
    exit 0
  fi

  echo ""
  echo "Codex exited with status $STATUS."
  echo "Possibly still rate-limited, interrupted, or failed."
  echo "Waiting $SLEEP_SECONDS seconds before retrying..."
  sleep "$SLEEP_SECONDS"
done

echo ""
echo "Max attempts reached."
echo "Check:"
echo "  logs/codex/"
echo "  docs/refoundation/SESSION_HANDOFF.md"
echo "  docs/refoundation/BUILD_STATE.json"
exit 1
