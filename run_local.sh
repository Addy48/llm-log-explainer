#!/usr/bin/env bash
# Run all three services on this machine without Docker.
#   ./run_local.sh          start everything, open http://localhost:3000
#   Ctrl+C                  stop everything
set -euo pipefail
cd "$(dirname "$0")"

if command -v uv >/dev/null; then
  [ -d .venv ] || uv venv -q -p 3.11 .venv
  uv pip install -q -p .venv -r llm-service/requirements.txt -r log-generator/requirements.txt
else
  [ -d .venv ] || python3 -m venv .venv
  .venv/bin/pip install -q -r llm-service/requirements.txt -r log-generator/requirements.txt
fi
PY="$PWD/.venv/bin/python"

# Optional LLM key (see .env.example)
if [ -f .env ]; then set -a; . ./.env; set +a; fi

# Stop leftovers from an earlier run of this script (only our own processes).
for port in 5001 8000 3000; do
  for pid in $(lsof -ti tcp:$port -sTCP:LISTEN 2>/dev/null || true); do
    if ps -o command= -p "$pid" | grep -qE "app\.py|uvicorn api:app|http\.server 3000"; then
      kill "$pid" 2>/dev/null || true
    else
      echo "Port $port is used by another program (pid $pid). Stop it and retry." >&2
      exit 1
    fi
  done
done
sleep 0.5

pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd log-generator && PORT=5001 exec "$PY" app.py) & pids+=($!)
(cd llm-service && LOG_GENERATOR_URL=http://localhost:5001 exec "$PY" -m uvicorn api:app --port 8000 --log-level warning) & pids+=($!)
(cd web-interface && exec "$PY" -m http.server 3000 --bind 127.0.0.1 >/dev/null 2>&1) & pids+=($!)

for i in $(seq 1 30); do
  curl -sf http://localhost:8000/health >/dev/null && break
  sleep 0.5
done
echo
echo "  Dashboard      http://localhost:3000"
echo "  API docs       http://localhost:8000/docs"
echo "  Log generator  http://localhost:5001/health"
echo
command -v open >/dev/null && open http://localhost:3000 || true
wait
