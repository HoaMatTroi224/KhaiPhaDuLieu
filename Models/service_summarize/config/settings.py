from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Đường dẫn đến LoRA adapter
    # Có thể là local path hoặc HuggingFace repo ID
    ADAPTER_PATH: str = os.getenv(
        "ADAPTER_PATH",
        "./models/vit5-lora-adapter"
    )
    BASE_MODEL_NAME: str = "VietAI/vit5-base"

    MAX_INPUT_LENGTH: int = 1024
    MAX_TARGET_LENGTH: int = 512        # 256→512: cho phép tóm tắt dài hơn
    MIN_TARGET_LENGTH: int = 80         # ép model sinh ít nhất 80 token
    NUM_BEAMS: int = 2                  # 4→2: nhanh ~2x, chất lượng giảm nhẹ
    NO_REPEAT_NGRAM_SIZE: int = 3

    # Map-Reduce: số token mỗi chunk khi text vượt context window
    # MAX_INPUT_LENGTH=1024, để ~150 token headroom → chunk=874
    MAP_REDUCE_CHUNK_TOKENS: int = 874  # 700→874: ít chunk hơn (~11 thay vì 15)
    MAP_REDUCE_OVERLAP_TOKENS: int = 50

    # Dùng GPU nếu có, fallback về CPU
    DEVICE: str = "auto"

    class Config:
        env_file = ".env"

settings = Settings()