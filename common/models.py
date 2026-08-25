from enum import Enum
from pydantic import BaseModel
from typing import Optional, TypedDict

class ClaudeAIModels:
    small = "claude-haiku-4-5"
    medium = "claude-sonnet-5"
    large = "claude-opus-5"

class Classifications(Enum):
    PASSWORD_RESET = "password_reset"
    IAM_ACCOUNT_UNLOCK = "iam_account_unlock"
    VPN_ACCESS_RESET = "vpn_access_reset"
    UNKNOWN = "unknown"

class IntakeContextResponse(BaseModel):
    job_id: str
    user_id: str
    statusCode: int
    classification: str
    raw_input: str
    retrieved_chunks: list[dict]
    action: str
    body: str = "Hello from Intake Context Lambda!"

class TicketDetailResponse(BaseModel):
    title: Optional[str]
    summary: Optional[str]

class ProposalResponse(BaseModel):
    proposal: Optional[str]
    new_classification: Optional[str]

class AgentState(TypedDict, total=False):
    job_id: str
    action: str
    user_id: Optional[str]
    device_id: Optional[str]
    classification: Optional[str]
    raw_input: Optional[str]
    retrieved_chunks: Optional[list]
    ticket_id: Optional[str]
    title: Optional[str]
    summary: Optional[str]
    proposed_resolution: Optional[str]
    approved: Optional[bool]
    token: Optional[str]
    resolution_audit_log: Optional[list]
    # updated_at: Optional[int]