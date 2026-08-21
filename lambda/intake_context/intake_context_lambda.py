import json

import boto3

from common.models import IntakeContextResponse, ClaudeAIModels
from pydantic import BaseModel
from anthropic import Anthropic
import os

from common.secrets import get_secret

_CLAUDE_SECRET_ARN = os.environ["CLAUDE_API_KEY_SECRET_ARN"]
client = Anthropic(api_key=get_secret(secret_arn=_CLAUDE_SECRET_ARN))

class ActionClassification(BaseModel):
    action: str
    classification: str

ACTIONS = ["initialize", "upload"]
CLASSIFICATIONS = ["password_reset", "iam_account_unlock", "vpn_access_reset", "unknown"]

def handler(event, context):
    print("Received event: " + str(event))
    # Process the event here
    job_id = event.get('job_id', 'unknown')
    input_data = event.get('input', '')
    user_id = event.get('user_id', 'unknown')
    processed_input = process_input(input_data)
    response = IntakeContextResponse(
        job_id=job_id,
        user_id=user_id,
        statusCode=200,
        action=processed_input.get('action', 'initialize'),
        classification=processed_input.get('classification', 'unknown'),
        raw_input=input_data,
        retrieved_chunks=processed_input.get('retrieved_chunks', [])
    )
    return response.model_dump()

def get_rag_chunks(input_data: str):
    # Placeholder for the function to get RAG chunks
    return ""

def process_input(input_data: str):
    response = client.messages.create(
        model = ClaudeAIModels.medium,
        max_tokens = 1000,
        system=get_system_prompt(),
        tools = get_tools(),
        tool_choice = {"type": "tool", "name": "propose_action_classification"},
        messages = [
            {
                "role": "user",
                "content": (f"Input: {input_data}"
                            f"Retrieved Chunks: {get_rag_chunks(input_data)}")
            }
        ]
    )
    tool_block = next(b for b in response.content if b.type == "tool_use")
    return tool_block.input

def get_tools():
    return [{
        "name": "propose_action_classification",
        "description": ("Propose an action and classification based on the input and retrieved chunks."
                        f"The action must be one of {ACTIONS} and the classification must be one of {CLASSIFICATIONS}."),
        "input_schema": ActionClassification.model_json_schema()
    }]

def get_system_prompt():
    return (
        "You are an AI-enabled corporate IT ticketing assistant that helps classify user requests and propose actions. "
        f"The action must be one of {ACTIONS} and the classification must be one of {CLASSIFICATIONS}. "
        "initialize represents the start of a new IT ticketing workflow, and upload represents the action of uploading a runbook document for later rag retrieval. "
        "You will receive input data and retrieved chunks, and you should return a JSON object with 'action' and 'classification'."
    )