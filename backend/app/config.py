# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     DATABASE_URL: str
#     SUPABASE_URL: str

#     class Config:
#         env_file = ".env"

# settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    PG_CONNECTION_STRING: str

    EMBEDDING_MODEL: str = "gemini-embedding-2"
    LARGE_LANGUAGE_MODEL: str = "gemini-1.5-flash"

    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_MIME_TYPES: list[str] = ["application/pdf"]

    model_config = SettingsConfigDict(
        env_file=".env",
        protected_namespaces=()
    )

settings = Settings()