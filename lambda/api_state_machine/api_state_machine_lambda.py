import boto3
import os
import json
import uuid
from fastapi import FastAPI, HTTPException
from mangum import Mangum

app = FastAPI()

sfn = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN")

#TODO: Add "Get Status" function to retrieve the status of a job from DynamoDB or another storage solution
def get_status(job_id: str):
    return {'status': 'queued', 'task_token': 'dummy_task_token', 'job_id': job_id}  # Placeholder implementation

#Test comment


@app.post("/start-query")
async def start_query(payload: dict):
    job_id = str(uuid.uuid4())
    #TODO: Add "Update Status" to keep track of job status

    try:
        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=job_id,
            input=json.dumps({"job_id": job_id, **payload})
        )
        return {"job_id": job_id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/query-status/{job_id}")
async def query_status(job_id: str):
    item = get_status(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return item

@app.post("/approve-query/{job_id}")
async def approve(job_id: str):
    item = get_status(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    
    sfn.send_task_success(
        taskToken=item["task_token"],
        output=json.dumps({**item, "status": "approved"})
    )
    return {"job_id": job_id, "status": "approved"}

@app.post("/reject-query/{job_id}")
async def reject(job_id: str):
    item = get_status(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    
    sfn.send_task_failure(
        taskToken=item["task_token"],
        error="QueryRejected",
        cause="The query was rejected by the user."
    )
    return {"job_id": job_id, "status": "rejected"}

handler = Mangum(app)