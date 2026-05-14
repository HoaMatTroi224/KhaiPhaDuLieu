from functools import lru_cache
from langchain_groq import ChatGroq
from ..config import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def _is_rate_limit_or_server_error(exc: Exception) -> bool:
    """Retry khi bị rate limit (429) hoặc lỗi server Groq (5xx)."""
    msg = str(exc).lower()
    return "rate_limit" in msg or "429" in msg or "500" in msg or "503" in msg


@lru_cache(maxsize=1)
def _get_llm() -> ChatGroq:
    return ChatGroq(
        model=settings.LARGE_LANGUAGE_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
        timeout=30,
    )


class ChatGenerator:
    def __init__(self):
        pass

    @retry(
        retry=retry_if_exception(_is_rate_limit_or_server_error),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        before_sleep=lambda rs: logger.warning(
            f"[GROQ] Retry {rs.attempt_number}/4 sau {rs.next_action.sleep:.0f}s — {rs.outcome.exception()}"
        ),
    )
    async def answer_question(
        self,
        chunks: List[Dict[str, Any]],
        question: str,
        chat_history: list,
    ) -> Dict[str, Any]:
        """
        Sinh câu trả lời từ danh sách chunks đã truy xuất, kèm trích dẫn nguồn.

        Pipeline theo kiến trúc RAG từ tài liệu:
        1. Format chunks → numbered sources [S1], [S2],... kèm tên file
        2. Lọc chunks quá ngắn hoặc trùng lặp (theo format_docs trong PDF)
        3. Đưa vào prompt template tiếng Việt
        4. Groq LLM sinh câu trả lời có trích dẫn nguồn
        5. Phát hiện các [S1][S2] được dùng → trả về citations
        """
        # --- Lọc và dedup chunks (theo format_docs trong PDF) ---
        seen = set()
        filtered_chunks = []
        for chunk in chunks:
            text = chunk["text"].strip()
            if text and len(text) > 40 and text not in seen:
                filtered_chunks.append(chunk)
                seen.add(text)

        if not filtered_chunks:
            return {
                "answer": "Tôi không tìm thấy đủ thông tin trong tài liệu để trả lời câu hỏi này.",
                "citations": [],
            }

        # --- Format chunks thành numbered sources [S1], [S2],... ---
        sources_block = ""
        for i, chunk in enumerate(filtered_chunks, start=1):
            sources_block += (
                f"[S{i}] (Tài liệu: {chunk['file_name']}, Đoạn #{chunk['chunk_index']}):\n"
                f"{chunk['text'].strip()}\n\n"
            )

        # --- Lịch sử hội thoại ---
        history_str = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in chat_history[-5:]
        ]) or "(Chưa có)"

        # --- Prompt template tiếng Việt (theo chuẩn từ tài liệu RAG) ---
        prompt = f"""Bạn là trợ lý AI phân tích tài liệu tiếng Việt chuyên nghiệp.

        [TÀI LIỆU]:
        {sources_block}
        [LỊCH SỬ HỘI THOẠI]:
        {history_str}

        [CÂU HỎI]:
        {question}

        Hãy trả lời dựa trên tài liệu. Nếu tài liệu không có thông tin, nói rõ "Không có thông tin".
        Trả lời đầy đủ những gì bạn tìm được trong tài liệu, không thêm bất kỳ chi tiết nào ngoài tài liệu.
        Sau mỗi thông tin trích dẫn, ghi ngay nhãn nguồn tương ứng: [S1], [S2],... Nếu nhiều nguồn cùng hỗ trợ một ý, liệt kê tất cả: [S1][S3].

        [TRẢ LỜI]:"""

        llm = _get_llm()
        response = await llm.ainvoke(prompt)
        answer_text = response.content.strip()

        # Tách phần sau "[TRẢ LỜI]:" nếu LLM lặp lại template
        if "[TRẢ LỜI]:" in answer_text:
            answer_text = answer_text.split("[TRẢ LỜI]:")[-1].strip()

        # --- Xác định các nguồn được LLM thực sự trích dẫn ---
        citations = []
        for i, chunk in enumerate(filtered_chunks, start=1):
            if f"[S{i}]" in answer_text:
                citations.append({
                    "source_marker": f"S{i}",
                    "file_name": chunk["file_name"],
                    "chunk_index": chunk["chunk_index"],
                    "document_id": chunk["document_id"],
                    "relevance_score": round(chunk["score"], 4),
                })

        return {
            "answer": answer_text,
            "citations": citations,
        }
