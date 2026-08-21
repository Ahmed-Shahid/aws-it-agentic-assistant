from pydantic import BaseModel

class ClaudeAIModels:
    small = "claude-haiku-4-5"
    medium = "claude-sonnet-5"
    large = "claude-opus-5"

class IntakeContextResponse(BaseModel):
    job_id: str
    user_id: str
    statusCode: int
    classification: str
    raw_input: str
    retrieved_chunks: list[str]
    action: str
    body: str = "Hello from Intake Context Lambda!"
    