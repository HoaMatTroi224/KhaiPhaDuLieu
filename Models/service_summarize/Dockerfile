FROM python:3.11-slim

WORKDIR /app

# Cài system deps (sentencepiece cần g++)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

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

# Khởi chạy uvicorn
CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]