import streamlit as st
import boto3
import json
import requests

st.set_page_config(page_title="IT Assistant Dashboard", layout="wide")

lambda_client = boto3.client("lambda", region_name="us-west-1")  # match your region

TEMP_QUERY_FN = "temp_query"
API_FN_URL = "https://xxxx.lambda-url.us-west-1.on.aws/"  # api_state_machine's Function URL

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

def retrieve(question, top_k=3):
    results = collection.query(query_texts=[question], n_results=top_k)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    rows = []
    for d, m in zip(docs, metas):
        rows.append({
            "text": d,
            "source": m.get("source_file", "unknown"),
            "chunk_id": m.get("chunk_id", "na")
        })
    return rows

def generate_answer(prompt, model="phi3:mini", base_url="http://host.docker.internal:11434"):
    payload = {"model": model, "prompt": prompt, "stream": False}
    r = requests.post(f"{base_url}/api/generate", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["response"]

st.set_page_config(page_title="Local RAG Assistant", layout="wide")
st.title("Mini Project 2 - Local RAG Knowledge Assistant")

question = st.text_input("Ask a question about the sample documents")
top_k = st.slider("Top K", 1, 5, 3)
model = st.text_input("Model", value="phi3:mini")
base_url = st.text_input("Ollama URL", value="http://host.docker.internal:11434")

if st.button("Ask") and question.strip():
    chunks = retrieve(question, top_k=top_k)
    context = "\\n\\n".join([f"[{c['source']} - {c['chunk_id']}]\\n{c['text']}" for c in chunks])

    prompt = f"""You are an internal knowledge assistant.
Answer only from the provided context.
If the answer is not supported by the context, say:
"I do not know based on the provided documents."
Cite the sources in the format [source_file - chunk_id].

Question:
{question}

Context:
{context}
"""

    with st.spinner("Generating answer..."):
        answer = generate_answer(prompt, model=model, base_url=base_url)

    st.subheader("Answer")
    st.write(answer)

    st.subheader("Retrieved Chunks")
    for c in chunks:
        with st.expander(f"{c['source']} - {c['chunk_id']}"):
            st.write(c["text"])
