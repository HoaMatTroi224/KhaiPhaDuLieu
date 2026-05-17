# 🌟 Dự án Khai phá Dữ liệu: Summarize Paper

---

## 📖 Giới thiệu

**KhaiPhaDuLieu** là một hệ thống tự động hóa toàn diện được thiết kế để thu thập, xử lý và khai thác thông tin từ dữ liệu báo khoa học tiếng Việt. Dự án sử dụng ngôn ngữ Python 100%, tích hợp các công nghệ tiên tiến bao gồm:
- **Trí tuệ nhân tạo (AI):** Hỗ trợ tóm tắt bài báo và hỏi đáp thông minh.
- **Xử lý dữ liệu lớn:** Làm sạch, chuẩn hóa và lưu trữ tập trung.
- **Giao diện người dùng hiện đại:** Gồm cả giao diện web và ứng dụng mobile.

---

## 🎯 Mục tiêu và Tính năng nổi bật

### Mục tiêu:
- Tự động hóa thu thập và quản lý bài báo khoa học.
- Xây dựng các dịch vụ AI để truy vấn và cung cấp thông tin nhanh chóng, chính xác.
- Hỗ trợ việc khai thác dữ liệu bài báo khoa học để phục vụ nghiên cứu.

### Tính năng nổi bật:
1. **Thu thập dữ liệu tự động:**
   - Crawl dữ liệu từ nguồn báo khoa học VJST, trích xuất PDF + metadata.
2. **Tiền xử lý mạnh mẽ:**
   - Làm sạch văn bản, chuyển đổi sang Unicode chuẩn.
3. **Tóm tắt và hỏi đáp bằng AI:**
   - Ứng dụng `VietAI/vit5-base` với LoRA và RAG index embedding.


---

## 🗂️ Cấu trúc thư mục Dự án Chi Tiết

```plaintext
KhaiPhaDuLieu/
├── README.md                     # Hướng dẫn tổng quan dự án
│
├── data/                         # Tiền xử lý dữ liệu
│   ├── crawl_data.py             # Script crawl và thu thập bài báo khoa học
│   └── data_preprocessing.py     # Làm sạch và chuẩn hóa dữ liệu
│
├── ai_module/                    # Các module AI hỗ trợ QA, Fact-check và tóm tắt (Docker services)
│   ├── docker-compose.yml        # Orchestration các AI services
│   ├── README.md                 # Hướng dẫn tổng thể module AI
│   │
│   ├── gateway/                  # API Gateway - điểm vào chính cho các dịch vụ AI
│   │   ├── Dockerfile           # Container image cho gateway
│   │   └── main.py              # Routing chính, điều hướng requests tới các services
│   │
│   ├── service_qa/              # Dịch vụ Hỏi Đáp (RAG-based QA)
│   │   ├── Dockerfile           # Container image cho QA service
│   │   ├── requirements.txt      # Thư viện cần thiết
│   │   ├── config/              # Cấu hình QA
│   │   │   └── config.py
│   │   ├── data_access/         # CRUD DB PostgreSQL/Supabase + xử lý metadata
│   │   │   └── supabase_client.py
│   │   ├── embedding/           # Xử lý vector embedding (E5 model)
│   │   │   └── embedder.py
│   │   ├── generation/          # RAG-based answer generator
│   │   │   └── generator.py
│   │   ├── retrieval/           # Truy vấn vector database (pgvector)
│   │   │   └── pgvector_store.py
│   │   └── serving/             # Endpoints chính (FastAPI)
│   │       └── main.py
│   │
│   ├── service_factcheck/       # Dịch vụ Kiểm chứng Sự kiện (NLI-based)
│   │   ├── Dockerfile           # Container image cho Fact-check service
│   │   ├── download_model.py    # Script tải models
│   │   ├── requirements.txt      # Thư viện cần thiết
│   │   ├── config/              # Cấu hình Fact-check
│   │   │   └── settings.py
│   │   ├── inference/           # Inference NLI model
│   │   │   └── nli.py
│   │   ├── models/              # Model loading utilities
│   │   │   └── model_loader.py
│   │   └── serving/             # Endpoints chính (FastAPI)
│   │       ├── api.py
│   │       └── schemas.py
│   │
│   └── service_summarize/       # Dịch vụ Tóm tắt bài báo (ViT5 + LoRA)
│       ├── Dockerfile           # Container image cho Summarize service
│       ├── download_model.py    # Script tải models
│       ├── requirements.txt      # Thư viện cần thiết
│       ├── README.md             # Tài liệu dịch vụ Tóm tắt
│       ├── config/              # Cấu hình Tóm tắt
│       │   └── settings.py
│       ├── inference/           # Inference summarization models
│       │   ├── pdf_extractor.py # Trích xuất PDF
│       │   └── summarize.py     # Logic tóm tắt bằng ViT5
│       ├── models/              # Model loading utilities
│       │   ├── model_loader.py
│       │   └── vit5-lora-adapter/ # Fine-tuned ViT5 base + LoRA adapters
│       └── serving/             # Endpoints chính (FastAPI)
│           └── app.py
│
├── test/                         # Test scripts
│   ├── test_api.py              # Test các API endpoints
│   └── test_data.py             # Test data pipeline
│
├── web/                          # Giao diện Web (Backend + Frontend)
│   ├── docker-compose.yml        # Orchestration web services
│   ├── README.md                 # Hướng dẫn cài đặt web
│   │
│   ├── backend/                  # Backend FastAPI
│   │   ├── Dockerfile           # Container image cho backend
│   │   ├── requirements.txt      # Thư viện cần thiết
│   │   └── app/                  # Application backend logic
│   │       ├── main.py           # Điểm vào chính của FastAPI
│   │       ├── config.py         # Cấu hình backend
│   │       ├── core.py           # Các hàm core utilities
│   │       ├── database.py       # Kết nối database
│   │       ├── dependencies.py   # Dependency injection
│   │       ├── models.py         # Mô hình DB
│   │       ├── schemas.py        # Pydantic validation schemas
│   │       ├── cache.py          # Cache utilities
│   │       ├── routers/          # API routes (upload, QA, log, ...)
│   │       └── services_chat/    # Services cho chat/QA
│   │
│   └── frontend/                 # Frontend Next.js
│       ├── Dockerfile           # Container image cho frontend
│       ├── package.json          # Dependencies Node.js
│       ├── tsconfig.json         # Cấu hình TypeScript
│       ├── next.config.ts        # Cấu hình Next.js
│       ├── postcss.config.mjs    # Cấu hình PostCSS
│       ├── eslint.config.mjs     # Cấu hình ESLint
│       ├── proxy.ts              # Proxy API backend
│       ├── components.json       # Cấu hình UI components
│       ├── AGENTS.md             # Cấu hình AI agents cho Copilot
│       ├── CLAUDE.md             # Cấu hình Claude
│       ├── README.md             # Tài liệu frontend
│       ├── app/                  # Routing chính Next.js
│       ├── components/           # React Components tái sử dụng
│       ├── lib/                  # Utilities và helpers
│       ├── public/               # Tài nguyên tĩnh
│       └── postcss.config.mjs    # PostCSS configuration
│
└── mobile/                       # Ứng dụng di động (Expo React Native)
    ├── app.json                  # Cấu hình Expo
    ├── package.json              # Dependencies Node.js
    ├── tsconfig.json             # Cấu hình TypeScript
    ├── eslint.config.js          # Cấu hình ESLint
    ├── app/                      # Cấu trúc chính Expo
    │   ├── _layout.tsx           # Root layout
    │   ├── index.tsx             # Trang chính
    │   ├── login.tsx             # Trang đăng nhập
    │   ├── register.tsx          # Trang đăng ký
    │   ├── chat.tsx              # Trang chat
    │   ├── Summary.tsx           # Trang tóm tắt
    │   ├── modal.tsx             # Modal dialogs
    │   ├── (tabs)/               # Tab navigation screens
    │   │   ├── _layout.tsx
    │   │   ├── index.tsx
    │   │   ├── library.tsx
    │   │   └── new-project.tsx
    ├── components/               # React Native Components
    │   ├── external-link.tsx
    │   ├── haptic-tab.tsx
    │   ├── hello-wave.tsx
    │   ├── parallax-scroll-view.tsx
    │   ├── themed-text.tsx
    │   ├── themed-view.tsx
    │   └── ui/                   # UI component library
    ├── constants/                # Hằng số ứng dụng
    │   └── theme.ts
    ├── hooks/                    # Custom React hooks
    │   ├── use-color-scheme.ts
    │   ├── use-color-scheme.web.ts
    │   └── use-theme-color.ts
    ├── lib/                      # Utilities
    │   ├── backend.ts            # Backend API client
    │   └── supabase.ts           # Supabase client
    └── assets/                   # Tài nguyên ứng dụng
        └── images/
```

---

## 🛠️ Hướng dẫn cài đặt và triển khai

### 1. Yêu cầu hệ thống
- **Ngôn ngữ lập trình:** Python 3.10+
- **Cơ sở dữ liệu:** PostgreSQL (hoặc Supabase)
- **Công cụ bổ trợ:** Docker, Node.js, npm

### 2. Các bước cài đặt

#### [A] Chuẩn bị môi trường
- Tạo môi trường ảo và cài đặt dependencies (python, npm). 
- Xem chi tiết tại từng `README.md` của các thư mục.

#### [B] Triển khai cục bộ/dùng Docker
- Chi tiết setup nằm tại các tệp hướng dẫn trong từng nhánh.

---

Hãy sử dụng README này để triển khai đồng bộ và phát triển dự án.
