#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || CHROME="$(command -v chromium || command -v google-chrome)"
"$CHROME" \
  --headless \
  --disable-gpu \
  --no-pdf-header-footer \
  --print-to-pdf="$DIR/draft.pdf" \
  --virtual-time-budget=5000 \
  "file://$DIR/draft.html" 2>/dev/null
echo "OK: $DIR/draft.pdf"
