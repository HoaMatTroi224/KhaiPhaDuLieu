import torch
import logging
from models.model_loader import load_model, get_device
from config.settings import settings

logger = logging.getLogger(__name__)

MAP_PROMPT = (
    "Tóm tắt đoạn văn bản khoa học sau bằng tiếng Việt. "
    "Giữ nguyên các thông tin quan trọng: số liệu, thuật ngữ chuyên môn, kết quả thí nghiệm:\n\n"
)

REDUCE_PROMPT = (
    "Tổng hợp các tóm tắt sau thành một bản tóm tắt khoa học liền mạch bằng tiếng Việt. "
    "Ưu tiên: mục tiêu nghiên cứu, phương pháp chính, kết quả quan trọng nhất và kết luận. "
    "Loại bỏ thông tin trùng lặp, giữ thuật ngữ chuyên môn:\n\n"
)


class SummaryGenerator:
    def __init__(self):
        self.model, self.tokenizer = load_model()
        self.device = get_device()

    def generate(self, text: str) -> dict:
        """
        Single-pass nếu text vừa context window.
        Flat Map-Reduce nếu ≤ 5 chunks.
        Hierarchical Map-Reduce nếu > 5 chunks.
        """
        if not text or not text.strip():
            raise ValueError("Input text không được để trống")

        text = text.strip()
        total_tokens = len(self.tokenizer.encode(text, add_special_tokens=False))

        # ── Single-pass ──
        if total_tokens <= settings.MAP_REDUCE_CHUNK_TOKENS:
            inputs = self._tokenize(REDUCE_PROMPT + text)
            summary, output_tokens = self._run_generation(
                inputs,
                max_new_tokens=settings.MAX_FINAL_TARGET_LENGTH,
                min_new_tokens=settings.MIN_TARGET_LENGTH,
            )
            return {"summary": summary, "input_tokens": inputs["input_ids"].shape[1], "output_tokens": output_tokens}

        # ── Map phase ──
        chunks = self._split_into_chunks(text)
        logger.info(f"map-reduce: {total_tokens} tokens → {len(chunks)} chunks (hierarchical={len(chunks) > 5})")

        chunk_summaries = self._map_phase(chunks)

        # ── Reduce phase ──
        if len(chunks) <= 5:
            final_summary, output_tokens = self._flat_reduce(chunk_summaries)
        else:
            final_summary, output_tokens = self._hierarchical_reduce(chunk_summaries)

        logger.info(f"done: final summary {len(final_summary)} chars")
        return {"summary": final_summary, "input_tokens": total_tokens, "output_tokens": output_tokens}

    def _tokenize(self, text: str):
        return self.tokenizer(
            text,
            max_length=settings.MAX_INPUT_LENGTH,
            truncation=True,
            return_tensors="pt",
        ).to(self.device)

    def _run_generation(
        self,
        inputs: dict,
        max_new_tokens: int,
        min_new_tokens: int = 0,
        length_penalty: float = 2.0,
    ) -> tuple[str, int]:
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                min_new_tokens=min_new_tokens,
                num_beams=settings.NUM_BEAMS,
                no_repeat_ngram_size=settings.NO_REPEAT_NGRAM_SIZE,
                length_penalty=length_penalty,
                early_stopping=False,
            )
        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True), output_ids.shape[1]

    def _split_into_chunks(self, text: str) -> list[str]:
        token_ids = self.tokenizer.encode(text, add_special_tokens=False)
        chunks = []
        start = 0
        while start < len(token_ids):
            end = min(start + settings.MAP_REDUCE_CHUNK_TOKENS, len(token_ids))
            chunks.append(self.tokenizer.decode(token_ids[start:end], skip_special_tokens=True))
            if end >= len(token_ids):
                break
            start = end - settings.MAP_REDUCE_OVERLAP_TOKENS
        return chunks

    def _map_phase(self, chunks: list[str]) -> list[str]:
        summaries = []
        for i, chunk in enumerate(chunks):
            inputs = self._tokenize(MAP_PROMPT + chunk)
            summary, _ = self._run_generation(inputs, max_new_tokens=settings.MAX_CHUNK_TARGET_LENGTH)
            summaries.append(summary)
            logger.info(f"  chunk {i + 1}/{len(chunks)}: {len(chunk)} chars → {len(summary)} chars")
        return summaries

    def _reduce_once(
        self,
        summaries: list[str],
        max_new_tokens: int,
        min_new_tokens: int = 0,
    ) -> tuple[str, int]:
        combined = REDUCE_PROMPT + " ".join(summaries)
        inputs = self._tokenize(combined)
        return self._run_generation(inputs, max_new_tokens=max_new_tokens, min_new_tokens=min_new_tokens)

    def _flat_reduce(self, chunk_summaries: list[str]) -> tuple[str, int]:
        return self._reduce_once(
            chunk_summaries,
            max_new_tokens=settings.MAX_FINAL_TARGET_LENGTH,
            min_new_tokens=settings.MIN_TARGET_LENGTH,
        )

    def _hierarchical_reduce(self, chunk_summaries: list[str]) -> tuple[str, int]:
        group_size = settings.MAP_REDUCE_GROUP_SIZE
        groups = [
            chunk_summaries[i : i + group_size]
            for i in range(0, len(chunk_summaries), group_size)
        ]
        logger.info(f"  hierarchical: {len(chunk_summaries)} chunk summaries → {len(groups)} groups")

        group_summaries = []
        for j, group in enumerate(groups):
            g_summary, _ = self._reduce_once(group, max_new_tokens=settings.MAX_GROUP_TARGET_LENGTH)
            group_summaries.append(g_summary)
            logger.info(f"  group {j + 1}/{len(groups)}: {len(group)} summaries → {len(g_summary)} chars")

        return self._reduce_once(
            group_summaries,
            max_new_tokens=settings.MAX_FINAL_TARGET_LENGTH,
            min_new_tokens=settings.MIN_TARGET_LENGTH,
        )


# Module-level singleton — load model một lần khi import
_generator: SummaryGenerator | None = None


def get_generator() -> SummaryGenerator:
    global _generator
    if _generator is None:
        _generator = SummaryGenerator()
    return _generator


def generate_summary(text: str) -> dict:
    return get_generator().generate(text)
