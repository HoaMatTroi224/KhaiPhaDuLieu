# KPDL - AI Paper Summarizer

Một ứng dụng web để quản lý, phân tích và tóm tắt tài liệu học thuật bằng công nghệ AI.

## Tính năng chính

- 📚 **Quản lý dự án**: Tổ chức và quản lý các dự án nghiên cứu
- 📄 **Xử lý tài liệu**: Tải lên và xử lý file PDF với GROBID và PyMuPDF4LLM
- 🤖 **Chat AI**: Tương tác với AI để hỏi đáp về nội dung tài liệu
- 📊 **Tóm tắt thông minh**: Tự động tạo tóm tắt từ tài liệu
- 🔍 **Tìm kiếm**: Tìm kiếm thông minh qua tài liệu dựa trên vector embeddings

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────┐
│  Frontend (Next.js + TypeScript + React)    │
│  Running on: http://localhost:3000          │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│  Backend (FastAPI)                          │
│  Running on: http://localhost:8000          │
├─────────────────────────────────────────────┤
│  Services:                                  │
│  - Chat & Retrieval (RAG)                   │
│  - Document Processing                      │
│  - Summary Generation                       │
└──────────┬──────────────┬────────────────────┘
           │              │
           ↓              ↓
    ┌────────────┐   ┌──────────────┐
    |PyMuPDF4LLM │   │ PostgreSQL   │
    |(PDF Parse) |   | (Supabase)   |
    └────────────┘   └──────────────┘
```

## Yêu cầu hệ thống

- Docker & Docker Compose
- Python 3.10+
- Node.js 18+
- npm hoặc yarn

## Cài đặt và chạy ứng dụng

### 1. Chuẩn bị môi trường

Clone repository:
```bash
git clone <repository-url> <branch-name>
cd Khaiphadulieu
```

### 2. Khởi động Backend và Services

Từ **thư mục gốc** (`KPDL`), chạy:

```bash
docker-compose up
```

Điều này sẽ khởi động:
- **GROBID** service (port 8070) - Để xử lý PDF
- **Backend** FastAPI (port 8000) - API server
- **PostgreSQL Database** - Cơ sở dữ liệu

**Lưu ý**: Hãy chờ cho đến khi tất cả các service khởi động thành công (bạn sẽ thấy thông báo "Application startup complete" từ FastAPI).

### 3. Khởi động Frontend

**Trong một terminal mới**, chạy các lệnh sau:

```bash
cd frontend
npm run dev
```

Frontend sẽ chạy trên: **http://localhost:3000**

### 4. Kiểm tra tình trạng

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

## Cấu trúc dự án

```
KPDL/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── main.py            # Entry point
│   │   ├── models.py          # Database models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── routers/           # API endpoints
│   │   │   ├── chat.py
│   │   │   ├── documents.py
│   │   │   ├── projects.py
│   │   │   └── summaries.py
│   │   ├── services_chat/     # Chat & RAG services
│   │   │   ├── chat_generator.py
│   │   │   ├── embedder.py
│   │   │   ├── pgvector_store.py
│   │   │   └── retrieval.py
│   │   └── services_summary/  # Summary generation services
│   │       ├── file_processor.py
│   │       ├── pdf_extractor.py
│   │       └── summary_generator.py
│   ├── db/                    # Database files
│   │   ├── init.sql          # Schema initialization
│   │   ├── papers.csv        # Sample data
│   │   └── outputs/          # Processed documents
│   └── requirements.txt       # Python dependencies
│
├── frontend/                  # Next.js frontend application
│   ├── app/                  # Next.js app directory
│   │   ├── page.tsx          # Home page
│   │   ├── dashboard/        # Dashboard pages
│   │   ├── projects/         # Projects pages
│   │   └── login/            # Authentication pages
│   ├── components/           # React components
│   │   ├── ChatBox.tsx
│   │   ├── DocumentViewer.tsx
│   │   ├── FileUploadArea.tsx
│   │   └── ...
│   ├── lib/                  # Utility functions
│   ├── package.json          # Node dependencies
│   └── tsconfig.json         # TypeScript config
│
├── docker-compose.yml        # Docker Compose configuration
└── README.md                 # This file
```

## Luồng hoạt động chính

1. **Người dùng** đăng nhập/đăng ký trên Frontend
2. **Tạo dự án** và **tải lên tài liệu** (PDF)
3. **GROBID** xử lý PDF và trích xuất nội dung
4. **Backend** lưu trữ tài liệu và tạo embeddings
5. **Chat AI** - Người dùng có thể:
   - Hỏi câu hỏi về tài liệu
   - Backend sử dụng RAG (Retrieval-Augmented Generation) để tìm kiếm tài liệu liên quan
   - AI trả lời dựa trên nội dung tài liệu
6. **Tóm tắt** - Tự động hoặc thủ công tóm tắt tài liệu

