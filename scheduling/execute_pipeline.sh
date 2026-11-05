#!/usr/bin/env bash
# Run the collection pipeline. Designed to be called by cron.

# Adjust PROJECT and PYTHON to the paths on YOUR computer (always absolute).
set -u

PROJECT="../pipeline"
PYTHON="$PROJECT/.venv/bin/python"
LOG="$PROJECT/logs/cron.log"

mkdir -p "$PROJECT/logs"
cd "$PROJECT" || exit 2

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') start"
  "$PYTHON" -m coleta "$@"
  codigo=$?
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') end (code $codigo)"
} >> "$LOG" 2>&1

exit "$codigo"
