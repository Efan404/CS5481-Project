FROM python:3.11-slim

WORKDIR /app

COPY rag /app/rag
COPY rag/start.sh /app/start.sh

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    requests \
    streamlit \
    sentence-transformers \
    python-dotenv \
    appwrite \
    faiss-cpu \
    numpy

EXPOSE 8964
EXPOSE 8501

CMD ["/bin/sh", "-c", "/app/start.sh"]
