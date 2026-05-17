from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    NLI_MODEL: str = "cross-encoder/nli-deberta-v3-small"
    CONFIDENCE_THRESHOLD: float = 0.70
    MAX_EVIDENCE_CHUNKS: int = 10
    # Per-label thresholds — REFUTED cần chắc hơn để tránh false positive
    SUPPORTED_THRESHOLD: float = 0.65
    REFUTED_THRESHOLD: float = 0.80
    NEI_THRESHOLD: float = 0.60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        protected_namespaces=(),
    )


settings = Settings()
