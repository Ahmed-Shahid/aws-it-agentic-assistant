from enum import Enum

from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from atlassian import Jira

from common.models import IntakeContextResponse, ClaudeAIModels
from pydantic import BaseModel
from anthropic import Anthropic
import os

from common.secrets import get_secret

_CLAUDE_SECRET_ARN = os.environ["CLAUDE_API_KEY_SECRET_ARN"]
_JIRA_SECRET_ARN = os.environ["JIRA_TOKEN_SECRET_ARN"]
client = Anthropic(api_key=get_secret(secret_arn=_CLAUDE_SECRET_ARN))

class TicketDetailResponse(BaseModel):
    title: Optional[str]
    summary: Optional[str]

class AgentState(TypedDict, total=False):
    job_id: str
    action: str
    classification: str
    raw_input: str
    retrieved_chunks: Optional[list]
    ticket_id: Optional[str]
    title: Optional[str]
    summary: Optional[str]
    proposed_resolution: Optional[str]

class AgentAction(Enum):
    INITIALIZE = "initialize"
    UPDATE = "update"
    REQUEST_APPROVAL = "request_approval"
    APPROVE = "approve"
    REJECT = "reject"
    RESOLVE = "resolve"

"""
HELPER FUNCTIONS
"""
def add_ticket_comment(state: AgentState):
    # Placeholder for adding a comment to a ticket
    print(f"Adding comment to ticket with state: {state}")
    return {"ticket_id": "TICKET-12345", "status": "comment added"}

def get_tools():
    return [{
        "name": "get_ticket_creation_details",
        "description": ("Propose a ticket title and summary based on the input and retrieved chunks."),
        "input_schema": TicketDetailResponse.model_json_schema()
    }]

def get_system_prompt():
    return (
        "You are an AI-enabled corporate IT ticketing assistant that creates and writes tickets based on several inputs. "
        "You will be provided with a classification, raw user input (raw_input), and retrieved chunks of corporate runbook"
        " documentation (retrieved_chunks). Your task is to propose a ticket title less than 60 characters, and a summary less "
        "than 200 characters."
    )

def initialize_jira():
    # ref: https://atlassian-python-api.readthedocs.io/
    jira_secret = get_secret(secret_arn=_JIRA_SECRET_ARN)
    return Jira(
        url=jira_secret["server"],
        username=jira_secret["email"],
        password=jira_secret["token"],
        cloud=True
    )

"""
NODES
"""
def route_action(state: AgentState):
    action = state.get('action', 'unknown')
    return {'action': action}

def create_ticket(state: AgentState):
    print(f"Creating ticket with state: {state}")
    jira = initialize_jira()
    ticket = jira.issue_create({'summary': state.get('title', 'No Title'),
                       'description': (f"DESCRIPTION:\n{state.get('summary', 'No Summary')}"
                                       f"\n\nCLASSIFICATION:\n{state.get('classification', 'unknown')}"
                                       f"\n\nJOB ID:\n{state.get('job_id', 'unknown')}"
                                       f"\n\nRAW INPUT:\n{state.get('raw_input', '')}"
                                       f"\n\nRETRIEVED CHUNKS:\n{str(state.get('retrieved_chunks', []))}"
                                       ),
                       'project': {'key': 'KAN'},
                       'issuetype': {'name': 'Task'}})

    jira.issue_add_comment
    return {"ticket_id": ticket["key"]}

def get_ticket_creation_details(state: AgentState):
    print(f"Getting ticket creation details for state: {state}")
    response = client.messages.create(
            model = ClaudeAIModels.medium,
            max_tokens = 1000,
            system=get_system_prompt(),
            tools = get_tools(),
            tool_choice = {"type": "tool", "name": "get_ticket_creation_details"},
            messages = [
                {
                    "role": "user",
                    "content": (f"raw_input: {state.get('raw_input', '')}"
                                f"classification: {state.get('classification', '')}"
                                f"retrieved_chunks: {str(state.get('retrieved_chunks', ''))}")
                }
            ]
        )
    tool_block = next(b for b in response.content if b.type == "tool_use")
    result = tool_block.input
    return {"title": result.get("title", ""), "summary": result.get("summary", "")}

def retrieve_ticket(state: AgentState):
    # Placeholder for ticket retrieval logic
    print(f"Retrieving ticket with state: {state}")
    return {"ticket_id": "TICKET-12345", "status": "retrieved"}

def update_ticket(state: AgentState):
    # Placeholder for ticket update logic
    print(f"Updating ticket with state: {state}")
    return {"ticket_id": "TICKET-12345", "status": "updated"}

def move_to_proposal(state: AgentState):
    # Placeholder for moving ticket to proposal state
    print(f"Moving ticket to proposal with state: {state}")
    return {"action": "propose"}

def move_to_pending_approval(state: AgentState):
    # Placeholder for moving ticket to pending approval
    print(f"Moving ticket to pending approval with state: {state}")
    return {"ticket_id": "TICKET-12345", "status": "pending approval"}

def request_approval(state: AgentState):
    # Placeholder for requesting approval for a ticket
    print(f"Requesting approval for ticket with state: {state}")
    return {"ticket_id": "TICKET-12345", "status": "approval requested"}

def mark_ticket_approved(state: AgentState):
    # Placeholder for marking ticket as approved
    print(f"Marking ticket as approved with state: {state}")
    return {"ticket_id": "TICKET-12345", "status": "approved"}

def mark_ticket_rejected(state: AgentState):
    # Placeholder for marking ticket as rejected
    print(f"Marking ticket as rejected with state: {state}")
    return {"ticket_id": "TICKET-12345", "status": "rejected"}

def resolve_ticket(state: AgentState):
    # Placeholder for resolving a ticket
    print(f"Resolving ticket with state: {state}")
    return {"ticket_id": "TICKET-12345", "status": "resolved"}

def close_ticket(state: AgentState):
    # Placeholder for closing a ticket
    print(f"Closing ticket with state: {state}")
    return {"ticket_id": "TICKET-12345", "status": "closed"}

graph = StateGraph(AgentState)

graph.add_node("route_action", route_action)
graph.add_node("create_ticket", create_ticket)
graph.add_node("get_ticket_creation_details", get_ticket_creation_details)
graph.add_node("retrieve_ticket", retrieve_ticket)
graph.add_node("update_ticket", update_ticket)
graph.add_node("add_ticket_comment", add_ticket_comment)
graph.add_node("move_to_proposal", move_to_proposal)
graph.add_node("request_approval", request_approval)
graph.add_node("move_to_pending_approval", move_to_pending_approval)
graph.add_node("mark_ticket_approved", mark_ticket_approved)
graph.add_node("resolve_ticket", resolve_ticket)
graph.add_node("mark_ticket_rejected", mark_ticket_rejected)
graph.add_node("close_ticket", close_ticket)

"""
route_action -> get_ticket_creation_details -> create_ticket -> move_to_proposal -> END
route_action -> update_ticket -> move_to_pending_approval -> END
route_action -> request_approval -> END
route_action -> mark_ticket_approved -> END
route_action -> mark_ticket_rejected -> close_ticket -> END
route_action -> resolve_ticket -> close_ticket -> END
route_action -> retrieve_ticket -> END
"""

graph.set_entry_point("route_action")
graph.add_conditional_edges("route_action", route_action, {
    AgentAction.INITIALIZE.value: "get_ticket_creation_details",
    AgentAction.UPDATE.value: "update_ticket",
    AgentAction.REQUEST_APPROVAL.value: "request_approval",
    AgentAction.APPROVE.value: "mark_ticket_approved",
    AgentAction.REJECT.value: "mark_ticket_rejected",
    AgentAction.RESOLVE.value: "resolve_ticket",
})
graph.add_edge("get_ticket_creation_details", "create_ticket")
graph.add_edge("create_ticket", "move_to_proposal")
graph.add_edge("move_to_proposal", END)
graph.add_edge("update_ticket", "move_to_pending_approval")
graph.add_edge("move_to_pending_approval", END)
graph.add_edge("request_approval", END)
graph.add_edge("mark_ticket_approved", END)
graph.add_edge("mark_ticket_rejected", "close_ticket")
graph.add_edge("resolve_ticket", "close_ticket")
graph.add_edge("close_ticket", END)
graph.add_edge("retrieve_ticket", END)

app = graph.compile()

def handler(event, context):
    print("Received event: " + str(event))
    # Process the event here

    state: AgentState = {
        "job_id": event.get("job_id", "unknown"),
        "action": event.get("action", "unknown"),
        "classification": event.get("classification", "unknown"),
        "raw_input": event.get("raw_input", ""),
        "retrieved_chunks": event.get("retrieved_chunks", []),
        "proposed_resolution": event.get("proposed_resolution", None),
    }

    try:
        result = app.invoke(state)
    except Exception as e:
        print(f"Error invoking state graph: {e}")
        return {
            'statusCode': 500,
            'body': str(e),
            'state': state,
        }

    return {
        'statusCode': 200,
        'body': str(result),
        'action': state['action'],
    }