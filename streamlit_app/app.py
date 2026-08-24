import streamlit as st
import boto3
import json
import requests

st.set_page_config(page_title="IT Assistant Dashboard", layout="wide")

lambda_client = boto3.client("lambda", region_name="us-east-1")  # match your region

TEMP_QUERY_FN = "temp_query"
API_FN_URL = "https://xxxx.lambda-url.us-east-1.on.aws/"  # api_state_machine's Function URL

def call_temp_query(payload=None):
    resp = lambda_client.invoke(
        FunctionName=TEMP_QUERY_FN,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload or {}),
    )
    result = json.loads(resp["Payload"].read())
    if "body" in result:  # if temp_query returns API-Gateway-style {statusCode, body}
        result = json.loads(result["body"])
    return result

def call_api_state_machine(payload):
    r = requests.post(API_FN_URL, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

st.title("Access Requests Dashboard")

if st.button("Refresh data"):
    st.cache_data.clear()

@st.cache_data(ttl=30)
def load_data():
    return call_temp_query()

data = load_data()
st.dataframe(data)

st.divider()
st.subheader("Trigger a new resolution")
username = st.text_input("Username")
system_name = st.text_input("System name")

if st.button("Submit issue"):
    result = call_api_state_machine({
        "username": username,
        "system_name": system_name,
    })
    st.success("Submitted")
    st.json(result)