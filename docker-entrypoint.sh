#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

if [ "$SEED_ON_START" = "true" ] && [ ! -f "/app/.seeded" ]; then
    echo "Seeding database with demo data..."
    python seed.py
    touch /app/.seeded
fi

exec "$@"
