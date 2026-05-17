# Models — Backend AI Services

Hệ thống gồm 4 service chạy độc lập, giao tiếp qua HTTP:

| Service             | Port | Chức năng                                            |
| ------------------- | ---- | ---------------------------------------------------- |
| `gateway`           | 8000 | API entry-point, định tuyến request đến các service  |
| `service_qa`        | 8003 | RAG Q&A — nhận PDF, tìm kiếm vector, trả lời câu hỏi |
| `service_summarize` | 8001 | Tóm tắt văn bản / PDF bằng ViT5 LoRA                 |
| `service_factcheck` | 8002 | Kiểm tra độ tin cậy câu trả lời bằng NLI             |

---

## Yêu cầu hệ thống

- Python 3.11
- Docker

### API Keys cần có

| Biến môi trường        | Dùng cho                   | Lấy ở đâu                                    |
| ---------------------- | -------------------------- | -------------------------------------------- |
| `GROQ_API_KEY`         | LLM inference (service_qa) | [console.groq.com](https://console.groq.com) |
| `SUPABASE_URL`         | Database (service_qa)      | Supabase project settings                    |
| `SUPABASE_KEY`         | Database (service_qa)      | Supabase project settings                    |
| `SUPABASE_SERVICE_KEY` | Admin DB ops (service_qa)  | Supabase project settings                    |
| `SUPABASE_JWT_SECRET`  | Auth (service_qa)          | Supabase project settings                    |
| `PG_CONN_STRING`       | PGVector (service_qa)      | Supabase → Database → Connection string      |

---

## Cách 1 — Chạy bằng Docker

### Bước 1 — Tạo file `.env`

Tạo file `.env` ở **thư mục gốc** (`Models/.env`) cho gateway:

```env
# Không cần thêm gì nếu gateway chỉ proxy — để trống hoặc xoá file này
```

Tạo `service_qa/.env`:

```env
GROQ_API_KEY=gsk_...
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_JWT_SECRET=...
PG_CONN_STRING=postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
FACTCHECK_SERVICE_URL=http://factcheck:8000
```

Tạo `service_summarize/.env`:

```env
ADAPTER_PATH=./models/vit5-lora-adapter
ADAPTER_REPO=CV12323/vit5-summarize
# HF_TOKEN=hf_...   # Bỏ comment nếu repo private
```

Tạo `service_factcheck/.env`:

```env
# Có thể để trống — model tải tự động từ Hugging Face
```

### Bước 2 — Build và chạy

```bash
cd Models
docker compose up --build
```

> Lần đầu build sẽ mất 5–15 phút do tải model. Các lần sau nhanh hơn nhờ cache.

### Bước 3 — Kiểm tra

```bash
curl http://localhost:8000/docs          # Gateway API docs
curl http://localhost:8001/health        # Summarize service
curl http://localhost:8002/health        # Factcheck service
curl http://localhost:8003/health        # QA service
```

Truy cập **http://localhost:8000/docs** để test API trực tiếp qua giao diện Swagger.

---

## API Endpoints chính

### Tóm tắt văn bản

```bash
POST http://localhost:8000/api/v1/summarize

{
  "text": "Nội dung văn bản cần tóm tắt (tối thiểu 50 ký tự)..."
}
```

### Kiểm tra thông tin (Fact-check)

```bash
POST http://localhost:8000/api/v1/factcheck

{
  "claim": "Câu cần kiểm tra",
  "evidence": ["Đoạn bằng chứng 1", "Đoạn bằng chứng 2"]
}
```

### Q&A với tài liệu (gọi trực tiếp service_qa)

```bash
# Upload PDF
POST http://localhost:8003/upload
Content-Type: multipart/form-data
file: <file.pdf>

# Hỏi đáp
POST http://localhost:8003/ask
{
  "question": "Câu hỏi về nội dung tài liệu"
}
```

---

## Cấu trúc thư mục

```
Models/
├── docker-compose.yml
├── gateway/              # API gateway
│   └── main.py
├── service_qa/           # RAG Q&A service
│   ├── config/
│   ├── data_access/      # Supabase client
│   ├── embedding/        # Sentence-transformers
│   ├── generation/       # LLM (Groq/LLaMA)
│   ├── retrieval/        # PGVector search
│   └── serving/          # FastAPI app
├── service_summarize/    # Summarization service
│   ├── inference/        # ViT5 LoRA inference
│   ├── models/           # Model weights (local)
│   └── serving/          # FastAPI app
└── service_factcheck/    # Fact-checking service
    ├── inference/        # NLI inference
    ├── models/           # DeBERTa model loader
    └── serving/          # FastAPI app
```
