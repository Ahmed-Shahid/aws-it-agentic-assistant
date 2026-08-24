import os

import streamlit as st
import boto3
import json
import requests
import dotenv

dotenv.load_dotenv()
TEMP_QUERY_FN = os.getenv("TEMP_QUERY_FN")
DATA_SEEDER_FN = os.getenv("DATA_SEEDER_FN")
REGION = os.getenv("REGION")
API_FN_URL = os.getenv("API_FN_URL")
CA_BUNDLE_PATH = os.getenv("CA_BUNDLE_PATH")

st.set_page_config(page_title="IT Assistant Dashboard", layout="wide")

lambda_client = boto3.client("lambda", region_name=REGION)  # match your region

# DATABASE

def call_temp_query(payload=None):
    """Invoke temp_query Lambda and normalize the response."""
    resp = lambda_client.invoke(
        FunctionName=TEMP_QUERY_FN,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload or {}),
    )
    result = json.loads(resp["Payload"].read())["result"]
    # print(result)
    # if isinstance(result, dict) and "body" in result:
    #     body = result["body"]
    #     result = json.loads(body) if isinstance(body, str) else body
    return result

# def call_temp_query(payload=None):
#     resp = lambda_client.invoke(
#         FunctionName=TEMP_QUERY_FN,
#         InvocationType="RequestResponse",
#         Payload=json.dumps(payload or {}),
#     )
#     print(resp)
#     result = json.loads(resp["Payload"].read())
#     if "body" in result:  # if temp_query returns API-Gateway-style {statusCode, body}
#         result = json.loads(result["body"]) if isinstance(result["body"], str) else result["body"]
#     return result

def get_user_data():
    payload = {
    "sql": "select * from users"
    }
    return call_temp_query(payload)

def get_vpn_profiles():
    payload = {
    "sql": "select * from vpn_profiles"
    }
    return call_temp_query(payload)

def get_iam_accounts():
    payload = {
    "sql": "select * from iam_accounts"
    }
    return call_temp_query(payload)

def get_devices():
    payload = {
    "sql": "select * from devices"
    }
    return call_temp_query(payload)

def reset_database():
    payload = {
    "sql": "db_sql"
    }
    resp = lambda_client.invoke(
            FunctionName=DATA_SEEDER_FN,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload or {}),
        )
    return resp

# API STATE MACHINE

def start_query(payload):
    r = requests.post(f"{API_FN_URL}/start-query", json=payload, timeout=15, verify=CA_BUNDLE_PATH)
    r.raise_for_status()
    return r.json()

def get_all_statuses():
    r = requests.get(f"{API_FN_URL}/get-all-statuses", timeout=15, verify=CA_BUNDLE_PATH)
    r.raise_for_status()
    return r.json()

def get_status(job_id):
    r = requests.get(f"{API_FN_URL}/query-status/{job_id}", timeout=15, verify=CA_BUNDLE_PATH)
    r.raise_for_status()
    return r.json()

# st.title("Access Requests Dashboard")

# if st.button("Refresh data"):
#     st.cache_data.clear()

# @st.cache_data(ttl=30)
# def load_data():
#     return call_temp_query()

# data = load_data()
# st.dataframe(data)

# st.divider()
# st.subheader("Trigger a new resolution")
# username = st.text_input("Username")
# system_name = st.text_input("System name")

# if st.button("Submit issue"):
#     result = call_api_state_machine({
#         "username": username,
#         "system_name": system_name,
#     })
#     st.success("Submitted")
#     st.json(result)


# INITIALIZE DATA

reset_database()
user_data = get_user_data()
vpn_profiles = get_vpn_profiles()
iam_accounts = get_iam_accounts()
devices = get_devices()

st.set_page_config(page_title="IT Agentic Assistant", layout="wide")
st.title("AWS IT Agentic Assistant")

# SIDEBAR

top_k = st.sidebar.slider("Top K", 1, 5, 3)
user_id = st.sidebar.selectbox("User ID", options=[x["user_id"] for x in user_data], index=0)

# MAIN CONTENT
# st.json(user_data, expanded=False)
# st.json(vpn_profiles, expanded=False)
# st.json(iam_accounts, expanded=False)
# st.json(devices, expanded=False)

# st.table(user_data)
tab1, tab2, tab3, tab4 = st.tabs(["Issue Input", "Data Overview", "Jira Tickets", "Evaluations"])

with tab1:
    st.subheader("Describe your issue")
    question = st.text_input("Desribe your issue")

    if st.button("Submit and Create Ticket") and question.strip():
        payload = {
            "raw_input": question,
            "top_k": top_k,
            "user_id": user_id,
        }

        with st.spinner("Generating answer..."):
            result = start_query(payload)

        st.subheader("Result")
        st.write(result)

        with st.spinner("Checking status..."):
            status = get_status(result["job_id"])
        st.subheader("Status")
        st.write(status)

with tab2:
    user_data = get_user_data()
    vpn_profiles = get_vpn_profiles()
    iam_accounts = get_iam_accounts()
    devices = get_devices()

    st.subheader("User Data")
    st.dataframe(user_data)

    st.subheader("VPN Profiles")
    st.dataframe(vpn_profiles)

    st.subheader("IAM Accounts")
    st.dataframe(iam_accounts)

    st.subheader("Devices")
    st.dataframe(devices)

with tab3:
    statuses = get_all_statuses()
    # statuses = [
    #     {"job_id": "job1", "status": "queued"},
    #     {"job_id": "job2", "status": "approved"},
    #     {"job_id": "job3", "status": "rejected"},
    # ]
    st.subheader("All Query Statuses")
    st.dataframe(statuses)

with tab4:
    st.subheader("Evaluations")
    # Add evaluation content here
    evaluations = [
        {"Original Prompt": "If the classification is incorrect, propose a new classification.", 
         "Issue": "Classification was changed even though there was an issue with the underlying data",
         "New Prompt": "If no corrections are possible with the underlying data, propose a new classification."},
    ]