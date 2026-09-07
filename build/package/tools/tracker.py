"""
tools/tracker.py — revenue + task logging via DynamoDB.
"""
import os
import datetime

try:
    import boto3
    _dynamo = boto3.resource("dynamodb")
    TABLE_NAME = os.environ.get("DYNAMO_TABLE", "shreyo-agent-tracker")
    _table = _dynamo.Table(TABLE_NAME)
except Exception:
    _table = None


def _now() -> str:
    return datetime.datetime.utcnow().isoformat()


def log_revenue(amount: float, source: str) -> str:
    if _table is None:
        return "DynamoDB not configured (local test mode)."
    _table.put_item(Item={
        "record_type": "revenue",
        "timestamp": _now(),
        "amount": str(amount),
        "source": source,
    })
    return f"Logged ₹{amount} from {source}."


def log_task(description: str) -> str:
    if _table is None:
        return "DynamoDB not configured (local test mode)."
    _table.put_item(Item={
        "record_type": "task",
        "timestamp": _now(),
        "description": description,
        "done": "false",
    })
    return f"Task logged: {description}"


def revenue_summary() -> str:
    if _table is None:
        return "DynamoDB not configured (local test mode)."
    import boto3.dynamodb.conditions as cond
    response = _table.query(
        KeyConditionExpression=cond.Key("record_type").eq("revenue")
    )
    items = response.get("Items", [])
    total = sum(float(i["amount"]) for i in items)
    return f"Total logged revenue: ₹{total:.2f} across {len(items)} entries."
