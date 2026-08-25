"""
Embedding generation via Amazon Bedrock's Titan Text Embeddings model.

Claude has no embeddings endpoint of its own, so something else has to
generate vectors for pgvector similarity search. This uses Bedrock rather
than a third vendor (e.g. Voyage AI) so the project doesn't need a second
API key alongside Anthropic and Jira -- just an IAM grant.
"""
import json

import boto3

_bedrock = boto3.client("bedrock-runtime")
_MODEL_ID = "amazon.titan-embed-text-v2:0"


def embed(text: str) -> list:
    print(f"Generating embedding for text: {text}")
    response = _bedrock.invoke_model(
        modelId=_MODEL_ID,
        body=json.dumps({"inputText": text}),
    )
    print(f"Bedrock response: {response}")
    payload = json.loads(response["body"].read())
    return payload["embedding"]
