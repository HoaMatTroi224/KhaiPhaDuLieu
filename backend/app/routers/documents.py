import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import List
from ..database import get_db, AsyncSessionLocal
from ..models import Document, DocumentStatus, Project
from ..schemas import DocumentListCreate, DocumentListResponse, DocumentResponse
from ..dependencies import get_current_user_id
from ..services_summary.file_processor import process_document
from ..config import settings
from ..cache import delete_keys, get_json, set_json

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = logging.getLogger(__name__)


def _project_documents_cache_key(user_id: UUID, project_id: UUID) -> str:
    return f"user:{user_id}:project:{project_id}:documents"


def _document_summaries_cache_key(user_id: UUID, document_id: UUID) -> str:
    return f"user:{user_id}:document:{document_id}:summaries"


async def _invalidate_document_caches(
    user_id: UUID,
    project_id: UUID,
    document_id: UUID | None = None,
) -> None:
    keys = [_project_documents_cache_key(user_id, project_id)]
    if document_id is not None:
        keys.append(_document_summaries_cache_key(user_id, document_id))
    await delete_keys(*keys)


def _document_list_payload(document: Document) -> dict:
    return DocumentListResponse.model_validate(document).model_dump(mode="json")


async def _mark_document_status(document_id: UUID, status_value: DocumentStatus) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            return

        document.status = status_value
        await db.commit()
        await _invalidate_document_caches(
            document.user_id,
            document.project_id,
            document.id,
        )


async def process_document_wrapper(document_id: UUID, user_id: UUID) -> None:
    try:
        await _mark_document_status(document_id, DocumentStatus.processing)
        await process_document(document_id, user_id)
    except Exception:
        logger.exception(
            "Background processing failed for document_id=%s user_id=%s",
            document_id,
            user_id,
        )
        try:
            await _mark_document_status(document_id, DocumentStatus.failed)
        except Exception:
            logger.exception("Could not mark document_id=%s as failed", document_id)

@router.get("/", response_model=List[DocumentListResponse])
async def list_documents(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    cache_key = _project_documents_cache_key(user_id, project_id)
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Document)
        .where(
            Document.user_id == user_id,
            Document.project_id == project_id
        )
    )

    documents = result.scalars().all()
    payload = [_document_list_payload(document) for document in documents]
    has_pending = any(
        document.status in {DocumentStatus.uploaded, DocumentStatus.processing}
        or not (document.title or "").strip()
        for document in documents
    )
    ttl = (
        settings.CACHE_DOCUMENTS_PENDING_TTL_SECONDS
        if has_pending
        else settings.CACHE_DOCUMENTS_READY_TTL_SECONDS
    )
    await set_json(cache_key, payload, ttl)
    return payload


@router.post("/", response_model=List[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def add_documents(
    project_id: UUID,
    payload: DocumentListCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.is_draft == False
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_count = await db.scalar(
        select(func.count(Document.id)).where(
            Document.user_id == user_id,
            Document.project_id == project_id
        )
    )
    if (existing_count or 0) + len(payload.documents) > 10:
        raise HTTPException(
            status_code=400,
            detail="A project can contain a maximum of 10 documents"
        )

    documents = []
    for doc_meta in payload.documents:
        document = Document(
            user_id=user_id,
            project_id=project_id,
            status=DocumentStatus.uploaded,
            **doc_meta.model_dump()
        )
        documents.append(document)

    db.add_all(documents)
    await db.commit()

    for document in documents:
        await db.refresh(document)
        background_tasks.add_task(process_document_wrapper, document.id, user_id)

    await _invalidate_document_caches(user_id, project_id)

    return documents

