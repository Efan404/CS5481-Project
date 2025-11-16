# AGENTS

Internal orientation notes for Codex-style agents working on this project.

## Mission Snapshot

- Deliver a medical Retrieval-Augmented Generation assistant that pulls textbook snippets from a FAISS index stored in Appwrite Storage and sends replies through QnAIGC (`deepseek/deepseek-v3.2-exp` by default).
- Raw textbooks live in the Appwrite bucket `data` (id `691947bc0010c515b099`). Helper scripts handle uploads/downloads; the runtime container remains stateless.
- FastAPI (`middleware.py`) is the backend entrypoint consumed by both the Streamlit UI and any future SaaS layer (e.g., Coolify deployments).

## Key Components & Ownership

| Area | Primary Files | Responsibilities |
| --- | --- | --- |
| **Infrastructure** | `Dockerfile`, `docker-compose.yml`, `start.sh` | Build/run the combined FastAPI + Streamlit container locally; Coolify builds directly from the Dockerfile. Ensure environment variables are supplied via `.env` or the hosting platform. |
| **Middleware API** | `middleware.py`, `storage/appwrite_storage.py` | Downloads FAISS + metadata (if missing), exposes `/healthz`, `/api/rag`, `/api/chat`, and forwards augmented prompts to the remote LLM. |
| **Streamlit Frontend** | `frontend/frontend.py` | UI surface for MedBot, calling `/api/rag` then `/api/chat`, and displaying streaming-like responses. |
| **Data Management** | `scripts/upload_textbooks.py`, `dataset_ingest.py`, `utils/*` | Upload textbook archives to Appwrite and build/upload FAISS artifacts. Utilities support PDF parsing and embedding generation. |

## Standard Workflows

1. **Seed/refresh the dataset**
   - `python scripts/upload_textbooks.py --source books/MedQuAD-master/textbooks` (requires Appwrite creds in `.env`).
   - `python dataset_ingest.py --source books/MedQuAD-master/textbooks/chunk --upload` to rebuild FAISS and push to Appwrite.

2. **Run locally**
   - `docker compose up --build`
   - Visit Streamlit on `http://localhost:8501`; FastAPI docs at `http://localhost:8964/docs`.

3. **Deploy via Coolify/GitHub**
   - Push to `git@github.com:Efan404/CS5481-Project.git`.
   - Configure Coolify to build the Dockerfile and inject environment variables (`QINIU_*`, `APPWRITE_*`, `FAISS_*`). No additional services are required.

4. **Debugging**
   - `/healthz` verifies whether FAISS artifacts exist locally.
   - `curl http://localhost:8964/api/rag` with a JSON string payload to test retrieval.
   - `docker compose logs -f app` for container logs.

## Guardrails

- Do not store raw medical data in the repo; always push datasets/indices to Appwrite and fetch them at runtime.
- Never commit filled `.env` files—use `rag/.env.example` as reference and keep secrets in GitHub/Coolify secrets or local `.env` ignored by Git.
- When changing the embedding model or FAISS parameters, rebuild both the index and metadata to keep ordering consistent.
- Keep the remote LLM credentials in sync across environments; failure to set `QINIU_API_KEY` breaks `/api/chat`.

## Extension Ideas

- Implement periodic Appwrite sync or versioning (e.g., store index version metadata and allow rolling back).
- Add observability (structured logs, tracing, or metrics) and integrate with Coolify/hosted monitoring.
- Introduce authentication/authorization on the FastAPI endpoints if deploying publicly.
