#!/bin/sh
# Prepares the database, then starts the API (the container's CMD).
set -e

echo "Applying database migrations..."
alembic upgrade head

# Adds the standard exercise library; safe to run on every start (existing exercises are kept).
echo "Checking the exercise library..."
python -m app.cli seed-exercises

exec "$@"
