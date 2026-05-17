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
