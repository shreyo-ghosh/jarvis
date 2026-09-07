#!/usr/bin/env bash
set -euo pipefail
export PATH="/c/ProgramData/chocolatey/bin:/c/Program Files/Amazon/AWSCLIV2:$PATH"
cd "$(dirname "$0")/.."
TEMP_ENV=$(mktemp)
trap 'rm -f "$TEMP_ENV"' EXIT
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "Python is required to normalize the local .env file."
  exit 127
fi
"$PYTHON_BIN" - "$TEMP_ENV" <<'PY'
from pathlib import Path
import sys
src = Path('.env')
tmp = Path(sys.argv[1])
text = src.read_text(encoding='utf-8-sig')
tmp.write_text(text.replace('\r\n', '\n').replace('\r', '\n'), encoding='utf-8')
PY
set -a
source "$TEMP_ENV"
set +a
WEBHOOK_URL=$(cd terraform && terraform output -raw webhook_url)
echo "Registering webhook: $WEBHOOK_URL"
curl -s --data "url=${WEBHOOK_URL}" \
  "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook"
echo ""
echo "Done. Verify with:"
echo "curl https://api.telegram.org/bot${TELEGRAM_TOKEN}/getWebhookInfo"
