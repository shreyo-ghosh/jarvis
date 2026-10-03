"""API Gateway Lambda handlers for the Jarvis Growth OS dashboard.

Expected routes:
  GET    /growth/content
  POST   /growth/content
  POST   /growth/content/{id}/submit
  POST   /growth/content/{id}/approve
  POST   /growth/content/{id}/schedule
  GET    /growth/campaigns
  POST   /growth/campaigns
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from .workflow import ContentWorkflow


def _response(status_code: int, body: Any) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": os.environ.get("UI_ORIGIN", "*"),
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body, default=str),
    }


def _body(event: Dict[str, Any]) -> Dict[str, Any]:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64

        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw or "{}")


def _path_parameters(event: Dict[str, Any]) -> Dict[str, str]:
    return event.get("pathParameters") or {}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """API Gateway proxy integration entry point."""

    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return _response(204, {})

    workflow = ContentWorkflow()
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("requestContext", {}).get("http", {}).get("path", "")
    params = _path_parameters(event)

    try:
        if path.endswith("/growth/content") and method == "GET":
            status = (event.get("queryStringParameters") or {}).get("status")
            return _response(200, {"items": workflow.store.list_content(status)})

        if path.endswith("/growth/content") and method == "POST":
            payload = _body(event)
            item = workflow.create_draft(
                campaign_id=payload["campaign_id"],
                channel=payload["channel"],
                content_type=payload["content_type"],
                title=payload["title"],
                body=payload["body"],
                scheduled_for=payload.get("scheduled_for"),
            )
            return _response(201, item)

        if "/growth/content/" in path and method == "POST":
            content_id = params.get("id") or path.rstrip("/").split("/")[-2]
            payload = _body(event)
            action = path.rstrip("/").split("/")[-1]

            if action == "submit":
                return _response(200, workflow.submit_for_approval(content_id, payload.get("actor", "jarvis")))

            if action == "approve":
                return _response(200, workflow.approve(content_id, payload.get("actor", "")))

            if action == "schedule":
                return _response(
                    200,
                    workflow.schedule(
                        content_id,
                        payload["scheduled_for"],
                        payload.get("actor", "jarvis"),
                    ),
                )

        if path.endswith("/growth/campaigns") and method == "GET":
            return _response(200, {"items": workflow.store.list_campaigns()})

        if path.endswith("/growth/campaigns") and method == "POST":
            payload = _body(event)
            item = workflow.store.create_campaign(
                name=payload["name"],
                objective=payload["objective"],
                channel=payload["channel"],
                start_date=payload["start_date"],
                end_date=payload["end_date"],
            )
            return _response(201, item)

        return _response(404, {"error": "Route not found", "path": path, "method": method})

    except KeyError as exc:
        return _response(400, {"error": f"Missing required field: {exc}"})
    except ValueError as exc:
        return _response(400, {"error": str(exc)})
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return _response(500, {"error": "Internal error", "detail": str(exc)})
