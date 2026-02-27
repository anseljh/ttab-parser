#!/usr/bin/env bash
# bin/run.sh — Start the TTAB pipeline Docker services and wait until ready.
#
# Usage:
#   ./bin/run.sh          # start all services (build if needed)
#   ./bin/run.sh --build  # force rebuild before starting

set -euo pipefail

COMPOSE_FILE="$(cd "$(dirname "$0")/.." && pwd)/docker-compose.yml"
TIMEOUT=120   # seconds to wait for each health check
INTERVAL=2    # polling interval in seconds

# ── Colour helpers ────────────────────────────────────────────────────────────
red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
blue()  { printf '\033[0;34m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n' "$*"; }

# ── Parse flags ───────────────────────────────────────────────────────────────
EXTRA_ARGS=()
for arg in "$@"; do
  EXTRA_ARGS+=("$arg")
done

# ── Pre-flight checks ─────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  red "Error: docker is not installed or not on PATH."
  exit 1
fi

if ! docker compose version &>/dev/null; then
  red "Error: 'docker compose' (v2 plugin) is not available."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SETTINGS="$SCRIPT_DIR/settings.toml"
if [[ ! -f "$SETTINGS" ]]; then
  red "Error: settings.toml not found at $SETTINGS"
  printf 'Run: cp settings-example.toml settings.toml  # then fill in API keys\n'
  exit 1
fi

# ── Start services ────────────────────────────────────────────────────────────
blue "Starting TTAB pipeline services..."
docker compose -f "$COMPOSE_FILE" up -d "${EXTRA_ARGS[@]}"

# ── Wait helpers ──────────────────────────────────────────────────────────────
wait_for_tcp() {
  local name="$1" host="$2" port="$3"
  local elapsed=0
  printf 'Waiting for %s (%s:%s) ' "$name" "$host" "$port"
  while ! docker compose -f "$COMPOSE_FILE" exec -T "$name" \
        sh -c "nc -z localhost $port" &>/dev/null; do
    if (( elapsed >= TIMEOUT )); then
      printf '\n'
      red "Timed out waiting for $name after ${TIMEOUT}s."
      docker compose -f "$COMPOSE_FILE" logs --tail=20 "$name"
      exit 1
    fi
    printf '.'
    sleep "$INTERVAL"
    (( elapsed += INTERVAL ))
  done
  printf ' ready\n'
}

wait_for_log() {
  local name="$1" pattern="$2"
  local elapsed=0
  printf 'Waiting for %s to be ready ' "$name"
  while ! docker compose -f "$COMPOSE_FILE" logs "$name" 2>&1 | grep -q "$pattern"; do
    if (( elapsed >= TIMEOUT )); then
      printf '\n'
      red "Timed out waiting for $name after ${TIMEOUT}s."
      docker compose -f "$COMPOSE_FILE" logs --tail=20 "$name"
      exit 1
    fi
    printf '.'
    sleep "$INTERVAL"
    (( elapsed += INTERVAL ))
  done
  printf ' ready\n'
}

# ── Health checks ─────────────────────────────────────────────────────────────
# Redis: ping via redis-cli inside the container
elapsed=0
printf 'Waiting for redis '
while ! docker compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli ping 2>/dev/null | grep -q PONG; do
  if (( elapsed >= TIMEOUT )); then
    printf '\n'
    red "Timed out waiting for redis after ${TIMEOUT}s."
    docker compose -f "$COMPOSE_FILE" logs --tail=20 redis
    exit 1
  fi
  printf '.'
  sleep "$INTERVAL"
  (( elapsed += INTERVAL ))
done
printf ' ready\n'

# Postgres: pg_isready inside the container
elapsed=0
printf 'Waiting for postgres '
while ! docker compose -f "$COMPOSE_FILE" exec -T postgres \
      pg_isready -U ttab -d ttab &>/dev/null; do
  if (( elapsed >= TIMEOUT )); then
    printf '\n'
    red "Timed out waiting for postgres after ${TIMEOUT}s."
    docker compose -f "$COMPOSE_FILE" logs --tail=20 postgres
    exit 1
  fi
  printf '.'
  sleep "$INTERVAL"
  (( elapsed += INTERVAL ))
done
printf ' ready\n'

# Worker: look for Celery's "ready" log line
wait_for_log worker "celery@.* ready"

# Beat: look for "beat: Starting..." or "Scheduler: Sending" in logs
wait_for_log beat "beat: Starting\|Scheduler: Sending"

# ── Done ──────────────────────────────────────────────────────────────────────
printf '\n'
bold "$(green '✓ All TTAB pipeline services are up and ready.')"
printf '\n'
printf '  %-12s %s\n' "Redis:"    "redis://localhost:6379/0"
printf '  %-12s %s\n' "Postgres:" "postgresql://ttab:ttab@localhost:5432/ttab"
printf '  %-12s %s\n' "Worker:"   "$(docker compose -f "$COMPOSE_FILE" ps -q worker)"
printf '  %-12s %s\n' "Beat:"     "$(docker compose -f "$COMPOSE_FILE" ps -q beat)"
printf '\n'
printf 'Useful commands:\n'
printf '  docker compose logs -f worker          # follow worker logs\n'
printf '  docker compose logs -f beat            # follow beat logs\n'
printf '  docker compose exec worker uv run celery -A src.celery_app call src.tasks.download_task --kwargs '"'"'{"days":1}'"'"'\n'
printf '  docker compose down                    # stop all services\n'
