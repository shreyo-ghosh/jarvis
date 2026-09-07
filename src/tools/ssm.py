"""
tools/ssm.py — fetch secrets from AWS SSM Parameter Store, with local .env fallback.
"""
import os

try:
    import boto3
    _ssm = boto3.client("ssm")
except Exception:
    _ssm = None

PREFIX = os.environ.get("SSM_PREFIX", "/shreyo-agent")


def get_secret(name: str) -> str:
    local_value = os.environ.get(name)
    if local_value:
        return local_value

    if _ssm is None:
        raise RuntimeError(f"No boto3 client and no local env var for {name}")

    param_name = f"{PREFIX}/{name}"
    response = _ssm.get_parameter(Name=param_name, WithDecryption=True)
    value = response["Parameter"]["Value"]
    return value
