import os

import streamlit as st
import boto3
import json
import requests
import dotenv
import pypdf
import docx

dotenv.load_dotenv()
TEMP_QUERY_FN = os.getenv("TEMP_QUERY_FN")
DATA_SEEDER_FN = os.getenv("DATA_SEEDER_FN")
REGION = os.getenv("REGION")
API_FN_URL = os.getenv("API_FN_URL")
CA_BUNDLE_PATH = os.getenv("CA_BUNDLE_PATH")
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
UPLOAD_DOCUMENT_FN = os.getenv("UPLOAD_DOCUMENT_FN")

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
    return result

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

def get_document_chunks():
    payload = {
    "sql": "select document_name, count(*) as num_chunks from document_chunks group by document_name"
    }
    return call_temp_query(payload)

def upload_document(file_content, file_name, chunk_size=500):
    """Invoke upload_document Lambda and normalize the response."""
    resp = lambda_client.invoke(
        FunctionName=UPLOAD_DOCUMENT_FN,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "document_content": file_content,
            "document_name": file_name,
            "chunk_size": chunk_size
        }),
    )
    result = resp["Payload"].read().decode("utf-8")
    return result

def reset_database(type="db_sql"):
    payload = {
    "sql": type
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


# INITIALIZE DATA

user_data = get_user_data()
vpn_profiles = get_vpn_profiles()
iam_accounts = get_iam_accounts()
devices = get_devices()

st.set_page_config(page_title="IT Agentic Assistant", layout="wide")
st.title("AWS IT Agentic Assistant")

# SIDEBAR

top_k = st.sidebar.slider("Top K", 1, 5, 3)
user_id = st.sidebar.selectbox("User ID", options=[x["user_id"] for x in user_data], index=0)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Issue Input", "Data Overview", "Jira Tickets", "Evaluations", "Upload Document", "Test Cases"])

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
        st.link_button("View Jira Board", JIRA_BASE_URL)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh Data"):
            st.rerun()

    with col2:
        if st.button("Reset Database"):
            reset_database()
            st.success("Database reset successfully!")
            st.rerun()

    user_data = get_user_data()
    vpn_profiles = get_vpn_profiles()
    iam_accounts = get_iam_accounts()
    devices = get_devices()
    document_chunks = get_document_chunks()

    st.subheader("User Data")
    st.dataframe(user_data)

    st.subheader("VPN Profiles")
    st.dataframe(vpn_profiles)

    st.subheader("IAM Accounts")
    st.dataframe(iam_accounts)

    st.subheader("Devices")
    st.dataframe(devices)

    st.subheader("Document Chunks")
    st.dataframe(document_chunks)

with tab3:
    if st.button("Refresh Jira Tickets"):
        st.rerun()

    statuses = get_all_statuses()
    statuses = [{k: v for k, v in item.items() if k in ("ticket_id", "title", "user_id", "action", "job_id")} for item in statuses]
    for i, x in enumerate(statuses):
        statuses[i]["ticket_url"] = f"{JIRA_BASE_URL}/browse/{x['ticket_id']}" if x.get("ticket_id") else ""

    st.subheader("Jira Tickets")
    st.dataframe(
        statuses,
        column_config={
            "ticket_url": st.column_config.LinkColumn(
                help="Link to ticket",
                max_chars=100
            )
        }
    )

with tab4:
    st.subheader("Evaluation 1")
    # Add evaluation content here
    evaluations = [
        {"Original Prompt": "If the classification is incorrect, propose a new classification.", 
         "Issue": "Classification was changed even though there was an issue with the underlying data",
         "New Prompt": "If no corrections are possible with the underlying data, propose a new classification."},
    ]
    st.dataframe(evaluations)

    st.subheader("Evaluation 2")
    evaluations2 = [
        {"Classification": "password_reset", 
         "Chunk Size": "500",
         "Similarity Score": "0.1682"},
        {"Classification": "password_reset", 
         "Chunk Size": "250",
         "Similarity Score": "0.1682 (same chunks retrieved)"},

    ]

with tab5:
    st.subheader("Upload Runbook Documentation")
    chunk_size = st.number_input("Chunk Size", min_value=100, max_value=10000, value=500, step=100)
    uploaded_file = st.file_uploader("Choose a file", type=["txt", "md", "pdf", "docx"])
    if st.button("Upload") and uploaded_file is not None and chunk_size > 0:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        bytes_data = ""
    
        if file_extension == "pdf":
            st.write("Processing PDF...")
            reader = pypdf.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text().replace("\'", "\"") + "\n"
            bytes_data = text
            
        elif file_extension == "docx":
            st.write("Processing DOCX...")
            doc = docx.Document(uploaded_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text.replace("\'", "\"") + "\n"
            bytes_data = text
        else:
            bytes_data = str(uploaded_file.read()).replace("\'", "\"")

        st.write(f"Filename: {uploaded_file.name}")
        st.write(f"File size: {len(bytes_data)} bytes")
        st.write(f"File type: {uploaded_file.type}")
        st.write(f"File content (first 100 bytes): {bytes_data[:100]}")

        with st.spinner("Uploading document and creating embeddings..."):
            result = upload_document(
            file_content=str(bytes_data), 
            file_name=uploaded_file.name, 
            chunk_size=chunk_size
            )
            st.write("Document uploaded and embeddings created successfully!")
            st.json(result)

with tab6:
    st.subheader("VPN Access Reset Success")
    st.subheader("VPN Access Reset Not Needed (Jira/State Machine Side By Side)")
    st.subheader("Password Reset Retrieved Chunks")
    st.subheader("Rejection")