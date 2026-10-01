#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---quick}"
if [[ -n "${PYTHON:-}" ]]; then
  PYTHON="$PYTHON"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
else
  PYTHON="python"
fi

if [[ $# -gt 1 || ( "$MODE" != "--quick" && "$MODE" != "--full" ) ]]; then
  printf 'Uso: %s [--quick|--full]\n' "$0" >&2
  exit 2
fi

cd "$ROOT_DIR"

printf '[qa] tests\n'
"$PYTHON" -m pytest -q

printf '[qa] compileall\n'
"$PYTHON" -m compileall -q .

printf '[qa] git diff --check\n'
git diff --check

if [[ "$MODE" == "--quick" ]]; then
  printf '[qa] quick OK\n'
  exit 0
fi

printf '[qa] db-check\n'
"$PYTHON" -m flask --app app db-check

printf '[qa] db-counts\n'
"$PYTHON" -m flask --app app db-counts

QA_PORT="${QA_PORT:-$("$PYTHON" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')}"
GUNICORN_LOG="$(mktemp "${TMPDIR:-/tmp}/amon-erp-gunicorn.XXXXXX")"
GUNICORN_PID=""

cleanup() {
  if [[ -n "$GUNICORN_PID" ]] && kill -0 "$GUNICORN_PID" 2>/dev/null; then
    kill "$GUNICORN_PID" 2>/dev/null || true
    wait "$GUNICORN_PID" 2>/dev/null || true
  fi
  rm -f "$GUNICORN_LOG"
}
trap cleanup EXIT INT TERM

printf '[qa] gunicorn /health\n'
"$PYTHON" -m gunicorn --bind "127.0.0.1:${QA_PORT}" --workers 1 --timeout 30 wsgi:app >"$GUNICORN_LOG" 2>&1 &
GUNICORN_PID=$!

HEALTH_OK=0
for _attempt in {1..30}; do
  if HEALTH_RESPONSE="$(curl --fail --silent --show-error "http://127.0.0.1:${QA_PORT}/health" 2>/dev/null)"; then
    if [[ "$HEALTH_RESPONSE" == *'"status":"ok"'* && "$HEALTH_RESPONSE" == *'"database":"ok"'* ]]; then
      HEALTH_OK=1
      break
    fi
  fi
  if ! kill -0 "$GUNICORN_PID" 2>/dev/null; then
    break
  fi
  sleep 0.2
done

if [[ "$HEALTH_OK" -ne 1 ]]; then
  printf '[qa] Gunicorn health check failed.\n' >&2
  cat "$GUNICORN_LOG" >&2
  exit 1
fi

printf '[qa] full OK\n'
