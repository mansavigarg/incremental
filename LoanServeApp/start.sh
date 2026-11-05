#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python_bin="${LOANSERVE_PYTHON:-python3}"
if ! "$python_bin" -c 'import uvicorn, streamlit' >/dev/null 2>&1; then
  echo "Dependencies missing. Run ./install.sh first." >&2
  exit 1
fi
"$python_bin" -m uvicorn loanserve.api.server:create_server_application --factory --host 127.0.0.1 --port 8000 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT
"$python_bin" -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
