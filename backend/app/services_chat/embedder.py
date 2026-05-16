import os
from threading import Lock
from typing import Optional

from langchain_huggingface import HuggingFaceEmbeddings
from ..config import settings


_embedding_model: Optional[HuggingFaceEmbeddings] = None
_embedding_model_lock = Lock()


def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Lazy singleton embedding model per backend process.

    HuggingFace sentence-transformer models are heavy, so every PGVectorStore
    instance must reuse the same object instead of loading another copy into RAM.
    """
    global _embedding_model

    if _embedding_model is None:
        with _embedding_model_lock:
            if _embedding_model is None:
                model_kwargs = {"device": "cpu"}
                if os.getenv("TRANSFORMERS_OFFLINE") == "1" or os.getenv("HF_HUB_OFFLINE") == "1":
                    model_kwargs["local_files_only"] = True

                _embedding_model = HuggingFaceEmbeddings(
                    model_name=settings.EMBEDDING_MODEL,
                    cache_folder=os.getenv("SENTENCE_TRANSFORMERS_HOME"),
                    model_kwargs=model_kwargs,
                    encode_kwargs={"normalize_embeddings": True},
                )

    return _embedding_model
