from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    ADAPTER_PATH: str = os.getenv(
        "ADAPTER_PATH",
        "./models/vit5-lora-adapter"
    )
    BASE_MODEL_NAME: str = "VietAI/vit5-base"

    MAX_INPUT_LENGTH: int = 1024
    MAX_CHUNK_TARGET_LENGTH: int = 128   # Map phase: tóm tắt mỗi chunk
    MAX_GROUP_TARGET_LENGTH: int = 200   # Hierarchical: tóm tắt mỗi group
    MAX_FINAL_TARGET_LENGTH: int = 256   # Reduce phase: bản tóm tắt cuối
    MIN_TARGET_LENGTH: int = 50
    NUM_BEAMS: int = 2
    LENGTH_PENALTY: float = 2.0
    NO_REPEAT_NGRAM_SIZE: int = 3

    MAP_REDUCE_CHUNK_TOKENS: int = 874
    MAP_REDUCE_OVERLAP_TOKENS: int = 50
    MAP_REDUCE_GROUP_SIZE: int = 4       # Hierarchical: số chunks/group

    DEVICE: str = "auto"

    class Config:
        env_file = ".env"

settings = Settings()
