from pydantic_settings import BaseSettings
from pydantic import Field
import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings(BaseSettings):
    GROQ_API_KEY: str = Field(default=os.getenv("GROQ_API_KEY", ""))
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_JWT_SECRET: str = Field(default=os.getenv("SUPABASE_JWT_SECRET", ""))
    PG_CONN_STRING: str = Field(default=os.getenv("PG_CONN_STRING", ""))
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-base"

    SUPABASE_STORAGE_BUCKET: str = "documents"

    # File upload limits
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_MIME_TYPES: list = ["application/pdf"]

    # Chunking 
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 120

    # RAG retrieval
    TOP_K_CHUNKS: int = 20
    MIN_SIMILARITY_SCORE: float = 0.45  # lọc chunks không liên quan (0.0-1.0)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        protected_namespaces = ()

settings = Settings()
