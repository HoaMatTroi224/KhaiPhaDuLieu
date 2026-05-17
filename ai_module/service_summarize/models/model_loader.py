import torch
import logging
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel
from config.settings import settings

logger = logging.getLogger(__name__)

_model = None
_tokenizer = None


def get_device() -> str:
    if settings.DEVICE == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return settings.DEVICE


def load_model():
    """
    Load base ViT5 + LoRA adapter.
    Gọi một lần khi khởi động app (singleton pattern).
    """
    global _model, _tokenizer

    if _model is not None:
        return _model, _tokenizer

    device = get_device()
    logger.info(f"Loading model on device: {device}")

    # Load tokenizer từ adapter path
    # (tokenizer đã được save_pretrained cùng adapter ở Cell 11)
    logger.info(f"Loading tokenizer from {settings.ADAPTER_PATH}")
    _tokenizer = AutoTokenizer.from_pretrained(
        settings.ADAPTER_PATH,
        use_fast=True
    )

    # Load base model
    logger.info(f"Loading base model: {settings.BASE_MODEL_NAME}")
    dtype = torch.float16 if device == "cuda" else torch.float32
    base_model = AutoModelForSeq2SeqLM.from_pretrained(
        settings.BASE_MODEL_NAME,
        torch_dtype=dtype,
    )

    # Load LoRA adapter lên base model
    logger.info(f"Merging LoRA adapter from {settings.ADAPTER_PATH}")
    _model = PeftModel.from_pretrained(base_model, settings.ADAPTER_PATH)

    # Merge adapter vào weights để inference nhanh hơn
    # (không cần thiết nhưng tăng tốc độ ~15%)
    _model = _model.merge_and_unload()

    _model.to(device)
    _model.eval()

    logger.info("Model loaded and ready!")
    return _model, _tokenizer