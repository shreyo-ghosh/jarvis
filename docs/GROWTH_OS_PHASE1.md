# Jarvis Growth OS — Phase 1

Phase 1 adds the foundation for a business-growth operating system on top of the existing Jarvis Telegram bot.

## What this phase delivers

- A DynamoDB-backed content and campaign model.
- An approval-safe content lifecycle:
  `draft → pending_approval → approved → scheduled → published | failed`.
- API Gateway handlers for the future Jarvis web dashboard.
- A static dashboard shell for content creation, pipeline visibility, approvals, and scheduling.
- Metric storage for later Instagram, LinkedIn, website, and revenue attribution.

## Intentional scope boundaries

This phase does **not** publish to Instagram or LinkedIn, modify the existing Telegram bot, or change the current Terraform deployment. It establishes the safe workflow and UI foundation first.

## Content lifecycle

```text
draft
  └─> pending_approval
        ├─> approved
        │     └─> scheduled
        │           ├─> published
        │           └─> failed
        └─> draft
```

Publishing is intentionally separated from approval. A publisher worker must only transition content from `scheduled` to `published` after a successful external API call.

## API contract

| Method | Path | Purpose |
|---|---|---|
| GET | `/growth/content` | List content; optional `?status=pending_approval` |
| POST | `/growth/content` | Create a draft |
| POST | `/growth/content/{id}/submit` | Submit draft for approval |
| POST | `/growth/content/{id}/approve` | Approve content; requires a named human approver |
| POST | `/growth/content/{id}/schedule` | Schedule approved content |
| GET | `/growth/campaigns` | List campaigns |
| POST | `/growth/campaigns` | Create a campaign |

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `GROWTH_OS_TABLE` | DynamoDB table used by Growth OS | `shreyo-jarvis-state` |
| `UI_ORIGIN` | Allowed browser origin for CORS | `*` |

## UI configuration

Before deploying the dashboard, set the API base URL:

```html
<script>
  window.JARVIS_API_BASE = "https://your-api-gateway-id.execute-api.ap-south-1.amazonaws.com/prod";
</script>
```

For local development, serve the `ui/` directory and point `JARVIS_API_BASE` to a local API emulator or deployed API Gateway stage.

## Next implementation steps

1. Add Terraform resources for the `/growth/*` API routes and Lambda integration.
2. Add an EventBridge-scheduled research agent.
3. Connect the content workflow to Instagram Graph API publishing.
4. Add LinkedIn Company Page publishing after API access approval.
5. Add metrics ingestion and weekly performance reporting.
