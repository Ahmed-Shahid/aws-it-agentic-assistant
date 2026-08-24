from common.db import execute_query
from common.models import AgentState, Classifications, ClaudeAIModels, ProposalResponse
from common.secrets import get_secret
from common.status import get_status, write_state_to_status
from anthropic import Anthropic
from langgraph.graph import StateGraph, END
from typing import Optional
from enum import Enum
import os
from datetime import datetime, timezone, date

_CLAUDE_SECRET_ARN = os.environ["CLAUDE_API_KEY_SECRET_ARN"]
client = Anthropic(api_key=get_secret(secret_arn=_CLAUDE_SECRET_ARN, secret_key="api_key"))

class AgentAction(Enum):
    PROPOSE = "propose"
    APPLY = "apply"
    UNKNOWN = "unknown"

"""
HELPER FUNCTIONS
"""
def load_state_from_job_id(job_id: str) -> dict:
    # Placeholder for loading state from a job ID
    print(f"Loading state for job ID: {job_id}")
    status_record = get_status(job_id)
    return status_record

def get_tools():
    return [{
        "name": "propose_resolution",
        "description": ("Create an issue resolution proposal and verify the classification based on the provided information"),
        "input_schema": ProposalResponse.model_json_schema()
    }]

def get_system_prompt():
    return (
        "You are an AI-enabled corporate IT support agent that updates corporate data/profiles to resolve user issues. "
        "Everything you do absolutely must be grounded in retrieved corporate documentation (retrieved_chunks) and underlying corporate data for users, "
        "devices, IAM accounts, and VPN profiles. You must not hallucinate or make up any information. "
        "You will be provided with a classification, raw user input description of issue (raw_input), retrieved chunks, and underlying data. "
        "Your task is to propose a numbered list of resolution steps to resolve the issue, and verify the input classification is correct."
        " If no corrections are possible with the underlying data, propose a new classification. "
        "Each step should be actionable and concise; less than 400 characters. If you cannot propose a resolution, respond with 'No resolution proposed'. "
    )

def get_audit_log_string(log_entry: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {log_entry}"
    return log_entry

def retrieve_underlying_data(user_id: str, device_id: str) -> str:
    print(f"Retrieving underlying data for user_id: {user_id}, device_id: {device_id}")
    user_results = execute_query("SELECT * FROM users WHERE user_id = %s", (user_id,))
    iam_results = execute_query("SELECT * FROM iam_accounts WHERE user_id = %s", (user_id,))
    vpn_profile_results = execute_query("SELECT * FROM vpn_profiles WHERE user_id = %s", (user_id,))
    device_results = execute_query("SELECT * FROM devices WHERE device_id = %s", (device_id,))
    device_results += execute_query("SELECT * FROM devices WHERE user_id = %s", (user_id,))
    return (f"User Data: {user_results}, IAM Account Data: {iam_results}, VPN Profile Data: {vpn_profile_results}, Device Data: {device_results}")

#PLACEHOLDER
def get_resolution_steps(classification: str) -> Optional[str]:
    if classification == Classifications.PASSWORD_RESET.value:
        return (
            "1. Verify the user's identity. "
            "2. Reset the user's password using the corporate password management system. "
            "3. Notify the user of the password reset and provide instructions for setting a new password."
        )
    elif classification == Classifications.IAM_ACCOUNT_UNLOCK.value:
        return (
            "1. Verify the user's identity. "
            "2. Unlock the user's IAM account using the corporate IAM management system. "
            "3. Notify the user that their account has been unlocked and provide any necessary instructions."
        )
    elif classification == Classifications.VPN_ACCESS_RESET.value:
        return (
            "1. Verify the user's identity. "
            "2. Reset the user's VPN access credentials using the corporate VPN management system. "
            "3. Notify the user of the VPN access reset and provide instructions for setting new credentials."
        )
    return None

"""
NODES
"""
def route_action(state: AgentState):
    return {}

def action_router(state: AgentState) -> str:
    return state.get("action", "unknown")

def route_to_workflow(state: AgentState):
    job_id = state.get("job_id")
    if not job_id:
        raise ValueError("Job ID is required to retrieve status.")
    current_state = load_state_from_job_id(job_id)
    state.update(current_state)
    state["action"] = "apply"
    state["resolution_audit_log"] = [get_audit_log_string("Retrieved status and updated state.")]
    return state

def workflow_router(state: AgentState) -> str:
    classification = state.get("classification", "unknown")
    if classification not in [x.value for x in Classifications]:
        return Classifications.UNKNOWN.value
    return classification

def retrieve_status(state: AgentState):
    print(f"retrieve_status begin state: {state}")
    job_id = state.get("job_id")
    if not job_id:
        raise ValueError("Job ID is required to retrieve status.")
    current_state = load_state_from_job_id(job_id)
    state.update(current_state)
    state["action"] = "propose"
    state["resolution_audit_log"] = [get_audit_log_string("Retrieved status and updated state.")]
    print(f"retrieve_status end state: {state}")
    return state

def generate_proposal(state: AgentState):
    # Placeholder for generating a proposal based on the state
    # This could involve calling an AI model or other logic to create a proposal
    print(f"generate_proposal begin state: {state}")
    audit_log = state.get("resolution_audit_log", [])
    audit_log.append(get_audit_log_string("Retrieving user/device data based on current state."))
    underlying_data = retrieve_underlying_data(state.get("user_id"), state.get("device_id"))
    print(f"Generating proposal for state: {state}")
    audit_log.append(get_audit_log_string(f"Generating proposal"))
    response = client.messages.create(
                model = ClaudeAIModels.medium,
                max_tokens = 1000,
                system=get_system_prompt(),
                tools = get_tools(),
                tool_choice = {"type": "tool", "name": "propose_resolution"},
                messages = [
                    {
                        "role": "user",
                        "content": (f"raw_input: {state.get('raw_input', '')}\n"
                                    f"classification: {state.get('classification', '')}\n"
                                    f"retrieved_chunks: {str(state.get('retrieved_chunks', ''))}\n"
                                    f"underlying_data: {underlying_data}\n")
                    }
                ]
            )
    audit_log.append(get_audit_log_string("Proposal generated successfully."))
    tool_block = next(b for b in response.content if b.type == "tool_use")
    result = tool_block.input
    new_classification = result.get("new_classification", '')
    if new_classification and new_classification != state.get("classification"):
        audit_log.append(get_audit_log_string(f"Classification updated from {state.get('classification')} to {new_classification}."))
        state["classification"] = new_classification
    print(f"generate_proposal end state: {state}")
    return {"proposed_resolution": result.get("proposal"), "classification": state.get("classification"), "resolution_audit_log": audit_log}

def password_reset_workflow(state: AgentState):
    print(f"Executing password reset workflow for state: {state}")
    job_id = state.get("job_id")
    user_id = state.get("user_id")
    audit_log = state.get("resolution_audit_log", [])
    audit_log.append(get_audit_log_string(f"Resetting password for user_id: {user_id}"))
    execute_query("UPDATE iam_accounts SET last_password_change = %s WHERE user_id = %s", (date.today().isoformat(), user_id,))
    audit_log.append(get_audit_log_string(f"Password reset completed for user_id: {user_id}"))
    print(f"password_reset_workflow end state: {state}")
    return {"resolution_audit_log": audit_log, 'action': 'resolve'}

def iam_account_unlock_workflow(state: AgentState):
    print(f"Executing IAM account unlock workflow for state: {state}")
    job_id = state.get("job_id")
    user_id = state.get("user_id")
    audit_log = state.get("resolution_audit_log", [])
    audit_log.append(get_audit_log_string(f"Unlocking IAM account for user_id: {user_id}"))
    execute_query("UPDATE iam_accounts SET account_status = 'Active' WHERE user_id = %s", (user_id,))
    audit_log.append(get_audit_log_string(f"IAM account unlocked for user_id: {user_id}"))
    print(f"iam_account_unlock_workflow end state: {state}")
    return {"resolution_audit_log": audit_log, 'action': 'resolve'}

def vpn_access_reset_workflow(state: AgentState):
    print(f"Executing VPN access reset workflow for state: {state}")
    job_id = state.get("job_id")
    user_id = state.get("user_id")
    audit_log = state.get("resolution_audit_log", [])
    audit_log.append(get_audit_log_string(f"Resetting VPN access for user_id: {user_id}"))
    execute_query("UPDATE vpn_profiles SET vpn_status = 'Enabled', certificate_status = 'Valid', device_compliance = 'Pass' WHERE user_id = %s", (user_id,))
    audit_log.append(get_audit_log_string(f"VPN access reset completed for user_id: {user_id}"))
    print(f"vpn_access_reset_workflow end state: {state}")
    return {"resolution_audit_log": audit_log, 'action': 'resolve'}

def unknown_workflow(state: AgentState):
    print(f"Executing unknown workflow for state: {state}")
    audit_log = state.get("resolution_audit_log", [])
    audit_log.append(get_audit_log_string("Unknown or action encountered. No resolution applied."))
    audit_log.append(get_audit_log_string(f"classification: {state.get('classification')}, action: {state.get('action')}"))
    return {"resolution_audit_log": audit_log}

graph = StateGraph(AgentState)

graph.add_node("route_action", route_action)
graph.add_node("retrieve_status", retrieve_status)
graph.add_node("generate_proposal", generate_proposal)
graph.add_node("route_to_workflow", route_to_workflow)
graph.add_node("password_reset_workflow", password_reset_workflow)
graph.add_node("iam_account_unlock_workflow", iam_account_unlock_workflow)
graph.add_node("vpn_access_reset_workflow", vpn_access_reset_workflow)
graph.add_node("unknown_workflow", unknown_workflow)

"""
route_action -> retrieve_status -> generate_proposal ->  END
route_action -> route_to_workflow -> password_reset_workflow -> END
route_action -> route_to_workflow -> iam_account_unlock_workflow -> END
route_action -> route_to_workflow -> vpn_access_reset_workflow -> END
route_action -> route_to_workflow -> unknown -> END
"""

graph.set_entry_point("route_action")
graph.add_conditional_edges("route_action", action_router, {
    AgentAction.PROPOSE.value: "retrieve_status",
    AgentAction.APPLY.value: "route_to_workflow",
    AgentAction.UNKNOWN.value: "unknown_workflow",
})
graph.add_conditional_edges("route_to_workflow", workflow_router, {
    Classifications.PASSWORD_RESET.value: "password_reset_workflow",
    Classifications.IAM_ACCOUNT_UNLOCK.value: "iam_account_unlock_workflow",
    Classifications.VPN_ACCESS_RESET.value: "vpn_access_reset_workflow",
    Classifications.UNKNOWN.value: "unknown_workflow",
})
graph.add_edge("retrieve_status", "generate_proposal")
graph.add_edge("generate_proposal", END)
graph.add_edge("password_reset_workflow", END)
graph.add_edge("iam_account_unlock_workflow", END)
graph.add_edge("vpn_access_reset_workflow", END)
graph.add_edge("unknown_workflow", END)

app = graph.compile()


"""
HANDLER
"""

def handler(event, context):
    print("Received event: " + str(event))
    # Process the event here

    state: AgentState = {
        "job_id": event.get("job_id", "unknown"),
        "action": event.get("action", "unknown"),
    }

    result = app.invoke(state)

    print(f"issue_resolution lambda final result: {result}")
    write_state_to_status(result)  # Write the updated state to the status table

    return {
        'job_id': state.get("job_id", "unknown"),
        **result
    }