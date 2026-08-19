import json
import boto3

_secrets_client = boto3.client("secretsmanager")
_cache = {}

def get_secret(secret_arn: str, secret_key: str = None) -> str:
    """Fetches a secret value from AWS Secrets Manager."""
    if secret_arn not in _cache:
        _cache[secret_arn] = json.loads(_secrets_client.get_secret_value(SecretId=secret_arn)["SecretString"])
    secret = _cache[secret_arn]
    if secret_key is not None:
        return secret[secret_key]
    return secret