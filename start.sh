#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs/services"
PID_DIR="$ROOT_DIR/.pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python"
fi

is_port_open() {
  local port="$1"
  curl -fsS "http://127.0.0.1:${port}" >/dev/null 2>&1
}

is_api_healthy() {
  curl -fsS "http://127.0.0.1:8000/api/health" >/dev/null 2>&1
}

start_service() {
  local name="$1"
  local port="$2"
  local health_kind="$3"
  shift 3

  local pid_file="$PID_DIR/${name}.pid"
  local log_file="$LOG_DIR/${name}.log"

  if [[ -f "$pid_file" ]]; then
    local old_pid
    old_pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "$old_pid" ]] && kill -0 "$old_pid" >/dev/null 2>&1; then
      echo "[skip] ${name} already running (pid ${old_pid}, port ${port})"
      return 0
    fi
  fi

  if [[ "$health_kind" == "api" ]]; then
    if is_api_healthy; then
      echo "[skip] ${name} already responds on port ${port}"
      return 0
    fi
  elif is_port_open "$port"; then
    echo "[skip] ${name} already responds on port ${port}"
    return 0
  fi

  echo "[start] ${name} -> ${log_file}"
  (
    cd "$ROOT_DIR"
    setsid nohup "$@" >"$log_file" 2>&1 </dev/null &
    echo "$!" >"$pid_file"
  )

  sleep 0.2
}

wait_for_http() {
  local name="$1"
  local port="$2"
  local health_kind="$3"
  local attempts="${4:-60}"

  for _ in $(seq 1 "$attempts"); do
    if [[ "$health_kind" == "api" ]]; then
      if is_api_healthy; then
        echo "[ready] ${name}: http://127.0.0.1:${port}"
        return 0
      fi
    elif is_port_open "$port"; then
      echo "[ready] ${name}: http://127.0.0.1:${port}"
      return 0
    fi
    sleep 1
  done

  echo "[warn] ${name} did not respond on port ${port}; check logs/services/${name}.log" >&2
  return 1
}

start_service "fastapi" "8000" "api" "$PYTHON_BIN" "$ROOT_DIR/api_server.py"
start_service "react" "5173" "http" npm --prefix "$ROOT_DIR/frontend" run dev -- --host 0.0.0.0
start_service "gradio" "7860" "http" "$PYTHON_BIN" "$ROOT_DIR/main.py"

echo
wait_for_http "FastAPI" "8000" "api" 60 || true
wait_for_http "React" "5173" "http" 60 || true
wait_for_http "Gradio" "7860" "http" 90 || true

echo
echo "Services:"
echo "  React:  http://127.0.0.1:5173"
echo "  API:    http://127.0.0.1:8000"
echo "  Gradio: http://127.0.0.1:7860"
echo
echo "Logs: $LOG_DIR"
echo "PIDs: $PID_DIR"
