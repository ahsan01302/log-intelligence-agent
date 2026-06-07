import streamlit as st
import requests

st.set_page_config(
    page_title="AI Log Intelligence Agent",
    layout="wide"
)

st.title("🤖 AI Log Intelligence Agent")

uploaded_file = st.file_uploader(
    "Upload Log File",
    type=["log", "txt"]
)

if uploaded_file:

    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue()
        )
    }

    response = requests.post(
        "http://127.0.0.1:8000/upload",
        files=files
    )

    if response.status_code == 200:
        st.success("Log uploaded successfully")

question = st.text_input(
    "Ask a question about your logs"
)

if st.button("Analyze Logs"):

    response = requests.get(
        "http://127.0.0.1:8000/chat",
        params={
            "question": question
        }
    )

    result = response.json()

    st.subheader("Diagnosis")

    st.write(
        result["response"]
    )