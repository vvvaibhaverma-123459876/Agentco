#!/bin/bash
# ============================================================
# Wait for PostgreSQL to be ready
# ============================================================
# This script waits for the Postgres container to accept connections.
# It uses pg_isready to check the database health.

set -e

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-agentco}"
POSTGRES_DB="${POSTGRES_DB:-agentco_test}"
MAX_RETRIES="${MAX_RETRIES:-30}"
RETRY_INTERVAL="${RETRY_INTERVAL:-2}"

echo "⏳ Waiting for PostgreSQL to be ready..."
echo "   Host: $POSTGRES_HOST:$POSTGRES_PORT"
echo "   User: $POSTGRES_USER"
echo "   Database: $POSTGRES_DB"
echo ""

retry_count=0
while [ $retry_count -lt $MAX_RETRIES ]; do
    echo -n "   Attempt $((retry_count + 1))/$MAX_RETRIES... "

    if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        exit 0
    fi

    echo "❌ Not ready yet. Waiting ${RETRY_INTERVAL}s..."
    sleep "$RETRY_INTERVAL"
    retry_count=$((retry_count + 1))
done

echo ""
echo "❌ PostgreSQL did not become ready after $((MAX_RETRIES * RETRY_INTERVAL)) seconds"
echo ""
echo "Troubleshooting:"
echo "1. Check if docker daemon is running: docker ps"
echo "2. Check postgres container: docker ps | grep postgres"
echo "3. Check logs: docker logs agentco-postgres"
echo "4. Try restarting: docker compose down && docker compose up -d postgres"
exit 1
