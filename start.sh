#!/bin/bash
set -euo pipefail

uvicorn middleware:app --host 0.0.0.0 --port 8964 &
UVICORN_PID=$!

streamlit run frontend/frontend.py --server.port 8501 --server.address 0.0.0.0

wait "$UVICORN_PID"
