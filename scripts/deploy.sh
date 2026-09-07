#!/usr/bin/env bash
set -euo pipefail
export PATH="/c/ProgramData/chocolatey/bin:/c/Program Files/Amazon/AWSCLIV2:$PATH"
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  echo ".env not found. Run: cp .env.example .env   then fill in your keys."
  exit 1
fi
echo "Step 1/4 — Building Lambda deployment package..."
./scripts/build_lambda.sh
echo "Step 2/4 — Pushing secrets to SSM..."
./scripts/push_secrets.sh
echo "Step 3/4 — Deploying infrastructure with Terraform..."
cd terraform
terraform init -input=false
terraform apply -auto-approve
cd ..
echo "Step 4/4 — Registering Telegram webhook..."
./scripts/set_webhook.sh
echo ""
echo "Deployment complete. Message your bot on Telegram to test it."
