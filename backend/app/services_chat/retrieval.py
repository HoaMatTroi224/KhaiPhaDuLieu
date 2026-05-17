from .pgvector_store import PGVectorStore
import logging
import httpx
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import settings
from ..models import Document, DocumentChunk, DocumentStatus

logger = logging.getLogger(__name__)

FACTCHECK_SERVICE_URL = settings.FACTCHECK_SERVICE_URL

async def recover_stuck_documents(db: AsyncSession):
    """
    Khi server restart, kiểm tra documents bị kẹt 'processing'.
    Nếu đã có chunks trong PGVector -> đánh dấu 'indexed'.
    Nếu không có chunks -> đánh dấu 'failed' để user biết cần upload lại.
    """
    try:
        result = await db.execute(
            select(Document).where(
                Document.status == DocumentStatus.processing
            )
        )

        stuck_docs = result.scalars().all()
        if not stuck_docs:
            return

        for doc in stuck_docs:
            count_result = await db.execute(
                select(func.count(DocumentChunk.id)).where(
                    DocumentChunk.document_id == doc.id
                )
            )
            chunk_count = count_result.scalar_one()

            new_status = (
                DocumentStatus.indexed if chunk_count > 0 else DocumentStatus.failed
            )
            doc.status = new_status
            logger.info("RECOVERED %s -> %s", doc.file_name, new_status.value)

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning(f"RECOVER ERROR: {e}")


async def call_factcheck(answer: str, chunks: list) -> Optional[dict]:
    """
    Gọi service_factcheck để kiểm tra câu trả lời.
    Trả về None nếu service không sẵn sàng (graceful degradation).
    Retry tối đa 2 lần để xử lý Cloud Run cold start (503).
    """
    if not FACTCHECK_SERVICE_URL:
        return None

    evidence = [c["text"] for c in chunks[:10]]
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{FACTCHECK_SERVICE_URL}/verify",
                    json={"claim": answer, "evidence": evidence},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503 and attempt < 2:
                logger.warning(f"Factcheck 503 (attempt {attempt + 1}/3), retrying...")
                import asyncio
                await asyncio.sleep(5 * (attempt + 1))
                last_exc = e
                continue
            last_exc = e
            break
        except Exception as e:
            last_exc = e
            break

    logger.warning(f"Factcheck failed: {last_exc}")
    return None
    
async def retrieve_chunks(
    project_id,
    question,
    db: AsyncSession
):
    return await PGVectorStore(db, project_id).similarity_search(question)
    


