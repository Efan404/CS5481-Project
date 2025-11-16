import json
import logging
import os
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from rag.storage.appwrite_storage import AppwriteStorageClient

load_dotenv()

DEFAULT_MODEL = os.getenv("QINIU_MODEL_NAME", "deepseek/deepseek-v3.2-exp")
REMOTE_BASE_URL = os.getenv("QINIU_API_URL", "https://api.qnaigc.com/v1").rstrip("/")
REMOTE_CHAT_URL = f"{REMOTE_BASE_URL}/chat/completions"
REMOTE_API_KEY = os.getenv("QINIU_API_KEY")

FAISS_INDEX_PATH = Path(os.getenv("FAISS_INDEX_PATH", "/tmp/faiss.index"))
FAISS_METADATA_PATH = Path(os.getenv("FAISS_METADATA_PATH", "/tmp/faiss_metadata.jsonl"))
FAISS_INDEX_ID = os.getenv("APPWRITE_FAISS_INDEX_ID", "faiss-index")
FAISS_METADATA_ID = os.getenv("APPWRITE_FAISS_METADATA_ID", "faiss-metadata")

embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

app = FastAPI()

_faiss_index = None
_documents: List[dict] = []


class Message(BaseModel):
    role: str
    content: str


class Options(BaseModel):
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 256


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    stream: bool = False
    options: Optional[Options] = None


def ensure_remote_credentials() -> None:
    if not REMOTE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing QINIU_API_KEY in environment")


def ensure_index_loaded() -> None:
    global _faiss_index, _documents
    if _faiss_index is not None and _documents:
        return

    if not FAISS_INDEX_PATH.exists() or not FAISS_METADATA_PATH.exists():
        storage = AppwriteStorageClient()
        storage.download_file(FAISS_INDEX_ID, FAISS_INDEX_PATH)
        storage.download_file(FAISS_METADATA_ID, FAISS_METADATA_PATH)

    if not FAISS_INDEX_PATH.exists() or not FAISS_METADATA_PATH.exists():
        raise RuntimeError("FAISS artifacts are missing. Run dataset_ingest.py to generate them.")

    _faiss_index = faiss.read_index(str(FAISS_INDEX_PATH))
    docs: List[dict] = []
    with FAISS_METADATA_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                docs.append(json.loads(line))
    _documents = docs


def search_documents(query: str, top_k: int = 3) -> List[dict]:
    ensure_index_loaded()
    query_vec = embedder.encode(query, normalize_embeddings=True)
    vectors = np.asarray([query_vec], dtype="float32")
    distances, indices = _faiss_index.search(vectors, top_k)
    hits = []
    for idx in indices[0]:
        if idx < 0 or idx >= len(_documents):
            continue
        hits.append(_documents[idx])
    return hits


def call_remote_model(messages: List[dict], stream: bool, options: Optional[Options], model_name: Optional[str]):
    ensure_remote_credentials()
    payload = {
        "model": model_name or DEFAULT_MODEL,
        "messages": messages,
        "stream": stream,
    }
    if options:
        if options.temperature is not None:
            payload["temperature"] = options.temperature
        if options.max_tokens is not None:
            payload["max_tokens"] = options.max_tokens

    headers = {
        "Authorization": f"Bearer {REMOTE_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(REMOTE_CHAT_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
    except requests.RequestException as exc:
        logging.exception("Remote LLM request failed")
        raise HTTPException(status_code=502, detail=f"Remote LLM request failed: {exc}")
    return response.json()


@app.get("/healthz")
def healthcheck():
    return {"status": "ok", "indexLoaded": FAISS_INDEX_PATH.exists()}


@app.post("/api/rag")
async def process_rag(payload: str = Body(...)):
    processed_prompt = custom_processing(payload)
    context_docs = search_documents(processed_prompt)

    context = "\n".join(doc.get("content", "") for doc in context_docs)
    final_prompt = f"Address patient's query: '{processed_prompt}' \n based on knowledge: '{context}'"
    return final_prompt


@app.post("/api/chat")
async def process_request(request: ChatRequest):
    user_prompt = str(request.messages[-1].content)
    processed_prompt = custom_processing(user_prompt)
    context_docs = search_documents(processed_prompt)

    context = "\n".join(doc.get("content", "") for doc in context_docs)
    final_prompt = f"Address patient's query: '{processed_prompt}' \n based on knowledge: '{context}'"

    updated_messages = [message.dict() for message in request.messages]
    updated_messages[-1] = {"role": "user", "content": final_prompt}

    response_payload = call_remote_model(
        messages=updated_messages,
        stream=request.stream,
        options=request.options,
        model_name=request.model,
    )
    return response_payload


def custom_processing(text: str) -> str:
    return text.strip()
