#!/usr/bin/env bash
set -euo pipefail

PORT="${CHROME_DEBUG_PORT:-9222}"
URL="http://127.0.0.1:${PORT}"

echo "Checking Chrome CDP at ${URL} ..."
if curl -fsS "${URL}/json/version" >/dev/null; then
  curl -s "${URL}/json/version" | python3 -m json.tool 2>/dev/null || curl -s "${URL}/json/version"
  echo ""
  echo "CDP is reachable. Use the debug Chrome window (separate from your daily Chrome)."
  echo "Open WhatsApp Web there, then run:"
  echo "  python -m personal_reply suggest --from-browser --verbose"
  exit 0
fi

echo "CDP is NOT reachable on port ${PORT}." >&2
echo "Start the agent's debug Chrome with:" >&2
echo "  ./scripts/launch_chrome_debug.sh" >&2
echo "Your regular Chrome can stay open — the script launches a second Chrome instance." >&2
exit 1
