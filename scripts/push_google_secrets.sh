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
PREFIX="/${PROJECT_NAME:-shreyo-agent}"
REGION="${AWS_REGION:-ap-south-1}"
if [ ! -f google_token.json ] || [ ! -f credentials.json ]; then
  echo "Missing google_token.json or credentials.json. Run scripts/setup_google_auth.py first."
  exit 1
fi
aws ssm put-parameter \
  --name "${PREFIX}/GMAIL_TOKEN_JSON" \
  --value "$(cat google_token.json)" \
  --type "SecureString" \
  --overwrite \
  --region "$REGION" > /dev/null
echo "Pushed ${PREFIX}/GMAIL_TOKEN_JSON"
aws ssm put-parameter \
  --name "${PREFIX}/GMAIL_CREDENTIALS_JSON" \
  --value "$(cat credentials.json)" \
  --type "SecureString" \
  --overwrite \
  --region "$REGION" > /dev/null
echo "Pushed ${PREFIX}/GMAIL_CREDENTIALS_JSON"
