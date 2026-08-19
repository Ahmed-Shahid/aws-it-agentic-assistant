import json
import os
from contextlib import contextmanager

import boto3
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

_secrets_client = boto3.client("secretsmanager")

def get_secret(secret_arn: str, secret_key: str = None) -> str:
    """Fetches a secret value from AWS Secrets Manager."""
    secret = json.loads(_secrets_client.get_secret_value(SecretId=secret_arn)["SecretString"])
    if secret_key is not None:
        return secret[secret_key]
    return secret