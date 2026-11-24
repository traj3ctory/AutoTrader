#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

HOST="${AUTOTRADER_HOST:-127.0.0.1}"
PORT="${AUTOTRADER_PORT:-8787}"
URL="http://${HOST}:${PORT}"

is_listening() {
  python3 -c "import socket, sys; s = socket.socket(); s.settimeout(0.5); sys.exit(0 if s.connect_ex(('${HOST}', ${PORT})) == 0 else 1)"
}

if ! is_listening; then
  if [ ! -d "app/web/dist" ]; then
    (cd app/web && bun run build)
  fi
  nohup python3 app/server.py >/tmp/autotrader-analyzer.log 2>&1 &
  for _ in $(seq 1 20); do
    if is_listening; then
      break
    fi
    sleep 0.25
  done
fi

open -a "Google Chrome" "${URL}"
echo "Opened ${URL} in Google Chrome"
