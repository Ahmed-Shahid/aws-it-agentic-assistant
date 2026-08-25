"""
Pooled Postgres connection + pgvector similarity search, shared by every
Lambda that actually needs database access (currently: langgraph_agent for
retrieval, postapproval_agent for the resolution write).

Connects through RDS Proxy, not the raw RDS endpoint -- this is what keeps
several concurrent Step Functions executions from exhausting Postgres's own
connection limit. The DB password is fetched from Secrets Manager once per
cold start and cached at module scope, never logged or placed in a plain
environment variable.
"""
import json
import os
from contextlib import contextmanager

import boto3
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

_DB_HOST = os.environ["DB_HOST"]
_DB_NAME = os.environ["DB_NAME"]
_DB_USER = os.environ["DB_USER"]
_DB_SECRET_ARN = os.environ["DB_PASSWORD_SECRET_ARN"]

_secrets_client = boto3.client("secretsmanager")


def _build_conninfo() -> str:
    secret = json.loads(_secrets_client.get_secret_value(SecretId=_DB_SECRET_ARN)["SecretString"])
    return (
        f"host={_DB_HOST} port=5432 dbname={_DB_NAME} "
        f"user={_DB_USER} password={secret['password']}"
    )


def _configure(conn):
    # Lets psycopg adapt Python lists <-> pgvector's `vector` column type
    # directly, so callers can pass embeddings as plain lists of floats.
    try:
        register_vector(conn)
    except Exception as e:
        print(f"pgvector adapter not registered (extension may not exist yet): {e}")


# Built once per container (cold start), reused across warm invocations --
# same pattern as the compiled LangGraph graph and the Anthropic client.
# Keep max_size small: each concurrent Lambda execution environment gets
# its OWN pool, so this multiplies by concurrency rather than dividing it.
_pool = ConnectionPool(conninfo=_build_conninfo(), min_size=1, max_size=3, open=True, configure=_configure)


@contextmanager
def get_cursor():
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            yield cur


def similarity_search(embedding: list, top_k: int = 3, table: str = "document_chunks") -> list:
    """Returns the top_k rows from `table` most similar to `embedding`,
    using pgvector's cosine-distance operator (<=>).

    Assumes a schema roughly like:
        chunk_id    serial primary key,
        chunk_content     text,
        embedding   vector(1024)

    `table` is a fixed, code-controlled default -- never pass a
    user-supplied value here, since it's interpolated directly into SQL.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT chunk_id, chunk_content, 1 - (embedding <=> %s) AS similarity
            FROM %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (embedding, table, embedding, top_k),
        )
        return [{"chunk_id": r[0], "chunk_content": r[1], "similarity": r[2]} for r in cur.fetchall()]

def execute_query(query: str, params: tuple = None) -> list:
    """Executes a SQL query and returns the results as a list of dictionaries."""
    with get_cursor() as cur:
        cur.execute(query, params)
        if cur.description:
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    return []