# Shreyo Agent — AWS Edition

A Telegram bot "AI agent" for business automation (web search, LinkedIn posts, revenue logging, task tracking, Gmail + Calendar), running on **AWS Lambda + API Gateway**, using **Groq** (Llama 3.3 70B) and **Google Gemini** as free-tier AI backends instead of the Anthropic API. Infrastructure is defined in **Terraform** so the whole thing deploys with one command from VS Code.

## Architecture

```
Telegram → API Gateway (HTTPS webhook) → Lambda (bot.py) → Groq / Gemini
                                              │
                                              ├── DynamoDB (revenue + task log)
                                              ├── SSM Parameter Store (secrets)
                                              └── Gmail / Calendar APIs (optional)
```

| Piece | AWS Service | Cost |
|---|---|---|
| Compute | Lambda (Python 3.12) | Free tier: 1M requests + 400k GB-s/month |
| Ingress | API Gateway HTTP API | Free tier: 1M requests/month |
| Storage | DynamoDB (on-demand) | Pennies at this scale |
| Secrets | SSM Parameter Store (Standard) | Free |
| AI brain | Groq (Llama 3.3 70B) | Free tier: 14,400 req/day |
| AI backup | Google Gemini 1.5 Flash | Free tier: 1,500 req/day |

**Total recurring cost: ~₹0–5/day.**

---

## Prerequisites

Install these once on your machine:

1. [AWS CLI](https://aws.amazon.com/cli/) — `aws configure` with your access key/secret and default region (e.g. `ap-south-1`)
2. [Terraform](https://developer.hashicorp.com/terraform/downloads) (>= 1.6)
3. [Python 3.12](https://www.python.org/downloads/)
4. [Docker](https://www.docker.com/) (used to build the Lambda deployment package with the correct Linux binaries)
5. [VS Code](https://code.visualstudio.com/) with the AWS Toolkit + Terraform extensions (optional but nice)

Get these keys before you start:

| Key | Where to get it |
|---|---|
| `TELEGRAM_TOKEN` | Message `@BotFather` on Telegram → `/newbot` |
| `ALLOWED_USER_ID` | Message `@userinfobot` on Telegram |
| `GROQ_API_KEY` | https://console.groq.com/keys (free, no card) |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey (free, no card) |

---

## Quick Start (VS Code Terminal)

```bash
# 1. Clone / open this repo in VS Code
git clone <your-repo-url> shreyo-agent-aws
cd shreyo-agent-aws

# 2. Copy env template and fill in your keys
cp .env.example .env
# edit .env with your TELEGRAM_TOKEN, GROQ_API_KEY, GEMINI_API_KEY, ALLOWED_USER_ID

# 3. One-command deploy (builds Lambda package, applies Terraform, sets Telegram webhook)
./scripts/deploy.sh
```

That's it. The script will:

1. Build a Lambda-compatible dependency layer using Docker
2. Push your secrets into SSM Parameter Store
3. Run `terraform init && terraform apply` to create Lambda, API Gateway, DynamoDB, IAM roles
4. Grab the API Gateway URL from Terraform output and call Telegram's `setWebhook` automatically

Message your bot on Telegram → `/start` → you're live.

---

## Repo Structure

```
shreyo-agent-aws/
├── terraform/
│   ├── main.tf          # Lambda, API Gateway, DynamoDB, IAM, SSM
│   ├── variables.tf
│   └── outputs.tf
├── src/
│   ├── bot.py            # Lambda handler — parses Telegram webhook, routes to agent
│   ├── agent.py           # Groq (primary) + Gemini (fallback) routing + tool-calling loop
│   └── tools/
│       ├── search.py      # DuckDuckGo web search (free, no key)
│       ├── gmail.py        # Gmail draft + send (optional, Step 5)
│       ├── calendar_tool.py # Google Calendar read/write (optional, Step 5)
│       ├── linkedin.py      # LinkedIn post generator
│       └── tracker.py       # Revenue + task logging via DynamoDB
├── scripts/
│   ├── deploy.sh           # One-shot build + deploy + webhook registration
│   ├── build_lambda.sh     # Builds deployment zip with Docker (Linux-compatible deps)
│   ├── set_webhook.sh      # Registers/updates Telegram webhook URL
│   └── setup_google_auth.py # Optional — run locally once for Gmail/Calendar OAuth
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Step-by-Step Manual Walkthrough

If you'd rather run each step yourself instead of `deploy.sh`:

### 1. Configure AWS CLI
```bash
aws configure
```

### 2. Fill in secrets
```bash
cp .env.example .env
```

### 3. Push secrets to SSM
```bash
./scripts/push_secrets.sh
```

### 4. Build the Lambda package
```bash
./scripts/build_lambda.sh
```

### 5. Deploy infrastructure
```bash
cd terraform
terraform init
terraform apply
```

### 6. Register the Telegram webhook
```bash
cd ..
./scripts/set_webhook.sh
```

### 7. Test it
Open Telegram → find your bot → send `/start`, then try:
- `search for AI automation trends India 2026`
- `write a LinkedIn post about SIPs for millennials`
- `log revenue: ₹8000 from LaunchLayer client today`
- `show my revenue summary`

---

## Step 5 (Optional) — Gmail + Calendar

1. Go to https://console.cloud.google.com → New Project → "ShreyoAgent"
2. Enable **Gmail API** and **Google Calendar API**
3. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID → Application type: Desktop app → download as `credentials.json` into the repo root
4. Configure the OAuth consent screen (External, add your Gmail as a test user, add Gmail + Calendar scopes)
5. Run locally once:
   ```bash
   pip install google-auth-oauthlib google-api-python-client
   python scripts/setup_google_auth.py
   ```
6. Push both files to SSM and redeploy:
   ```bash
   ./scripts/push_google_secrets.sh
   cd terraform && terraform apply
   ```

---

## Updating the Bot

```bash
./scripts/build_lambda.sh
cd terraform && terraform apply
```

---

## Tearing Everything Down

```bash
cd terraform
terraform destroy
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Bot doesn't respond | Check CloudWatch Logs for the Lambda function (`/aws/lambda/shreyo-agent-bot`) |
| `Unauthorized` in Telegram | Your `ALLOWED_USER_ID` doesn't match — confirm via `@userinfobot` |
| Webhook not receiving updates | Re-run `./scripts/set_webhook.sh`; verify with `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo` |
| Terraform apply fails on IAM | Ensure your AWS user/role has `IAMFullAccess` or equivalent permissions |
| Gmail/Calendar errors | Re-run `scripts/setup_google_auth.py` — token likely expired, refresh token missing |
