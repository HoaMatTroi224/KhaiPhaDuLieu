# service_summarize

FastAPI service tóm tắt bài báo khoa học tiếng Việt, sử dụng **ViT5-base** được fine-tune với LoRA adapter.

---

## Kiến trúc

```
Input text / PDF
      │
      ▼
 PDF Extractor (PyMuPDF)
      │
      ▼
 Map-Reduce Summarizer
  ├─ Split thành chunks (~874 tokens/chunk)
  ├─ Tóm tắt từng chunk song song (Map)
  └─ Tổng hợp thành bản tóm tắt cuối (Reduce)
      │
      ▼
   ViT5-base + LoRA Adapter
```

## Cài đặt & Chạy

### Bước 1 — Clone repo

```bash
git clone <repo-url>
cd service_summarize
```

### Bước 2 — Tạo file `.env`

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Nội dung `.env` mặc định (không cần sửa gì khi chạy Docker):

```env
ADAPTER_PATH=./models/vit5-lora-adapter
BASE_MODEL_NAME=VietAI/vit5-base
MAX_INPUT_LENGTH=1024
MAX_TARGET_LENGTH=512
NUM_BEAMS=2
DEVICE=auto
```

### Bước 3 — Build Docker image

````bash
docker build -t service-summarize .

### Bước 4 — Chạy container

```bash
docker run -d \
  --name summarize \
  -p 8001:8001 \
  --env-file .env \
  service-summarize
````

> **Lần đầu khởi động** sẽ tải model `VietAI/vit5-base` (~900MB) từ HuggingFace — mất 1–3 phút tùy mạng.
> Để cache model và không tải lại mỗi lần restart, thêm volume:
>
> ```bash
> docker run -d \
>   --name summarize \
>   -p 8001:8001 \
>   --env-file .env \
>   -v hf_model_cache:/root/.cache/huggingface \
>   service-summarize
> ```

### Bước 5 — Kiểm tra service đã sẵn sàng

```bash
# Xem log khởi động
docker logs -f summarize
```

Chờ đến khi thấy dòng:

```
INFO:models.model_loader:Model loaded and ready!
INFO:     Application startup complete.
```

---

## Test API

### Swagger UI (trình duyệt)

Mở: **http://localhost:8001/docs**

### Health check

```bash
curl http://localhost:8001/health
# {"status":"ok","service":"summarize"}
```

## API Reference

| Method | Endpoint                | Mô tả                        |
| ------ | ----------------------- | ---------------------------- |
| GET    | `/health`               | Kiểm tra service còn sống    |
| GET    | `/docs`                 | Swagger UI                   |
| POST   | `/api/v1/summarize`     | Tóm tắt raw text (JSON)      |
| POST   | `/api/v1/summarize/pdf` | Tóm tắt file PDF (multipart) |

### POST `/api/v1/summarize`

### POST `/api/v1/summarize/pdf`

**Form data:** `file` — file `.pdf`, tối đa 20MB, phải là PDF có text (không hỗ trợ PDF scan/ảnh).

---

## Lưu ý quan trọng

> **Model chỉ hỗ trợ tiếng Việt.**
> ViT5 được fine-tune trên tập dữ liệu bài báo khoa học tiếng Việt.
> Nếu input là tiếng Anh, output sẽ không có ý nghĩa.

| Thông số            | Giá trị                                 |
| ------------------- | --------------------------------------- |
| Ngôn ngữ hỗ trợ     | Tiếng Việt                              |
| Độ dài input tối đa | 20.000 ký tự                            |
| Độ dài output       | 80–512 tokens                           |
| Inference           | CPU (không cần GPU)                     |
| Thời gian xử lý     | ~15s (text ngắn) / ~250s (PDF dài, CPU) |

---

## Quản lý container

```bash
# Dừng
docker stop summarize

# Khởi động lại
docker start summarize

# Xem log real-time
docker logs -f summarize

# Xóa container
docker rm -f summarize

# Xóa image
docker rmi service-summarize
```
