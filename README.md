# Jarvis — Shreyo's 4-Agent Business Command System
**AWS Lambda + DynamoDB + API Gateway · Groq Llama 3.3 70B + Gemini Flash · ~₹0/day**

```
YOU (Telegram)
     │
     ▼
🧠  ORCHESTRATOR  ←── daily brief, calendar, tasks, routing
     │
     ├─────────────────────┬──────────────────────┐
     ▼                     ▼                      ▼
📈 MARKET AGENT     📡 TECH AGENT         💰 FINANCE AGENT
Nifty / Sensex      LaunchLayer content   @launchlayerfinance IG
Stock analysis      @launchlayer IG       MO investor emails
MF NAV / data       LinkedIn posts        WhatsApp broadcasts
Watchlists          "Automation Edge"     AUM growth campaigns
Macro news          Cold outreach email   Lead strategies
```

---

## Agent Capabilities

| Say this | Agent | Output |
|---|---|---|
| `What should I focus on today?` | Orchestrator | Prioritised daily brief from calendar + tasks + market |
| `What's Nifty doing today?` | Market | Live index data via Gemini search |
| `Add RELIANCE to my watchlist` | Market | Saved to DynamoDB, shows current data |
| `Write this week's LaunchLayer newsletter` | Tech | Full "Automation Edge" newsletter draft |
| `LinkedIn post about AI for CA firms` | Tech | Ready-to-post, 200 words, hashtags |
| `Instagram post for @launchlayer about chatbots` | Tech | Caption + Canva visual brief |
| `Post on @launchlayerfinance about SIP vs FD` | Finance | Caption + visual + MF disclaimer |
| `WhatsApp messages for my MO leads` | Finance | 2 versions (beginner + FD holder) |
| `Draft MO outreach email for salaried leads` | Finance | Full email draft via Gmail |
| `Plan a campaign to grow AUM to ₹2L` | Finance | Week-by-week campaign plan |
| `Log ₹8000 from LaunchLayer client ABC` | Orchestrator | Saved to DynamoDB |
| `Show revenue summary` | Orchestrator | Totals by source, by month |
| `What's on my calendar this week?` | Orchestrator | Google Calendar pull |
| `Add meeting with Rahul tomorrow 3pm` | Orchestrator | Event created in Calendar |

---

## Architecture

```
Telegram → API Gateway (HTTPS) → Lambda (bot.py)
                                       │
                          ┌────────────┼────────────┐
                          ▼            ▼             ▼
                    agents/        tools/        AWS Services
                orchestrator.py   search.py     DynamoDB
                market_agent.py   gmail.py      SSM (secrets)
                tech_agent.py     calendar.py   CloudWatch
                finance_agent.py  instagram.py
                                  tracker.py
                                  dynamo.py
```

| Service | AWS Cost | Notes |
|---|---|---|
| Lambda | Free tier: 1M req/month | Runs per-message, not always-on |
| API Gateway | Free tier: 1M req/month | HTTPS webhook endpoint |
| DynamoDB | ~₹0 at this scale | On-demand billing |
| SSM | Free (Standard tier) | Stores all secrets |
| CloudWatch Logs | Free tier | 7-day retention |
| **Groq AI** | Free: 14,400 req/day | Llama 3.3 70B — the AI brain |
| **Gemini** | Free: 1,500 req/day | Web search grounding |
| **Total** | **~₹0–5/day** | |

---

## Prerequisites

Install once on your machine:
- [AWS CLI](https://aws.amazon.com/cli/) → `aws configure` (region: `ap-south-1`)
- [Terraform >= 1.6](https://developer.hashicorp.com/terraform/downloads)
- [Docker](https://www.docker.com/) (for Lambda build)
- [Python 3.12](https://www.python.org/downloads/)

Get these keys (all free):

| Key | Where |
|---|---|
| `TELEGRAM_TOKEN` | @BotFather → `/newbot` |
| `ALLOWED_USER_ID` | @userinfobot on Telegram |
| `GROQ_API_KEY` | console.groq.com (no card) |
| `GEMINI_API_KEY` | aistudio.google.com/apikey |

---

## Deploy

```bash
# 1. Clone your repo
git clone https://github.com/shreyo-ghosh/jarvis.git
cd jarvis

# 2. Fill in secrets
cp .env.example .env
nano .env   # paste your keys

# 3. One command — builds Lambda zip, applies Terraform, registers webhook
chmod +x scripts/*.sh
./scripts/deploy.sh
```

Done. Message your bot `/start`.

---

## Update After Code Changes

```bash
./scripts/build_lambda.sh
cd terraform && terraform apply -auto-approve \
  -var="telegram_token=$TELEGRAM_TOKEN" \
  -var="allowed_user_id=$ALLOWED_USER_ID" \
  -var="groq_api_key=$GROQ_API_KEY" \
  -var="gemini_api_key=$GEMINI_API_KEY"
```

Or just re-run `./scripts/deploy.sh` — it's idempotent.

---

## Step 5 (Optional) — Gmail + Google Calendar

```bash
pip install google-auth-oauthlib
python scripts/setup_google_auth.py
```

Follow the browser flow → logs in with your Google account → appends `GMAIL_TOKEN_JSON` to `.env`.
Re-run `./scripts/deploy.sh` — it pushes the token to SSM automatically.

Google Cloud setup (one-time):
1. console.cloud.google.com → New Project → "JarvisAgent"
2. Enable: Gmail API + Google Calendar API
3. OAuth consent screen → External → add your Gmail as test user
4. Credentials → OAuth 2.0 Client ID → Desktop → download as `credentials.json`

---

## Instagram Auto-Posting (Optional)

Both Instagram accounts must be Professional and linked to Facebook Pages.
1. Create Facebook App at developers.facebook.com
2. Get Instagram Graph API long-lived token
3. Find your Instagram Business Account IDs
4. Add to `.env`:
   ```
   INSTAGRAM_ACCESS_TOKEN=...
   LAUNCHLAYER_IG_ACCOUNT_ID=...
   LAUNCHLAYER_FINANCE_IG_ACCOUNT_ID=...
   ```
5. Re-run `./scripts/deploy.sh`

Until configured, the bot generates captions + Canva briefs for manual posting.

---

## Teardown

```bash
cd terraform && terraform destroy
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Bot silent | Check CloudWatch: `/aws/lambda/shreyo-jarvis-bot` |
| "Unauthorized" | Wrong ALLOWED_USER_ID — check @userinfobot |
| Webhook not firing | Re-run `./scripts/set_webhook.sh` |
| Terraform IAM error | Ensure AWS user has `IAMFullAccess` |
| Gmail/Calendar errors | Re-run `scripts/setup_google_auth.py` |
| Lambda timeout | Agent taking >60s — check Groq quota |

---

## File Structure

```
jarvis/
├── src/
│   ├── bot.py                     # Lambda handler — Telegram webhook entry point
│   ├── agents/
│   │   ├── orchestrator.py        # 🧠 Routes + daily briefs + tracker/calendar
│   │   ├── market_agent.py        # 📈 Indian market intelligence
│   │   ├── tech_agent.py          # 📡 LaunchLayer content + outreach
│   │   └── finance_agent.py       # 💰 MO outreach + @launchlayerfinance
│   └── tools/
│       ├── search.py              # Gemini search + DDG fallback
│       ├── gmail.py               # Gmail draft/send/inbox (SSM-backed)
│       ├── calendar_tool.py       # Google Calendar (SSM-backed)
│       ├── instagram.py           # IG captions + Graph API auto-post
│       ├── tracker.py             # Revenue + task tracker (DynamoDB)
│       └── dynamo.py              # DynamoDB key-value store
├── terraform/
│   ├── main.tf                    # Lambda, API GW, DynamoDB, IAM, SSM, CloudWatch
│   ├── variables.tf
│   └── outputs.tf
├── scripts/
│   ├── deploy.sh                  # One-shot: build + terraform + webhook
│   ├── build_lambda.sh            # Docker build for Linux-compatible deps
│   ├── set_webhook.sh             # Register/update Telegram webhook
│   └── setup_google_auth.py      # One-time Google OAuth flow
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
