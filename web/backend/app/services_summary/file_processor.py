from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import Project, Document, Summary, DocumentStatus
from uuid import UUID
from datetime import datetime
import logging
import time
import asyncio
import os

from .pdf_extractor import PDFExtractor
from .summary_generator import SummaryGenerator
from ..database import AsyncSessionLocal
from ..services_chat.pgvector_store import PGVectorStore
from ..cache import delete_keys
from langchain_core.documents import Document as LangchainDocument

logger = logging.getLogger(__name__)


def _project_documents_cache_key(user_id: UUID, project_id: UUID) -> str:
    return f"user:{user_id}:project:{project_id}:documents"


def _document_summaries_cache_key(user_id: UUID, document_id: UUID) -> str:
    return f"user:{user_id}:document:{document_id}:summaries"


async def _invalidate_document_caches(
    user_id: UUID,
    project_id: UUID,
    document_id: UUID,
) -> None:
    await delete_keys(
        _project_documents_cache_key(user_id, project_id),
        _document_summaries_cache_key(user_id, document_id),
    )


# =========================
# GET DOCUMENT (SAFE)
# =========================
async def _get_document(db: AsyncSession, document_id: UUID, user_id: UUID) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.project.has(Project.user_id == user_id)
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise ValueError("Document not found or access denied")

    return doc


# =========================
# EXTRACT + UPDATE (FIXED)
# =========================
async def _extract_and_update_document(
    db: AsyncSession,
    document: Document,
    extractor: PDFExtractor
) -> dict:

    try:
        # FIX 1: tránh block event loop
        extracted = await asyncio.to_thread(extractor.extract)
        raw = await asyncio.to_thread(extractor.extract_raw_text)

        body_content = extracted.get("content") or ""
        full_content = raw or ""
        content_preview = " ".join(body_content.split())[:300]

        # FIX 2: normalize data source (single source of truth)
        document.title = extracted.get("title") or document.title
        document.authors = extracted.get("authors") or document.authors
        document.abstract = extracted.get("abstract") or document.abstract
        document.extracted_content = body_content or document.extracted_content
        document.full_content = full_content or document.full_content
        document.status = DocumentStatus.processing
        document.updated_at = datetime.utcnow()

        logger.info(
            "Extracted document %s with %s body chars. Preview: %r",
            document.id,
            len(body_content.strip()),
            content_preview,
        )

        await db.commit()
        await _invalidate_document_caches(
            document.user_id,
            document.project_id,
            document.id,
        )

        return {
            "extracted_content": document.extracted_content,
            "full_content": document.full_content
        }

    except Exception as e:
        logger.error(f"Extraction failed for {document.id}: {e}", exc_info=True)
        raise ValueError(f"Failed to extract document: {str(e)}")


# =========================
# SUMMARY GENERATION (FIXED)
# =========================
async def _generate_summary_for_document(
    db: AsyncSession,
    document: Document,
    generator: SummaryGenerator,
    user_id: UUID,
    context: str,
) -> tuple[Summary, dict]:

    if not context or len(context.strip()) < 50:
        raise ValueError("No sufficient content available for summary generation")

    existing = await db.execute(
        select(Summary).where(Summary.document_id == document.id)
    )
    if existing.scalar_one_or_none():
        raise ValueError("Summary already exists for this document")

    result = await generator.generate_summary(text=context)
    summary_text = result["summary"]

    summary = Summary(
        user_id=user_id,
        document_id=document.id,
        summary_text=summary_text,
        created_at=datetime.utcnow(),
    )

    db.add(summary)
    await db.flush()

    logger.info(
        f"Generated summary {summary.id} for document {document.id}"
    )

    return summary, result


async def _ensure_summary_not_exists(db: AsyncSession, document_id: UUID) -> None:
    existing = await db.execute(
        select(Summary).where(Summary.document_id == document_id)
    )
    if existing.scalar_one_or_none():
        raise ValueError("Summary already exists for this document")


# =========================
# MAIN PIPELINE (FIXED)
# =========================
async def process_document(document_id: UUID, user_id: UUID) -> dict:
    t0 = time.perf_counter()
    extractor = None

    async with AsyncSessionLocal() as db:
        try:
            # 1. Get document
            document = await _get_document(db, document_id, user_id)

            # FIX 6: validate file existence + security
            if not document.file_path:
                raise ValueError("Missing file path")

            # if not os.path.exists(document.file_path):
            #     raise ValueError("File not found on server")

            # if not document.file_path.lower().endswith(".pdf"):
            #     raise ValueError("Only PDF documents are supported")

            # 2. init services
            extractor = PDFExtractor(storage_path=document.file_path)
            generator = SummaryGenerator()

            vector_store = PGVectorStore(db=db, project_id=document.project_id)

            # 3. extract
            context = await _extract_and_update_document(
                db=db,
                document=document,
                extractor=extractor
            )
            full = context["full_content"]
            body = context["extracted_content"]

            langchain_docs = [LangchainDocument(
                page_content=full,
                metadata={
                    "document_id": document.id,
                    "project_id": document.project_id,
                    "file_name": document.file_name
                }
            )]

            if not body.strip():
                raise ValueError("Empty extracted content")
            if not full.strip():
                raise ValueError("Empty full content")

            if len(body.strip()) < 50:
                preview = " ".join(body.split())[:300]
                raise ValueError(
                    "No sufficient content available for summary generation "
                    f"(body_chars={len(body.strip())}, preview={preview!r})"
                )

            await _ensure_summary_not_exists(db, document.id)

            summary_task = asyncio.create_task(
                generator.generate_summary(text=body)
            )
            embedding_task = asyncio.create_task(
                vector_store.build_chunk_objects(
                    documents=langchain_docs,
                    document_id=document.id,
                )
            )

            try:
                gen_result, chunk_objects = await asyncio.gather(
                    summary_task,
                    embedding_task,
                )
            except Exception:
                for task in (summary_task, embedding_task):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(
                    summary_task,
                    embedding_task,
                    return_exceptions=True,
                )
                raise

            summary = Summary(
                user_id=user_id,
                document_id=document.id,
                summary_text=gen_result["summary"],
                created_at=datetime.utcnow(),
            )
            db.add(summary)

            chunks_count = len(chunk_objects)
            if chunks_count == 0:
                raise ValueError(
                    "Embedding produced 0 chunks"
                )

            db.add_all(chunk_objects)

            logger.info(
                f"Generated summary for document {document_id} with {gen_result['input_tokens']} input tokens and {gen_result['output_tokens']} output tokens"
            )

            logger.info(f"Embedded {chunks_count} chunks for document {document.id}")

            document.status = DocumentStatus.indexed
            document.updated_at = datetime.utcnow()

            # 4. commit summary + chunks + status after both background tasks finish
            await db.commit()
            await db.refresh(document)
            await _invalidate_document_caches(
                user_id,
                document.project_id,
                document.id,
            )

            latency_ms = round((time.perf_counter() - t0) * 1000, 1)

            logger.info(
                f"Processed document {document_id} in {latency_ms}ms"
            )

            return {
                "document_id": document_id,
                "chunks_count": chunks_count,
                "summary": gen_result["summary"],
                "input_tokens": gen_result["input_tokens"],
                "output_tokens": gen_result["output_tokens"],
                "latency_ms": latency_ms,
            }

        except ValueError:
            await db.rollback()
            raise

        except Exception as e:
            await db.rollback()
            logger.error(
                f"System error {document_id}: {type(e).__name__} - {e}",
                exc_info=True
            )
            raise

        finally:
            # FIX 7: safe cleanup
            if extractor:
                try:
                    await asyncio.to_thread(extractor.cleanup)
                except Exception as e:
                    logger.warning(f"Cleanup failed {document_id}: {e}")
