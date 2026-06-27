#!/usr/bin/env bash
# J.A.R.V.I.S. launcher for macOS and Linux (the cross-platform twin of JARVIS.bat).
#
#   ./jarvis.sh          start the backend and open the HUD as an app window
#   ./jarvis.sh --no-open start the backend only (open http://127.0.0.1:8765 yourself)
#
# The Python backend (jarvis_server.py) does the actual browser launching via its
# --open flag, so the same window-detection logic is shared across every OS.
set -euo pipefail

cd "$(dirname "$0")"

PORT="${JARVIS_PORT:-8765}"

# --- locate a Python 3 interpreter ---
PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' 2>/dev/null; then
      PY="$cand"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  echo "  [!] Python 3 not found on PATH. Install Python 3 and try again." >&2
  exit 1
fi

# --- optional: real telemetry ---
if ! "$PY" -c 'import psutil' >/dev/null 2>&1; then
  echo "  Installing psutil for real CPU/RAM telemetry (optional)..."
  "$PY" -m pip install --quiet psutil >/dev/null 2>&1 || \
    echo "  (psutil install skipped — estimated telemetry will be used)"
fi

echo
echo "  Booting J.A.R.V.I.S. on http://127.0.0.1:${PORT}/ ..."
echo "  (press Ctrl-C to shut down)"
echo

# The backend opens the app window itself unless told otherwise.
OPEN_FLAG="--open"
for arg in "$@"; do
  [ "$arg" = "--no-open" ] && OPEN_FLAG="--no-open"
done

exec "$PY" jarvis_server.py "$OPEN_FLAG"
