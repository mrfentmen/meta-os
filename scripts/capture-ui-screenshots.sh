#!/bin/sh
# capture-ui-screenshots.sh <label> [outdir]
# HN-021 capture helper — run on a machine WITH Chrome (del's Mac).
# Takes full-page desktop (1440x900) and mobile (390x844) captures
# of the app for one tip; the six surfaces in docs/UI_SCREENSHOT_PACK.md
# are framed from these plus the manual steps listed there.
# Usage: ./scripts/capture-ui-screenshots.sh before docs/screenshots
set -eu
LABEL="${1:?usage: $0 <label> [outdir]}"
OUTDIR="${2:-docs/screenshots}"
PORT="${PORT:-8080}"
mkdir -p "$OUTDIR"

CHROME=""
if command -v google-chrome >/dev/null 2>&1; then CHROME="google-chrome";
elif [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
else echo "no Chrome found (google-chrome or Mac Chrome app)"; exit 1; fi

if ! curl -fsS "http://localhost:$PORT/" >/dev/null 2>&1; then
  echo "starting server on port $PORT"
  PORT="$PORT" node server/server.mjs &
  SERVER_PID=$!
  trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
  for i in 1 2 3 4 5 6 7 8 9 10; do
    curl -fsS "http://localhost:$PORT/" >/dev/null 2>&1 && break
    sleep 1
  done
fi

"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1440,900 --virtual-time-budget=8000 \
  --screenshot="$OUTDIR/$LABEL-desktop.png" "http://localhost:$PORT/" >/dev/null 2>&1
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=390,844 --virtual-time-budget=8000 \
  --screenshot="$OUTDIR/$LABEL-mobile.png" "http://localhost:$PORT/" >/dev/null 2>&1
echo "wrote $OUTDIR/$LABEL-desktop.png $OUTDIR/$LABEL-mobile.png"
