FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

# Cài Python deps trước (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY config/     ./config/
COPY models/     ./models/
COPY inference/  ./inference/
COPY serving/    ./serving/

# Biến môi trường mặc định (bị override bởi .env khi docker run)
ENV ADAPTER_PATH=./models/vit5-lora-adapter
ENV BASE_MODEL_NAME=VietAI/vit5-base
ENV DEVICE=auto

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]