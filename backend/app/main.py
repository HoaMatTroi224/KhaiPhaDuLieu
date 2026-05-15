# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import projects, documents, summaries, chat
from .core import lifespan
import os

# ===========================
# Lazy load embedding model
# ===========================
embedding_model = None
EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

def get_embedding_model():
    """Chỉ load model khi cần (lazy load)"""
    global embedding_model
    if embedding_model is None:
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return embedding_model

# ===========================
# FastAPI app
# ===========================
app = FastAPI(title="AI Paper Summarizer", version="1.0.0", lifespan=lifespan)

# ===========================
# CORS middleware
# ===========================
# Cho phép frontend từ Vercel và localhost. Demo nhanh có thể dùng "*" tạm thời
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://khai-pha-du-lieu-dusky.vercel.app",
        "https://khai-pha-du-lieu-git-web-hoamattroi224s-projects.vercel.app",
        "https://khaiphadulieu-frontend.vercel.app",
        # "*"  # Nếu muốn demo nhanh, bỏ comment để cho tất cả domain
    ],
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],
)

# ===========================
# Include all routers
# ===========================
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(summaries.router)
app.include_router(chat.router)

# ===========================
# Health check
# ===========================
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Academic Paper Summary AI System"}
