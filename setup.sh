#!/usr/bin/env bash
# AcmeFlow API - local lab setup
#
# Builds the Docker images, starts PostgreSQL, waits for it to be healthy,
# and seeds deterministic test data. Safe to re-run at any time (it fully
# resets the database).
set -euo pipefail

cd "$(dirname "$0")"

echo "== AcmeFlow API setup =="

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop / Docker Engine and re-run this script." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 (the 'docker compose' subcommand) is required." >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Starting PostgreSQL..."
docker compose up -d db

echo "Waiting for PostgreSQL to become healthy..."
attempts=0
until [ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q db)" 2>/dev/null)" = "healthy" ]; do
  attempts=$((attempts + 1))
  if [ "$attempts" -gt 30 ]; then
    echo "PostgreSQL did not become healthy in time." >&2
    exit 1
  fi
  sleep 2
done

echo "Building the API image..."
docker compose build api

echo "Seeding deterministic lab data (Alice, Bob, David, Admin, and friends)..."
docker compose run --rm api python -m app.seed --reset

cat <<'EOF'

Setup complete.

Start the API with:
    docker compose up

Then visit:
    http://localhost:8000/docs
    http://localhost:8000/redoc
    http://localhost:8000/openapi.json

See README.md for test accounts, vulnerability write-ups, and APIAT integration.
EOF
