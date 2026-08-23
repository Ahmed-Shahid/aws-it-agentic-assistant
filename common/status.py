"""
Shared DynamoDB status helper.

Every Lambda in the pipeline copies this file into its image via:
    COPY common/ ${LAMBDA_TASK_ROOT}/common
so they all read/write the same job-status shape without duplicating logic.
"""
import os
import time
from typing import Optional
from common.models import AgentState

import boto3

_table_name = os.environ.get("STATUS_TABLE_NAME")
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_table_name) if _table_name else None


def update_status(job_id: str, status: str, **extra) -> None:
    """Write/overwrite the current status for a job_id. Extra kwargs become
    additional attributes (e.g. result='...')."""
    if _table is None:
        return  # no-op if not configured, e.g. running a handler locally
    item = {"job_id": job_id, "status": status, "updated_at": int(time.time())}
    item.update(extra)
    _table.put_item(Item=item) #NOTE: Full overwrite, not merge, so task_token my be lost


def get_status(job_id: str) -> Optional[dict]:
    if _table is None:
        return None
    resp = _table.get_item(Key={"job_id": job_id})
    return resp.get("Item")

def write_state_to_status(state: AgentState) -> None:
    """Write the current state to the status table for a given job_id."""
    job_id = state.get("job_id")
    if not job_id:
        raise ValueError("Job ID is required to write state to status.")
    extra = {k: v for k, v in state.items() if k != "job_id"}
    update_status(job_id, "in_progress", **extra)