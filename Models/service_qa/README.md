# service_qa — RAG Q&A Service

## Tính năng

- Upload nhiều file PDF cùng lúc vào một project
- Tự động chunk, embed và lưu vector vào PostgreSQL + pgvector
- Hỏi đáp cross-document: câu trả lời tổng hợp từ nhiều tài liệu trong cùng project
- Trích dẫn nguồn `[S1][S2]...` kèm tên file, chunk index, relevance score
- Lịch sử hội thoại theo thread
- Tích hợp sẵn slot cho `service_factcheck` (bật khi set `FACTCHECK_SERVICE_URL`)

## Stack

| Thành phần      | Công nghệ                                    |
| --------------- | -------------------------------------------- |
| Framework       | FastAPI + Uvicorn                            |
| Embedding       | `intfloat/multilingual-e5-base` (local, CPU) |
| LLM             | Groq (`llama-3.3-70b-versatile`)             |
| Vector store    | PostgreSQL + pgvector                        |
| File & metadata | Supabase Storage + Supabase DB               |
| Container       | Docker                                       |

---

## Hướng dẫn chạy

> **Lưu ý về Supabase**: Database, bảng, RLS policies và Storage bucket đã được setup sẵn trên Supabase cloud dùng chung cho cả nhóm.

### Bước 1 — Lấy file `.env`

Xin file `.env`. Đặt file vào thư mục `service_qa/`.

### Bước 2 — Chạy bằng Docker (khuyến nghị)

```bash
# Build image
docker build -t service_qa .

# Chạy service
docker run -d --name service_qa -p 8000:8000 --env-file .env service_qa
```

Kiểm tra service đang chạy:

```bash
curl http://localhost:8000/health
# {"status": "healthy", "service": "qa", "version": "2.0.0"}
```

Xem logs:

```bash
docker logs -f service_qa
```

Dừng service:

```bash
docker stop service_qa && docker rm service_qa
```

### Bước 2 (thay thế) — Chạy local không dùng Docker

Yêu cầu: Python 3.11+

```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt (Windows)
venv\Scripts\activate

# Cài dependencies
pip install -r requirements.txt

# Chạy server
uvicorn serving.main:app --reload --port 8000
```

> Lần đầu chạy, model embedding (~500MB) sẽ tự download và cache lại. Các lần sau không cần download nữa.

---

## API Endpoints

Swagger UI đầy đủ tại: `http://localhost:8000/docs`

### `GET /health`

Kiểm tra service đang chạy.

```bash
curl http://localhost:8000/health
```

```json
{ "status": "healthy", "service": "qa", "version": "2.0.0" }
```

---

### `POST /process-document/`

Upload một hoặc nhiều file PDF vào một project. Xử lý bất đồng bộ (trả về ngay, xử lý trong background).

**Form data:**

| Field        | Type          | Mô tả                                      |
| ------------ | ------------- | ------------------------------------------ |
| `files`      | File[]        | Một hoặc nhiều file PDF (tối đa 10MB/file) |
| `project_id` | string (UUID) | ID của project                             |

**Ví dụ:**

**Response (202):**

```json
{
  "message": "2 file đã được nhận, đang xử lý trong background",
  "project_id": "9e5a6cc2-4b6a-41ca-897d-c6bdd9aaee5d",
  "files": ["paper1.pdf", "paper2.pdf"]
}
```

### `POST /ask/`

Hỏi đáp dựa trên tài liệu trong project.

**Query params:**

| Param        | Type          | Mô tả                                        |
| ------------ | ------------- | -------------------------------------------- |
| `project_id` | string (UUID) | ID của project                               |
| `thread_id`  | string (UUID) | ID của luồng hội thoại (tự tạo một UUID mới) |
| `question`   | string        | Câu hỏi                                      |

**Ví dụ:**
**Response (200):**

```json
{
  "answer": "Bài báo đề xuất phương pháp... [S1][S3]",
  "citations": [
    {
      "source_marker": "S1",
      "file_name": "paper1.pdf",
      "chunk_index": 12,
      "document_id": "ad1807bb-...",
      "relevance_score": 0.8234
    }
  ],
  "chunks_retrieved": 15,
  "fact_check": null
}
```

**Trường `fact_check`** sẽ có dữ liệu khi `FACTCHECK_SERVICE_URL` được cấu hình:

```json
{
  "label": "SUPPORTED",
  "confidence": 0.87,
  "explanation": "Câu trả lời phù hợp với nội dung tài liệu.",
  "stage": "llm_judge"
}
```

---

## Cấu trúc thư mục

```
service_qa/
├── config/
│   └── config.py          # Cấu hình từ .env (Pydantic Settings)
├── data_access/
│   └── supabase_client.py # CRUD với Supabase DB + Storage
├── embedding/
│   └── embedder.py        # Load model E5, cache với lru_cache
├── retrieval/
│   └── pgvector_store.py  # Chunk, embed, lưu và tìm kiếm vector
├── generation/
│   └── generator.py       # Prompt + gọi Groq, trả về answer + citations
├── serving/
│   └── main.py            # FastAPI app, endpoints, background tasks
├── Dockerfile
├── requirements.txt
├── .env
└── README.md
```

## Luồng xử lý

```
Upload PDF
    │
    ├─► Supabase Storage (lưu file gốc)
    ├─► Supabase DB: bảng documents (metadata, status='processing')
    ├─► PyPDF → text → clean → RecursiveCharacterTextSplitter
    ├─► E5 embedding (batch, CPU)
    ├─► PostgreSQL pgvector: bảng document_chunks
    └─► Cập nhật status='completed'

Hỏi đáp
    │
    ├─► Lưu câu hỏi vào chat_history
    ├─► E5 embed query (prefix "query: ")
    ├─► pgvector similarity search (cosine, TOP_K=20, min_score=0.45)
    ├─► Lấy chat history (5 lượt gần nhất)
    ├─► Build prompt → Groq LLM
    ├─► Parse citations [S1][S2]...
    ├─► (Tuỳ chọn) Gọi service_factcheck
    ├─► Lưu câu trả lời vào chat_history
    └─► Trả về answer + citations + fact_check
```

## Biến môi trường

| Biến                    | Bắt buộc | Mô tả                                         |
| ----------------------- | -------- | --------------------------------------------- |
| `GROQ_API_KEY`          | Có       | API key Groq                                  |
| `SUPABASE_URL`          | Có       | URL project Supabase                          |
| `SUPABASE_KEY`          | Có       | Anon/public key                               |
| `SUPABASE_SERVICE_KEY`  | Có       | Service role key (bypass RLS)                 |
| `SUPABASE_JWT_SECRET`   | Có       | JWT secret (dùng khi verify token thật)       |
| `PG_CONN_STRING`        | Có       | PostgreSQL connection string                  |
| `FACTCHECK_SERVICE_URL` | Không    | URL của service_factcheck (để trống = bỏ qua) |

## Xử lý sự cố

**Upload thành công nhưng `/ask/` trả về "không tìm thấy tài liệu"**

Chạy SQL trong Supabase SQL Editor để kiểm tra:

```sql
SELECT file_name, status, COUNT(dc.id) as chunks
FROM documents d
LEFT JOIN document_chunks dc ON dc.document_id = d.id
GROUP BY d.file_name, d.status;
```

Nếu `status = 'processing'` nhưng có chunks, chạy:

```sql
UPDATE documents SET status = 'completed' WHERE status = 'processing';
```

**Lỗi rate limit từ Groq**

Service tự retry tối đa 4 lần với exponential backoff (5-60s). Nếu vẫn fail, đợi 1 phút rồi thử lại.
