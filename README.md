# AI Log Intelligence Agent

## Overview

AI-powered Log Intelligence Agent that analyzes raw system logs using Retrieval-Augmented Generation (RAG).

The application allows users to:

* Upload log files
* Generate embeddings using Ollama
* Store vectors in FAISS
* Perform semantic search
* Diagnose issues using Qwen3 LLM
* Receive Root Cause Analysis (RCA)

---

## Architecture

```text
Upload Logs
    │
    ▼
FastAPI Backend
    │
    ▼
Log Parser
    │
    ▼
Nomic Embeddings (Ollama)
    │
    ▼
FAISS Vector Store
    │
    ▼
Retriever
    │
    ▼
Qwen3 LLM
    │
    ▼
Diagnosis Response
```

---

## Tech Stack

### Backend

* FastAPI
* LangChain
* Ollama
* FAISS

### Frontend

* Streamlit

### LLM

* Qwen3:0.6B

### Embeddings

* nomic-embed-text

### Containerization

* Docker
* Docker Compose

---

## Features

* Log Upload
* Semantic Search
* Root Cause Analysis
* Impact Assessment
* Recommended Fixes
* Dockerized Deployment

---

## Run Locally

### Build

```bash
docker compose build
```

### Run

```bash
docker compose up
```

Backend:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

Frontend:

```text
http://localhost:8501
```

---

## Future Enhancements

* LangGraph Agent Workflow
* AWS ECS Deployment
* Terraform Infrastructure
* CI/CD Pipeline
* Multi-Log Analysis
* PDF Report Generation

```
```
