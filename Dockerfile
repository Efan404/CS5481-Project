FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN chmod +x /app/start.sh

EXPOSE 8964
EXPOSE 8501

CMD ["/bin/bash", "/app/start.sh"]
