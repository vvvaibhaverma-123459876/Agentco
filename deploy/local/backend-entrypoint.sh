#!/bin/sh
# Backend container entrypoint for the local live stack.
#
# Order matters: migrations must exist before the seed can write, and the seed's
# LLM_RESOURCE_ACTOR_ID / LLM_RESOURCE_ACCOUNT_ID exports must be in the
# environment before server.ts runs assertProductionSecrets() at boot.
set -eu

echo "[entrypoint] applying migrations" >&2
node dist/db/migrate.js

echo "[entrypoint] running bootstrap seed" >&2
seed_env="$(node dist/cli/seed-live.js --emit-env)"
eval "$seed_env"
export LLM_RESOURCE_ACTOR_ID LLM_RESOURCE_ACCOUNT_ID

# Share the seeded IDs with the worker containers via the shared volume.
# Non-fatal: a root-owned mount must degrade to a warning, not a boot loop.
if [ -d /shared ]; then
  if ! printf '%s\n' "$seed_env" > /shared/llm-ids.env 2>/dev/null; then
    echo "[entrypoint] WARN: /shared not writable; workers will run without seeded LLM budget IDs" >&2
  fi
fi

echo "[entrypoint] starting backend" >&2
exec node dist/server.js
