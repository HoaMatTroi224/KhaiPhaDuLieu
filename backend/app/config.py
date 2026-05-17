from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GROQ_API_KEY: str
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str 
    SUPABASE_JWT_SECRET: str 
    PG_CONNECTION_STRING: str
    FACTCHECK_SERVICE_URL: str

    # REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_URL: str
    CACHE_PROJECTS_TTL_SECONDS: int = 120
    CACHE_PROJECT_DETAIL_TTL_SECONDS: int = 300
    CACHE_DOCUMENTS_PENDING_TTL_SECONDS: int = 10
    CACHE_DOCUMENTS_READY_TTL_SECONDS: int = 300
    CACHE_SUMMARIES_TTL_SECONDS: int = 86400
    CACHE_SUMMARIES_EMPTY_TTL_SECONDS: int = 5

    # ViT5 tóm tắt qua Cloud Run (thay cho model local)
    VIT5_SUMMARIZE_API_URL: str
    VIT5_SUMMARIZE_TIMEOUT_S: float = 180.0

    # EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # EMBEDDING_MODEL: str = "infloat/multilingual-e5-small"
    EMBEDDING_MODEL: str = "/opt/models/embedding"
    LARGE_LANGUAGE_MODEL: str = "llama-3.3-70b-versatile"

    # ADAPTER_PATH: str = str(Path(__file__).parent / "ai_model" / "vit5-lora-adapter")
    # BASE_MODEL_NAME: str = "VietAI/vit5-base"

    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_MIME_TYPES: list[str] = ["application/pdf"]

    MAX_INPUT_LENGTH: int = 1024
    MIN_TARGET_LENGTH: int = 80 
    MAX_TARGET_LENGTH: int = 512 
    NUM_BEAMS: int = 2
    NO_REPEAT_NGRAM_SIZE: int = 3

    # Map-Reduce: số token mỗi chunk khi text vượt context window
    # MAX_INPUT_LENGTH=1024, để ~150 token headroom → chunk=874
    MAP_REDUCE_CHUNK_TOKENS: int = 874  # 700→874: ít chunk hơn (~11 thay vì 15)
    MAP_REDUCE_OVERLAP_TOKENS: int = 50

    # Dùng GPU nếu có, fallback về CPU
    DEVICE: str = "auto"

    # Chunking 
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 120

    # RAG retrieval
    TOP_K_CHUNKS: int = 20
    MIN_SIMILARITY_SCORE: float = 0.45  # lọc chunks không liên quan (0.0-1.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding = "utf-8",
        protected_namespaces=()
    )

settings = Settings()
