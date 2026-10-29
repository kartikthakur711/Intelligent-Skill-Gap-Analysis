#!/usr/bin/env bash
set -euo pipefail

uvicorn api:app --reload --host 0.0.0.0 --port 8000 &
api_pid=$!
npm run dev &
gateway_pid=$!
pnpm --dir web dev --host 0.0.0.0 &
web_pid=$!

stop_services() {
  kill "$api_pid" "$gateway_pid" "$web_pid" 2>/dev/null || true
}
trap stop_services EXIT INT TERM

wait -n "$api_pid" "$gateway_pid" "$web_pid"
