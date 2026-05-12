FROM python:3.11-slim

WORKDIR /app

# build-essential cần cho psycopg2, pgvector
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ ./config/
COPY data_access/ ./data_access/
COPY embedding/ ./embedding/
COPY retrieval/ ./retrieval/
COPY generation/ ./generation/
COPY serving/ ./serving/

EXPOSE 8000

CMD ["uvicorn", "serving.main:app", "--host", "0.0.0.0", "--port", "8000"]