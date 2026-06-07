from langchain_ollama import ChatOllama
from backend.rag import search_logs

llm = ChatOllama(
    model="qwen3:0.6b",
    base_url="http://host.docker.internal:11434"
)

def diagnose_logs(question):

    logs = search_logs(question)

    context = "\n".join(
        [log.page_content for log in logs]
    )

    prompt = f"""
You are a Site Reliability Engineer.

Analyze the following logs:

{context}

User Question:
{question}

Provide:
1. Root Cause
2. Impact
3. Recommended Fix
"""

    response = llm.invoke(prompt)

    return response.content