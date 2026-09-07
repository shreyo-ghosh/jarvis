"""
DynamoDB store — replaces the local JSON file tracker from Railway version.
Table: shreyo-agent-data (created by Terraform)
Schema: pk (string) = key, val (string) = JSON-encoded value
"""

import json
import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("DYNAMO_TABLE", "shreyo-agent-data")
REGION = os.environ.get("AWS_REGION", "ap-south-1")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("dynamodb", region_name=REGION)
    return _client


class DynamoStore:
    """Simple key-value store backed by DynamoDB."""

    def get(self, key: str):
        try:
            resp = _get_client().get_item(
                TableName=TABLE_NAME,
                Key={"pk": {"S": key}}
            )
            item = resp.get("Item", {})
            if "val" in item:
                return json.loads(item["val"]["S"])
            return None
        except ClientError as e:
            logger.error(f"DynamoDB get error for key {key}: {e}")
            return None

    def put(self, key: str, value) -> bool:
        try:
            _get_client().put_item(
                TableName=TABLE_NAME,
                Item={
                    "pk": {"S": key},
                    "val": {"S": json.dumps(value, ensure_ascii=False)}
                }
            )
            return True
        except ClientError as e:
            logger.error(f"DynamoDB put error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            _get_client().delete_item(
                TableName=TABLE_NAME,
                Key={"pk": {"S": key}}
            )
            return True
        except ClientError as e:
            logger.error(f"DynamoDB delete error for key {key}: {e}")
            return False

    def append_list(self, key: str, item: dict) -> list:
        """Append an item to a list stored at key."""
        current = self.get(key) or []
        current.append(item)
        self.put(key, current)
        return current

    def get_list(self, key: str) -> list:
        return self.get(key) or []
