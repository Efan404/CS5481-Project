# RAG FAISS Remote LLM Stack

This repository packages a Retrieval-Augmented Generation (RAG) assistant that:

- Generates embeddings for textbook chunks and stores them inside a FAISS index.
- Keeps the raw dataset, FAISS index, and metadata inside Appwrite Storage (bucket `data`, id `691947bc0010c515b099`).
- Uses a FastAPI middleware to fetch the relevant snippets from FAISS and forward prompt-augmented chats to Qiniu QnAIGC (`deepseek/deepseek-v3.2-exp` by default).
- Provides a Streamlit UI that consumes the middleware endpoints.

The codebase is ready for GitHub + Coolify deployments: the Dockerfile builds a single container that runs both FastAPI and Streamlit, and docker-compose is only used for local development.

## Repository Layout

| Path | Description |
| --- | --- |
| `Dockerfile` / `docker-compose.yml` | Build and (optionally) run the single container that hosts FastAPI + Streamlit. |
| `start.sh` | Boots Uvicorn and Streamlit simultaneously inside the container. |
| `middleware.py` | FastAPI application exposing `/healthz`, `/api/rag`, and `/api/chat`. Loads FAISS + metadata from Appwrite and calls the remote LLM. |
| `frontend/frontend.py` | Streamlit chat client that calls `/api/rag` then `/api/chat`. |
| `storage/appwrite_storage.py` | Thin wrapper around the Appwrite Python SDK for downloads/uploads. |
| `scripts/upload_textbooks.py` | Compresses `books/MedQuAD-master/textbooks/` and uploads it to Appwrite storage. |
| `dataset_ingest.py` | Builds the FAISS index + metadata from chunked JSONL files and can upload the artifacts to Appwrite. |
| `utils/*` | Misc utilities (PDF loader, embedding helpers). |
| `.env.example` | Documents all environment variables required by the service and the helper scripts. |

## System Architecture

1. **Data storage** – MedQuAD textbooks live in Appwrite storage (bucket `data`). Use `scripts/upload_textbooks.py` whenever you refresh the source material.
2. **Index build** – `python dataset_ingest.py --upload` reads chunked JSONL files (e.g., `books/MedQuAD-master/textbooks/chunk/*.jsonl`), embeds them with `sentence-transformers/all-MiniLM-L6-v2`, builds a FAISS `IndexFlatIP`, writes `faiss.index` + `metadata.jsonl`, and uploads those artifacts back to Appwrite (`APPWRITE_FAISS_INDEX_ID`, `APPWRITE_FAISS_METADATA_ID`).
3. **Middleware** – On startup, `middleware.py` downloads the FAISS + metadata bundle (if missing), loads it into memory, and exposes `/api/rag` (retrieval only) plus `/api/chat` (retrieval + call to QnAIGC’s `/chat/completions`).
4. **Frontend** – `frontend/frontend.py` (Streamlit) collects user prompts, calls `/api/rag` to augment them, then posts to `/api/chat` and displays the response, keeping session state locally.
5. **Remote LLM** – Qiniu QnAIGC (or any provider matching the OpenAI-style API) performs text generation. Supply `QINIU_API_KEY`, `QINIU_API_URL`, and optionally `QINIU_MODEL_NAME` in `.env`.

## Prerequisites

- Docker / Docker Compose for local testing.
- Python 3.11 and `pip` if you plan to run the helper scripts locally.
- Appwrite credentials: endpoint, project ID, bucket id/name (`data`/`691947bc0010c515b099`), and a dev API key.
- QnAIGC API key.

## Managing Data in Appwrite Storage

1. **Upload textbooks**

   ```bash
   # Copy .env.example to .env and fill in Appwrite + QnAIGC credentials first
   python scripts/upload_textbooks.py --source books/MedQuAD-master/textbooks --file-id medquad-textbooks
   ```

   The script compresses the folder into `medquad-textbooks.tar.gz` and uploads it to the configured bucket. Adjust `--file-id` if you want multiple versions.

2. **Build + upload the FAISS bundle**

   ```bash
   python dataset_ingest.py --source books/MedQuAD-master/textbooks/chunk --output artifacts --upload
   ```

   This command writes `artifacts/faiss.index` and `artifacts/metadata.jsonl`, then uploads them to Appwrite using the IDs in `.env`.

## Running the App Locally

```bash
# Build and run the container
docker compose up --build

# Streamlit -> http://localhost:8501
# FastAPI docs -> http://localhost:8964/docs
```

The container reads `.env` for runtime secrets (compose already mounts it). `/healthz` reports whether FAISS artifacts were found locally; if missing, the middleware automatically attempts to download them from Appwrite.

## Helper Endpoints & Scripts

- `/api/rag`: POST a JSON string (the raw user prompt) to inspect the augmented prompt before hitting the LLM.
- `/api/chat`: Send an OpenAI-style payload to get a full response (the middleware injects the retrieved context for you).
- `scripts/upload_textbooks.py`: one-shot uploader for the MedQuAD folder.
- `dataset_ingest.py`: rebuild FAISS + metadata, optionally uploading to storage.

## Coolify / CI/CD Notes

- Commit the repo to GitHub (`git@github.com:Efan404/CS5481-Project.git`) and connect it to Coolify. Coolify will build the Dockerfile on every push and can inject the necessary environment variables (`QINIU_*`, `APPWRITE_*`, `FAISS_*`).
- For additional safety, add a GitHub Actions workflow that runs lint/tests on pull requests before merges (Coolify handles the deployment builds).
- No stateful services are bundled in the container; Appwrite + FAISS artifacts are fetched at runtime, so deployments remain stateless.

## Configuration Reference

Key environment variables (see `.env.example` for the full list):

- `QINIU_API_KEY`, `QINIU_API_URL`, `QINIU_MODEL_NAME`
- `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_BUCKET_ID`, `APPWRITE_BUCKET_NAME`, `APPWRITE_API_KEY`
- `APPWRITE_TEXTBOOK_ARCHIVE_ID`, `APPWRITE_FAISS_INDEX_ID`, `APPWRITE_FAISS_METADATA_ID`
- `FAISS_INDEX_PATH`, `FAISS_METADATA_PATH`

## License & Attribution

The Milvus configuration file (`milvus.yaml`) remains for reference but is no longer used in the runtime stack. The MedQuAD dataset attribution is documented inside `textbooks/README.md`. Respect the source licenses when ingesting additional medical content.
