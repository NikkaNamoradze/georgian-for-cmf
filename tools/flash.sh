#!/usr/bin/env bash
# Sends firmware to a CMF Watch Pro 2 over Bluetooth from this computer.
#   tools/flash.sh            install the Georgian build (run tools/build.sh first)
#   tools/flash.sh --restore  put the untouched stock 1.0.0.73 firmware back
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
UTILS="$BUILD/cmf-watch-utils"
IMAGE="$BUILD/JX402_V1.0.0.73_georgian.bin"
[ "${1:-}" = "--restore" ] && IMAGE="$BUILD/JX402_V1.0.0.73.bin"

[ -f "$IMAGE" ] && [ -d "$UTILS" ] || { echo "Run tools/build.sh first." >&2; exit 1; }
(cd "$UTILS" && uv run -q fwkit verify "$IMAGE" >/dev/null) || { echo "Image failed its checksum check: $IMAGE" >&2; exit 1; }

cat <<'TXT'
Before you continue:
  - Turn Bluetooth OFF on your phone, so Nothing X does not take the connection.
  - Put the watch on its charger, next to this computer, and keep it awake.
  - Keep this computer awake and plugged in until the watch restarts.
TXT
read -r -p "Ready? [y/N] " ok; [ "$ok" = "y" ] || exit 1

cd "$UTILS"
echo "==> Connecting to the watch"
uv run -q python tools/cmf_watch.py pair >/dev/null
INFO="$(uv run -q python tools/cmf_watch.py info 2>&1)"
VERSION="$(printf '%s\n' "$INFO" | sed -n "s/.*AT GETVERSION -> 'GETVERSION:\([0-9.]*\),OK'.*/\1/p" | head -1)"
NAME="$(printf '%s\n' "$INFO" | sed -n "s/.*AT GETNAME -> 'GETNAME:\(.*\),OK'.*/\1/p" | head -1)"
echo "Found: ${NAME:-unknown}, firmware ${VERSION:-unknown}"
case "$NAME" in "CMF Watch Pro 2"*) ;; *) echo "This is not a CMF Watch Pro 2. Stopping." >&2; exit 1;; esac
if [ "$VERSION" != "1.0.0.73" ]; then
  echo "This build is made from firmware 1.0.0.73, but the watch runs ${VERSION:-an unknown version}." >&2
  echo "Installing it would be an untested downgrade. Stopping." >&2
  exit 1
fi

read -r -p "Send $(basename "$IMAGE") to the watch now? [y/N] " ok; [ "$ok" = "y" ] || exit 1
echo "==> Sending (about 10 minutes; do not move the watch)"
AWAKE=(); command -v caffeinate >/dev/null && AWAKE=(caffeinate -dims)  # macOS: no sleep during transfer
LOG="$BUILD/flash-$(date +%Y%m%d-%H%M%S).log"
"${AWAKE[@]}" uv run -q python tools/ota_client.py --image "$IMAGE" -v > "$LOG" 2>&1 || true
if grep -q "summary:" "$LOG"; then
  echo "Done. The watch installs the update and restarts. Turn phone Bluetooth back on."
else
  echo "The transfer did not finish. Log: $LOG" >&2
  echo "Do not retry repeatedly; see the troubleshooting link in README.md." >&2
  exit 1
fi
