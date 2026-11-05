#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python_bin="${LOANSERVE_PYTHON:-python3}"
"$python_bin" -m pip install --user --break-system-packages torch --index-url https://download.pytorch.org/whl/cpu
"$python_bin" -m pip install --user --break-system-packages -r requirements.txt
if [[ ! -f .env ]]; then
  cp .env.example .env
fi
if ! grep -q '^LOANSERVE_JWT_SECRET=.' .env; then
  printf '\nLOANSERVE_JWT_SECRET=%s\n' "$("$python_bin" -c 'import secrets; print(secrets.token_hex(32))')" >> .env
fi
echo "Installed. Add GEMINI_API_KEY and GEMINI_MODEL to .env, then run: ./start.sh"
