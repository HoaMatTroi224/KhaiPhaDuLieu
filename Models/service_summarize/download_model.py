"""
Download ViT5 LoRA adapter từ Hugging Face Hub.
Dùng khi adapter chưa có sẵn trong thư mục models/ (Cloud Run, CI/CD, v.v.)
Nếu adapter đã tồn tại ở local → bỏ qua.

Chạy trực tiếp:
    python download_model.py
Hoặc qua env:
    ADAPTER_REPO=CV12323/vit5-summarize HF_TOKEN=hf_... python download_model.py
"""
import os
from pathlib import Path

ADAPTER_PATH = os.getenv("ADAPTER_PATH", "./models/vit5-lora-adapter")
ADAPTER_REPO = os.getenv("ADAPTER_REPO", "CV12323/vit5-summarize")
HF_TOKEN = os.getenv("HF_TOKEN", "") or None

if Path(ADAPTER_PATH).exists() and any(Path(ADAPTER_PATH).iterdir()):
    print(f"Adapter already at '{ADAPTER_PATH}', skipping download.")
else:
    from huggingface_hub import snapshot_download
    print(f"Downloading adapter from '{ADAPTER_REPO}' → '{ADAPTER_PATH}'...")
    snapshot_download(
        repo_id=ADAPTER_REPO,
        local_dir=ADAPTER_PATH,
        token=HF_TOKEN,
    )
    print("Download complete!")
