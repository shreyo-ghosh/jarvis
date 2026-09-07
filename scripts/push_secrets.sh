#!/usr/bin/env bash
set -euo pipefail
export PATH="/c/ProgramData/chocolatey/bin:/c/Program Files/Amazon/AWSCLIV2:$PATH"
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  echo ".env not found. Copy .env.example to .env and fill in your keys first."
  exit 1
fi
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

push() {
  local name="$1"
  local value="$2"
  if [ -z "$value" ]; then
    echo "Skipping $name (empty)"
    return
  fi
  aws ssm put-parameter \
    --name "${PREFIX}/${name}" \
    --value "$value" \
    --type "SecureString" \
    --overwrite \
    --region "$REGION" > /dev/null
  echo "Pushed ${PREFIX}/${name}"
}

push "TELEGRAM_TOKEN" "$TELEGRAM_TOKEN"
push "ALLOWED_USER_ID" "$ALLOWED_USER_ID"
push "GROQ_API_KEY" "$GROQ_API_KEY"
push "GEMINI_API_KEY" "$GEMINI_API_KEY"
echo "Secrets pushed to SSM under ${PREFIX}/"
