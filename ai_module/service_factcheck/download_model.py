from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/nli-deberta-v3-small"
print(f"Downloading {MODEL_NAME}...")
CrossEncoder(MODEL_NAME)
print("Download complete!")
