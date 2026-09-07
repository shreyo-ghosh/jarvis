#!/usr/bin/env bash
# set_webhook.sh — register or update the Telegram webhook
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then echo "❌ .env not found"; exit 1; fi
set -a; source .env; set +a

# Get webhook URL from Terraform output
WEBHOOK_URL=$(cd terraform && terraform output -raw webhook_url 2>/dev/null || echo "")

if [[ -z "$WEBHOOK_URL" ]]; then
  echo "❌ Could not get webhook URL from Terraform. Run terraform apply first."
  exit 1
fi

echo "📡 Registering webhook: $WEBHOOK_URL"

RESPONSE=$(curl -s \
  "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_URL}" \
  -d "allowed_updates=[\"message\",\"callback_query\"]")

echo "Response: $RESPONSE"

if echo "$RESPONSE" | grep -q '"ok":true'; then
  echo "✅ Webhook set successfully"
else
  echo "❌ Failed to set webhook"
  exit 1
fi

# Verify
echo ""
echo "Verifying..."
curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/getWebhookInfo" | python3 -m json.tool
