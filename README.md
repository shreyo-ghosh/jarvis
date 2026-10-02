# Jarvis

Personal companion on AWS Lambda. Talk on Telegram or in the Iron Man HUD.

It answers general questions first — science, news, weather, coding, everyday things. LaunchLayer, Motilal, LinkedIn, and the desk come in only when you ask for them.

**HUD:** https://shreyo-ghosh.github.io/jarvis/

```
Telegram  ──┐
            ├──► API Gateway /webhook ──► Lambda (bot.py) ──► Orchestrator
HUD / desk ─┘         CORS + DESK_TOKEN              │
                                                     ├─ live search (weather, news, DDG)
                                                     ├─ memory (Dynamo)
                                                     └─ specialists only when the ask is theirs
                                                          Market · Tech · Finance
```

Groq chat (allowlist: `gpt-oss-20b` → `qwen3.8-27b` → `gpt-oss-120b`) · Whisper STT · Polly / browser TTS · ~₹0/day on the AWS free tier.

---

## Talk to it

| Where | How |
|---|---|
| Public HUD | https://shreyo-ghosh.github.io/jarvis/ — Preferences → paste `DESK_TOKEN` from `.env` once |
| This machine | `python3 scripts/hud.py` → http://127.0.0.1:8788/ — no token |
| Telegram | Your bot, `ALLOWED_USER_ID` only — text or a voice note |

On the HUD: click the core or press Space to talk (Chrome / Safari, HTTPS). Type if you prefer.

### Anything

`How does a rainbow form?` · `What's the weather in Kolkata right now?` · `What's the latest news I should know?`

### Desk (only when you mean it)

| Say this | What you get |
|---|---|
| `What should I focus on today?` | Calendar + tasks + market brief |
| `What's Nifty doing today?` | Market agent |
| `today's brief` / `linkedin calendar` | Daily LinkedIn review + 30-day plan |
| `linkedin post about …` | Draft card — review on the phone, tap to queue |
| `remind me in 20 minutes to call Rahul` | Reminder + activity |
| `/leads` · `/activities` · `/reminders` | Desk lists |
| `/remember …` · `/profile` | Standing notes |
| `/voice on` | Spoken replies on Telegram |

---

## Architecture

| Service | Cost | Notes |
|---|---|---|
| Lambda `shreyo-jarvis-bot` | Free tier | 120s / 1024 MB, ap-south-1 |
| API Gateway | Free tier | `https://xmkwdl0d1d.execute-api.ap-south-1.amazonaws.com/webhook` |
| DynamoDB `shreyo-agent-data` | ~₹0 | Memory, leads, drafts, reminders |
| SSM `/shreyo-agent/*` | Free | Secrets, including `DESK_TOKEN` |
| GitHub Pages | Free | Static HUD (`ui/`) |
| Groq | Free tier | Chat + Whisper |
| wttr.in / Google News RSS | Free | Live weather and headlines |

---

## Prerequisites

- AWS CLI, credentials for account `197517025619` in `.env` (the default AWS profile on this machine may be stale)
- Terraform ≥ 1.5
- Python 3.12 (Docker optional; `build_lambda.sh` can use manylinux wheels)

| Key | Where |
|---|---|
| `TELEGRAM_TOKEN` | @BotFather |
| `ALLOWED_USER_ID` | @userinfobot |
| `GROQ_API_KEY` | console.groq.com |
| `GEMINI_API_KEY` | aistudio.google.com/apikey |
| `DESK_TOKEN` | Long random string — HUD Preferences and SSM |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | IAM user `shreyo-cli`, region `ap-south-1` |

---

## Deploy (from this machine)

```bash
git clone https://github.com/shreyo-ghosh/jarvis.git
cd jarvis
cp .env.example .env   # fill keys; leave DESK_TOKEN blank to auto-generate
chmod +x scripts/*.sh
./scripts/deploy.sh
```

That builds `lambda_package.zip`, applies Terraform (CORS, OPTIONS, EventBridge tick), pushes `DESK_TOKEN` to SSM, and registers the Telegram webhook.

Then open the HUD → Preferences → paste `DESK_TOKEN` from `.env`.

Re-run `./scripts/deploy.sh` after code changes, or push to `main` — **Deploy Jarvis** applies the same state.

Terraform state is in S3 (`shreyo-jarvis-tfstate-197517025619` / `jarvis/terraform.tfstate`) with a Dynamo lock (`shreyo-jarvis-tf-lock`). First-time box:

```bash
./scripts/bootstrap_tf_backend.sh
cd terraform && terraform init
```

### GitHub Pages

Pushes to `ui/` publish https://shreyo-ghosh.github.io/jarvis/ via `.github/workflows/pages.yml`.

Pushes to `src/`, `terraform/`, or `scripts/` run **Deploy Jarvis** (Lambda zip + `terraform apply` against the remote state).

---

## Local HUD

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/hud.py
# http://127.0.0.1:8788/
```

Corporate SSL MITM: Groq and search retry without verify after certifi fails.

```bash
.venv/bin/python scripts/local_voice_test.py
```

---

## Optional

**Gmail + Calendar**

```bash
pip install google-auth-oauthlib
python scripts/setup_google_auth.py
./scripts/deploy.sh
```

**LinkedIn queue** — `PUBLORA_API_KEY` + `LINKEDIN_PLATFORM_ID` in `.env`, then deploy. Approve cards on Telegram; no laptop paste.

**Instagram** — Professional accounts + Graph token in `.env`. Until then, captions and Canva briefs only.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| HUD line **Down** | Lambda not deployed, or CORS missing — `./scripts/deploy.sh` |
| `Desk token rejected` | Preferences token ≠ SSM `/shreyo-agent/DESK_TOKEN` |
| GitHub Actions AWS error | Keys belong in `.env` and repo secrets; CI will not terraform-apply by default |
| `InvalidClientTokenId` | Source `.env` — do not rely on the default AWS profile |
| Bot silent | CloudWatch `/aws/lambda/shreyo-jarvis-bot` |
| Unauthorized on Telegram | Wrong `ALLOWED_USER_ID` |
| Webhook dead | `bash scripts/set_webhook.sh` |
| Answers drag in LaunchLayer | Ask a general question; work profile is injected only on work hints |

---

## Layout

```
jarvis/
├── ui/                         # GitHub Pages HUD
│   ├── index.html
│   ├── hud.css
│   └── hud.js
├── src/
│   ├── bot.py                  # Lambda: Telegram + desk_chat + CORS
│   ├── agents/
│   │   ├── orchestrator.py     # General chat, routing, desk, brief
│   │   ├── market_agent.py
│   │   ├── tech_agent.py
│   │   └── finance_agent.py
│   └── tools/                  # search, memory, LinkedIn, reminders, STT/TTS…
├── scripts/
│   ├── deploy.sh
│   ├── build_lambda.sh
│   ├── hud.py                  # Local HUD server
│   ├── push_secrets.sh
│   └── set_webhook.sh
├── terraform/
├── tests/
├── .github/workflows/
│   ├── pages.yml               # Publishes ui/
│   └── deploy.yml              # Lambda only if ALLOW_TF_APPLY=yes
└── .env.example
```
