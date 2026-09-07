#!/usr/bin/env bash
# deploy.sh — one command to build + deploy + register webhook
# Usage: ./scripts/deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo ""
echo "🤖 Jarvis 4-Agent Deploy"
echo "========================"
echo ""

# ── 0. Ensure local toolchain is on PATH for Git Bash / WSL-ish shells ──────
if ! command -v terraform >/dev/null 2>&1; then
  for candidate in \
    "/c/ProgramData/chocolatey/bin" \
    "/c/Program Files/Amazon/AWSCLIV2" \
    "/c/Program Files/Terraform" \
    "/c/Program Files/HashiCorp/Terraform"; do
    if [[ -d "$candidate" ]]; then
      export PATH="$candidate:${PATH:-}"
    fi
  done
fi
if ! command -v aws >/dev/null 2>&1; then
  export PATH="/c/Program Files/Amazon/AWSCLIV2:${PATH:-}"
fi

if command -v terraform >/dev/null 2>&1; then
  echo "✅ terraform found at: $(command -v terraform)"
fi
if command -v aws >/dev/null 2>&1; then
  echo "✅ aws found at: $(command -v aws)"
fi

# ── 1. Load .env ──────────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  echo "❌ .env not found. Copy .env.example and fill in your keys:"
  echo "   cp .env.example .env && nano .env"
  exit 1
fi
set -a; source .env; set +a
echo "✅ Loaded .env"

# ── 2. Build Lambda package ───────────────────────────────────────────────────
echo ""
echo "📦 Building Lambda package..."
if command -v docker >/dev/null 2>&1; then
  bash scripts/build_lambda.sh
else
  if [[ -f lambda_package.zip ]]; then
    echo "⚠️ Docker unavailable; using existing lambda_package.zip"
  else
    echo "❌ No lambda_package.zip found and Docker is not installed."
    echo "   Install Docker or build the ZIP on a Docker-enabled machine."
    exit 1
  fi
fi
echo "✅ lambda_package.zip ready"

# ── 3. Terraform apply ────────────────────────────────────────────────────────
echo ""
echo "🏗️  Applying Terraform..."
cd terraform
terraform init -input=false -upgrade 2>&1 | tail -5
terraform apply -auto-approve \
  -var="telegram_token=${TELEGRAM_TOKEN}" \
  -var="allowed_user_id=${ALLOWED_USER_ID}" \
  -var="groq_api_key=${GROQ_API_KEY}" \
  -var="gemini_api_key=${GEMINI_API_KEY}" \
  -var="aws_region=${AWS_REGION:-ap-south-1}"

WEBHOOK_URL=$(terraform output -raw webhook_url)
cd ..
echo "✅ Infrastructure deployed"
echo "   Webhook URL: $WEBHOOK_URL"

# ── 4. Push optional Google secrets to SSM ───────────────────────────────────
if [[ -n "${GMAIL_TOKEN_JSON:-}" ]]; then
  echo ""
  echo "📧 Pushing Gmail token to SSM..."
  aws ssm put-parameter \
    --name "/shreyo-agent/GMAIL_TOKEN_JSON" \
    --value "$GMAIL_TOKEN_JSON" \
    --type SecureString \
    --overwrite \
    --region "${AWS_REGION:-ap-south-1}"
  echo "✅ Gmail token stored"
fi

if [[ -n "${INSTAGRAM_ACCESS_TOKEN:-}" ]]; then
  echo ""
  echo "📸 Pushing Instagram token to SSM..."
  aws ssm put-parameter \
    --name "/shreyo-agent/INSTAGRAM_ACCESS_TOKEN" \
    --value "$INSTAGRAM_ACCESS_TOKEN" \
    --type SecureString \
    --overwrite \
    --region "${AWS_REGION:-ap-south-1}"
  echo "✅ Instagram token stored"
fi

# ── 5. Register Telegram webhook ──────────────────────────────────────────────
echo ""
echo "📡 Registering Telegram webhook..."
RESPONSE=$(curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_URL}" \
  -d "allowed_updates=[\"message\",\"callback_query\"]")

if echo "$RESPONSE" | grep -q '"ok":true'; then
  echo "✅ Webhook registered: $WEBHOOK_URL"
else
  echo "⚠️  Webhook registration returned: $RESPONSE"
  echo "   Run manually: bash scripts/set_webhook.sh"
fi

echo ""
echo "🚀 Jarvis is live!"
echo "   Open Telegram → find your bot → send /start"
echo ""
echo "   CloudWatch logs:"
LOGGROUP=$(cd terraform && terraform output -raw log_group)
echo "   https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION:-ap-south-1}#logsV2:log-groups/log-group/${LOGGROUP/\//\$252F}"
echo ""
