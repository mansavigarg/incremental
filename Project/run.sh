#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"

has_dependencies() {
  "$1" -c 'import uvicorn; import loanserve.api.server' >/dev/null 2>&1
}

if [[ -n "${LOANSERVE_PYTHON:-}" ]]; then
  python_bin="$LOANSERVE_PYTHON"
elif command -v python3 >/dev/null 2>&1 && has_dependencies python3; then
  python_bin="python3"
elif command -v python >/dev/null 2>&1 && has_dependencies python; then
  python_bin="python"
elif [[ -x .venv/bin/python ]] && has_dependencies .venv/bin/python; then
  python_bin=".venv/bin/python"
else
  echo "No Python interpreter with LoanServe dependencies was found." >&2
  echo "Install with: python3 -m pip install -r requirements.txt" >&2
  exit 1
fi

if ! has_dependencies "$python_bin"; then
  echo "LoanServe dependencies are missing from $python_bin." >&2
  echo "Install them with: $python_bin -m pip install -r requirements.txt" >&2
  exit 1
fi

case "${1:-serve}" in
  check)
    exec "$python_bin" -m scripts.check_features
    ;;
  check-live)
    exec "$python_bin" -m scripts.check_features --live
    ;;
  serve)
    ;;
  *)
    echo "Usage: bash run.sh [serve|check|check-live]" >&2
    exit 2
    ;;
esac

host="${LOANSERVE_HOST:-127.0.0.1}"
port="${LOANSERVE_PORT:-8000}"
exec "$python_bin" -m uvicorn loanserve.api.server:create_server_application \
  --factory --host "$host" --port "$port"
