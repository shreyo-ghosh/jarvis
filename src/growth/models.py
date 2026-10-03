"""DynamoDB data access for the Jarvis Growth OS.

Phase 1 uses a single-table design so it can be deployed alongside the
existing Jarvis DynamoDB infrastructure without requiring a new table.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Attr


TABLE_NAME = os.environ.get("GROWTH_OS_TABLE", "shreyo-jarvis-state")


class GrowthStore:
    """Persistence layer for campaigns, content, approvals, and metrics."""

    def __init__(self, table_name: Optional[str] = None, endpoint_url: Optional[str] = None):
        self.table_name = table_name or TABLE_NAME
        dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url)
        self.table = dynamodb.Table(self.table_name)

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def create_campaign(
        self,
        name: str,
        objective: str,
        channel: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        campaign_id = self._id("camp")
        item = {
            "pk": f"CAMPAIGN#{campaign_id}",
            "sk": "METADATA",
            "gsi1_pk": "CAMPAIGNS",
            "gsi1_sk": start_date,
            "campaign_id": campaign_id,
            "name": name,
            "objective": objective,
            "channel": channel,
            "start_date": start_date,
            "end_date": end_date,
            "status": "active",
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self.table.put_item(Item=item)
        return item

    def list_campaigns(self) -> List[Dict[str, Any]]:
        response = self.table.scan(FilterExpression=Attr("gsi1_pk").eq("CAMPAIGNS"))
        return sorted(response.get("Items", []), key=lambda x: x.get("created_at", ""))

    def create_content(
        self,
        campaign_id: str,
        channel: str,
        content_type: str,
        title: str,
        body: str,
        scheduled_for: Optional[str] = None,
        created_by: str = "jarvis",
    ) -> Dict[str, Any]:
        content_id = self._id("content")
        now = self._now()
        item = {
            "pk": f"CONTENT#{content_id}",
            "sk": "METADATA",
            "gsi1_pk": "CONTENT_QUEUE",
            "gsi1_sk": now,
            "content_id": content_id,
            "campaign_id": campaign_id,
            "channel": channel,
            "content_type": content_type,
            "title": title,
            "body": body,
            "scheduled_for": scheduled_for,
            "status": "draft",
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
            "history": [{"status": "draft", "at": now, "actor": created_by}],
        }
        self.table.put_item(Item=item)
        return item

    def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        response = self.table.get_item(Key={"pk": f"CONTENT#{content_id}", "sk": "METADATA"})
        return response.get("Item")

    def list_content(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        response = self.table.scan(FilterExpression=Attr("gsi1_pk").eq("CONTENT_QUEUE"))
        items = response.get("Items", [])
        if status:
            items = [item for item in items if item.get("status") == status]
        return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)

    def transition_content(
        self,
        content_id: str,
        new_status: str,
        actor: str = "jarvis",
        scheduled_for: Optional[str] = None,
        external_post_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        item = self.get_content(content_id)
        if not item:
            return None

        now = self._now()
        update_expression = ["SET #status = :status", "updated_at = :updated_at"]
        expression_values: Dict[str, Any] = {
            ":status": new_status,
            ":updated_at": now,
        }
        expression_names = {"#status": "status"}

        history = item.get("history", [])
        history.append({"status": new_status, "at": now, "actor": actor})
        update_expression.append("history = :history")
        expression_values[":history"] = history

        if scheduled_for is not None:
            update_expression.append("scheduled_for = :scheduled_for")
            expression_values[":scheduled_for"] = scheduled_for

        if external_post_id is not None:
            update_expression.append("external_post_id = :external_post_id")
            expression_values[":external_post_id"] = external_post_id

        if error_message is not None:
            update_expression.append("error_message = :error_message")
            expression_values[":error_message"] = error_message

        self.table.update_item(
            Key={"pk": f"CONTENT#{content_id}", "sk": "METADATA"},
            UpdateExpression=" ".join(update_expression),
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
        )
        return self.get_content(content_id)

    def record_metric(
        self,
        content_id: str,
        metric_date: str,
        impressions: int = 0,
        reach: int = 0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        clicks: int = 0,
        leads: int = 0,
    ) -> Dict[str, Any]:
        metric_id = self._id("metric")
        item = {
            "pk": f"METRIC#{metric_id}",
            "sk": "METADATA",
            "gsi1_pk": f"CONTENT_METRICS#{content_id}",
            "gsi1_sk": metric_date,
            "content_id": content_id,
            "metric_date": metric_date,
            "impressions": impressions,
            "reach": reach,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "clicks": clicks,
            "leads": leads,
            "created_at": self._now(),
        }
        self.table.put_item(Item=item)
        return item

    def list_metrics(self, content_id: str) -> List[Dict[str, Any]]:
        response = self.table.scan(
            FilterExpression=Attr("gsi1_pk").eq(f"CONTENT_METRICS#{content_id}")
        )
        return sorted(response.get("Items", []), key=lambda x: x.get("metric_date", ""))
