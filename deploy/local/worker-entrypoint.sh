#!/bin/sh
# Worker container entrypoint for the local live stack.
# Usage: worker-entrypoint.sh dist/workers/<worker>.js
#
# Sources the LLM budget IDs the backend entrypoint seeded (workers spawn LLM-calling
# subprocesses and must carry the same budget principal), then execs the worker.
set -eu

if [ -f /shared/llm-ids.env ]; then
  . /shared/llm-ids.env
  export LLM_RESOURCE_ACTOR_ID LLM_RESOURCE_ACCOUNT_ID
fi

exec node "$@"
