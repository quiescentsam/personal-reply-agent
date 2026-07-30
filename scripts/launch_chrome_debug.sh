#!/usr/bin/env bash
set -euo pipefail

PORT="${CHROME_DEBUG_PORT:-9222}"
CHROME_APP="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR="${CHROME_USER_DATA_DIR:-$HOME/.personal-reply-agent/chrome-debug-profile}"
START_URL="${CHROME_START_URL:-https://web.whatsapp.com}"
CDP_URL="http://127.0.0.1:${PORT}/json/version"

if [[ ! -x "$CHROME_APP" ]]; then
  echo "Google Chrome not found at: $CHROME_APP" >&2
  exit 1
fi

if curl -fsS "${CDP_URL}" >/dev/null 2>&1; then
  echo "Debug Chrome is already running on port ${PORT}."
  echo "Open WhatsApp Web in that window, then use Suggest Reply / Cmd+Shift+R."
  echo "Your regular Chrome is unaffected."
  exit 0
fi

mkdir -p "$USER_DATA_DIR"

if pgrep -xq "Google Chrome"; then
  echo "Your regular Chrome can stay open."
  echo "Starting a separate debug Chrome on port ${PORT}..."
else
  echo "Starting debug Chrome on port ${PORT}..."
fi

echo "Profile: ${USER_DATA_DIR}"
echo "This window is only for the reply agent — use your normal Chrome for everything else."
echo "Log into WhatsApp Web once in this window if you have not already."

# A dedicated --user-data-dir allows a second Chrome alongside your daily browser.
"$CHROME_APP" \
  --remote-debugging-port="${PORT}" \
  --remote-debugging-address=127.0.0.1 \
  --remote-allow-origins=* \
  --user-data-dir="${USER_DATA_DIR}" \
  --no-first-run \
  --no-default-browser-check \
  "${START_URL}" \
  "$@" &

sleep 1
if curl -fsS "${CDP_URL}" >/dev/null 2>&1; then
  echo "Debug Chrome is ready on port ${PORT}."
else
  echo "Debug Chrome launched; waiting for CDP on port ${PORT}..." >&2
  echo "If this persists, close other apps using port ${PORT} and retry." >&2
fi
