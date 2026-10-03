"""Approval-safe content lifecycle for Jarvis Growth OS."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import GrowthStore


ALLOWED_TRANSITIONS = {
    "draft": {"pending_approval", "archived"},
    "pending_approval": {"approved", "draft", "archived"},
    "approved": {"scheduled", "pending_approval", "archived"},
    "scheduled": {"published", "failed", "approved"},
    "published": set(),
    "failed": {"draft", "approved", "archived"},
    "archived": set(),
}


class ContentWorkflow:
    """Coordinates content state transitions and enforces approval before publishing."""

    def __init__(self, store: Optional[GrowthStore] = None):
        self.store = store or GrowthStore()

    def create_draft(
        self,
        campaign_id: str,
        channel: str,
        content_type: str,
        title: str,
        body: str,
        scheduled_for: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.store.create_content(
            campaign_id=campaign_id,
            channel=channel,
            content_type=content_type,
            title=title,
            body=body,
            scheduled_for=scheduled_for,
        )

    def submit_for_approval(self, content_id: str, actor: str = "jarvis") -> Dict[str, Any]:
        return self._transition(content_id, "pending_approval", actor)

    def approve(self, content_id: str, actor: str) -> Dict[str, Any]:
        if actor in ("", "jarvis", None):
            raise ValueError("A named human approver is required")
        return self._transition(content_id, "approved", actor)

    def schedule(self, content_id: str, scheduled_for: str, actor: str = "jarvis") -> Dict[str, Any]:
        item = self.store.get_content(content_id)
        if not item:
            raise ValueError("Content not found")
        if item.get("status") != "approved":
            raise ValueError("Only approved content can be scheduled")
        return self.store.transition_content(
            content_id,
            "scheduled",
            actor=actor,
            scheduled_for=scheduled_for,
        )

    def mark_published(self, content_id: str, external_post_id: str, actor: str = "publisher") -> Dict[str, Any]:
        return self.store.transition_content(
            content_id,
            "published",
            actor=actor,
            external_post_id=external_post_id,
        )

    def mark_failed(self, content_id: str, error_message: str, actor: str = "publisher") -> Dict[str, Any]:
        return self.store.transition_content(
            content_id,
            "failed",
            actor=actor,
            error_message=error_message,
        )

    def _transition(self, content_id: str, new_status: str, actor: str) -> Dict[str, Any]:
        item = self.store.get_content(content_id)
        if not item:
            raise ValueError("Content not found")

        current_status = item.get("status", "draft")
        if new_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ValueError(f"Invalid transition: {current_status} -> {new_status}")

        return self.store.transition_content(content_id, new_status, actor=actor)
