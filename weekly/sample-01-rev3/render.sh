#!/bin/bash
# 生成 sample.pdf：调用本机 Chrome 无头打印 sample.html
# 用法：./render.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || CHROME="$(command -v chromium || command -v google-chrome)"
"$CHROME" \
  --headless \
  --disable-gpu \
  --no-pdf-header-footer \
  --print-to-pdf="$DIR/sample.pdf" \
  --virtual-time-budget=5000 \
  "file://$DIR/sample.html" 2>/dev/null
echo "OK: $DIR/sample.pdf"
