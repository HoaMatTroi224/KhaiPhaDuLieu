import json
import logging

from fastapi import APIRouter, Depends
from uuid import UUID
from ..dependencies import get_current_user_id, get_chat_generator
from ..database import get_db
from ..services_chat.retrieval import call_factcheck, retrieve_chunks
from ..services_chat.chat_generator import ChatGenerator
from ..models import ChatHistory, DocumentChunk
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, func

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


def _log_answer_response(
    project_id: UUID,
    thread_id: UUID,
    user_id: UUID,
    response: dict,
) -> None:
    debug_payload = {
        "project_id": str(project_id),
        "thread_id": str(thread_id),
        "user_id": str(user_id),
        "response": response,
    }
    debug_text = json.dumps(debug_payload, ensure_ascii=False, default=str)

    logger.warning(
        "answer_question response project_id=%s thread_id=%s user_id=%s response=%s",
        project_id,
        thread_id,
        user_id,
        response,
    )
    print(f"[DEBUG answer_question response] {debug_text}", flush=True)

@router.post("/answer")
async def answer_question(
    project_id: UUID,
    thread_id: UUID,
    question: str,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    generator: ChatGenerator = Depends(get_chat_generator)
):
    """
    Hỏi đáp dựa trên tài liệu (Cross-Document RAG).

    Pipeline:
    1. Embed câu hỏi → tìm Top-K chunks liên quan nhất trong toàn bộ project (PGVector)
    2. Đóng gói tất cả chunks vào prompt (stuffing) kèm nhãn nguồn [S1], [S2],...
    3. Gemini sinh câu trả lời, tự động trích dẫn nguồn trong văn bản
    4. Trả về answer + danh sách citations (file, đoạn, điểm tương đồng)

    Response:
      - answer: câu trả lời với nhãn [S1][S2] nhúng trong văn bản
      - citations: các nguồn được trích dẫn (file_name, chunk_index, document_id, relevance_score)
      - chunks_retrieved: tổng số chunks đưa vào context
    """
    question = question.strip()
    if not question:
        return {
            "answer": "Empty question.",
            "citations": [],
            "chunks_retrieved": 0,
            "fact_check": None,
        }

    # 1. Lưu câu hỏi vào chat_history
    user_msg = ChatHistory(
        user_id=user_id,
        project_id=project_id,
        thread_id=thread_id,
        role="user",
        content=question
    )
    db.add(user_msg)

    # 2. Cross-document RAG: tìm Top-K chunks trong toàn bộ project
    chunks = await retrieve_chunks(project_id, question, db)  # dùng TOP_K_CHUNKS từ config

    if not chunks:
        chunk_count = await db.scalar(
            select(func.count(DocumentChunk.id))
            .where(DocumentChunk.project_id == project_id)
        )
        if chunk_count:
            answer_text = "Tôi chưa tìm thấy đoạn tài liệu phù hợp với câu hỏi này. Bạn hãy thử hỏi cụ thể hơn hoặc dùng từ khóa xuất hiện trong tài liệu nhé."
        else:
            answer_text = "Dự án này chưa có đoạn tài liệu nào được lập chỉ mục. Vui lòng kiểm tra lại trạng thái xử lý tài liệu."
        assistant_msg = ChatHistory(
            project_id=project_id,
            thread_id=thread_id,
            user_id=user_id,
            role="assistant",
            content=answer_text,
            citations=[],
            chunks_retrieved=0,
            fact_check=None,
        )
        db.add(assistant_msg)
        await db.commit()

        response = {
            "answer": answer_text,
            "citations": [],
            "chunks_retrieved": 0,
            "fact_check": None,
        }
        _log_answer_response(project_id, thread_id, user_id, response)

        return response

    # 3. Lấy lịch sử chat để AI có ngữ cảnh hội thoại
    chat_history_query = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.project_id == project_id, ChatHistory.thread_id == thread_id)
        .order_by(desc(ChatHistory.created_at))
        .limit(10)
    )

    messages = chat_history_query.scalars().all()
    chat_history = [{"role": m.role, "content": m.content} for m in reversed(messages)]

    # 4. Sinh câu trả lời với trích dẫn nguồn
    result = await generator.answer_question(chunks, question, chat_history)

    # 5. Fact-check câu trả lời trước khi trả về 
    factcheck_result = await call_factcheck(result["answer"], chunks)

    # 6. Lưu câu trả lời vào chat_history
    assistant_msg = ChatHistory(
        user_id=user_id,
        project_id=project_id,
        thread_id=thread_id,
        role="assistant",
        content=result["answer"],
        citations=result["citations"],
        chunks_retrieved=len(chunks),
        fact_check=factcheck_result,
    )
    db.add(assistant_msg)

    await db.commit() # commit ở cuối


    response = {
        "answer": result["answer"],
        "citations": result["citations"],
        "chunks_retrieved": len(chunks),
        "fact_check": factcheck_result,
    }

    # Thêm cảnh báo nếu bị REFUTED
    if factcheck_result and factcheck_result.get("label") == "REFUTED":
        response["warning"] = (
            f"⚠️ Câu trả lời này có thể không chính xác so với tài liệu. "
            f"{factcheck_result.get('explanation', '')}"
        )
    elif factcheck_result and factcheck_result.get("label") == "NEI":
        response["disclaimer"] = "ℹ️ Thông tin chưa được kiểm chứng đầy đủ từ tài liệu."

    _log_answer_response(project_id, thread_id, user_id, response)

    return response

@router.get("/history")
async def get_chat_history(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
    # limit: int = 50
    # offset: int = 0
):
    result = await db.execute(
        select(ChatHistory)
        .where(
            ChatHistory.user_id == user_id,
            ChatHistory.project_id == project_id
        )
        .order_by(asc(ChatHistory.created_at))
        # .offset(offset)
        # .limit(limit)
    )

    messages = result.scalars().all()
    return [
        {
            "id": message.id,
            "user_id": message.user_id,
            "project_id": message.project_id,
            "thread_id": message.thread_id,
            "role": message.role,
            "content": message.content,
            "citations": message.citations,
            "chunks_retrieved": message.chunks_retrieved,
            "fact_check": message.fact_check,
            "created_at": message.created_at,
        }
        for message in messages
    ]
