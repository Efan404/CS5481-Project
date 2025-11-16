#!/bin/bash
set -euo pipefail

uvicorn rag.middleware:app --host 0.0.0.0 --port 8964 &
UVICORN_PID=$!

streamlit run rag/frontend/frontend.py --server.port 8501 --server.address 0.0.0.0

wait "$UVICORN_PID"
