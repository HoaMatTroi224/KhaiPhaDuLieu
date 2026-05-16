FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/opt/sentence-transformers \
    EMBEDDING_MODEL_REPO=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 \
    EMBEDDING_MODEL=/opt/models/embedding

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from sentence_transformers import SentenceTransformer; import os; repo = os.environ['EMBEDDING_MODEL_REPO']; target = os.environ['EMBEDDING_MODEL']; model = SentenceTransformer(repo); model.save(target); print(f'Embedding model saved to {target}')"

COPY . .

EXPOSE 8000

ENV TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
