import torch
import logging
from models.model_loader import load_model, get_device
from config.settings import settings

logger = logging.getLogger(__name__)

REDUCE_PROMPT = "Tóm tắt chuyên sâu bài báo khoa học sau bằng tiếng Việt. Bao gồm rõ ràng: mục tiêu nghiên cứu, phương pháp, kết quả chính, kết luận và ý nghĩa khoa học. Trình bày mạch lạc, ngắn gọn, giữ nguyên thuật ngữ chuyên môn:\n\n"


def _run_generation(inputs: dict, model, tokenizer, length_penalty: float = 1.0) -> str:
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_length=settings.MAX_TARGET_LENGTH,
            min_length=settings.MIN_TARGET_LENGTH,
            num_beams=settings.NUM_BEAMS,
            early_stopping=True,
            no_repeat_ngram_size=settings.NO_REPEAT_NGRAM_SIZE,
            length_penalty=length_penalty,
        )
    return tokenizer.decode(output_ids[0], skip_special_tokens=True), output_ids.shape[1]


def _split_into_chunks(text: str, tokenizer, chunk_tokens: int, overlap_tokens: int) -> list[str]:
    """Split text thành các chunks theo token count, với overlap để tránh mất context."""
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    start = 0
    while start < len(token_ids):
        end = min(start + chunk_tokens, len(token_ids))
        chunk_ids = token_ids[start:end]
        chunks.append(tokenizer.decode(chunk_ids, skip_special_tokens=True))
        if end >= len(token_ids):
            break
        start = end - overlap_tokens
    return chunks


def generate_summary(text: str) -> dict:
    """
    Tóm tắt văn bản. Tự động chọn:
    - Single-pass nếu text vừa vào context window
    - Map-Reduce nếu text quá dài

    Returns:
        dict với 'summary', 'input_tokens', 'output_tokens'
    """
    model, tokenizer = load_model()
    device = get_device()

    if not text or not text.strip():
        raise ValueError("Input text không được để trống")

    text = text.strip()

    # Số token thực tế của input
    total_tokens = len(tokenizer.encode(text, add_special_tokens=False))

    # ── Single-pass: text vừa vào model ──
    if total_tokens <= settings.MAP_REDUCE_CHUNK_TOKENS:
        inputs = tokenizer(
            text,
            max_length=settings.MAX_INPUT_LENGTH,
            truncation=True,
            return_tensors="pt"
        ).to(device)

        summary, output_tokens = _run_generation(inputs, model, tokenizer, length_penalty=1.0)
        return {
            "summary": summary,
            "input_tokens": inputs["input_ids"].shape[1],
            "output_tokens": output_tokens,
        }

    # ── Map-Reduce: text quá dài ──
    chunks = _split_into_chunks(
        text, tokenizer,
        chunk_tokens=settings.MAP_REDUCE_CHUNK_TOKENS,
        overlap_tokens=settings.MAP_REDUCE_OVERLAP_TOKENS,
    )
    logger.info(f"Map-Reduce: {total_tokens} tokens → {len(chunks)} chunks")

    # Map: tóm tắt từng chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        inputs = tokenizer(
            chunk,
            max_length=settings.MAX_INPUT_LENGTH,
            truncation=True,
            return_tensors="pt"
        ).to(device)
        chunk_summary, _ = _run_generation(inputs, model, tokenizer, length_penalty=1.0)
        chunk_summaries.append(chunk_summary)
        logger.info(f"  Chunk {i + 1}/{len(chunks)}: {len(chunk)} chars → {len(chunk_summary)} chars")

    # Reduce: tổng hợp các chunk summary thành bản tóm tắt cuối
    combined = REDUCE_PROMPT + " ".join(chunk_summaries)
    inputs = tokenizer(
        combined,
        max_length=settings.MAX_INPUT_LENGTH,
        truncation=True,
        return_tensors="pt"
    ).to(device)

    final_summary, output_tokens = _run_generation(inputs, model, tokenizer, length_penalty=1.5)
    logger.info(f"Map-Reduce done: {len(chunks)} chunks → final summary {len(final_summary)} chars")

    return {
        "summary": final_summary,
        "input_tokens": total_tokens,
        "output_tokens": output_tokens,
    }
