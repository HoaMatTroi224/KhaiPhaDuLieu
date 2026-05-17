# routers/summaries.py (tiếp theo)
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..dependencies import get_current_user_id
from ..database import get_db
from ..models import Project, Document, Summary
from ..schemas import SummaryResponse
from ..config import settings
from ..cache import get_json, set_json
from typing import List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/summaries", tags=["summaries"])


def _document_summaries_cache_key(user_id: UUID, document_id: UUID) -> str:
    return f"user:{user_id}:document:{document_id}:summaries"


def _summary_payload(summary: Summary) -> dict:
    return SummaryResponse.model_validate(summary).model_dump(mode="json")



@router.get("", response_model=List[SummaryResponse])
async def list_summaries(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all summaries for the current user.
    Có thể filter theo document_id.
    """
    cache_key = _document_summaries_cache_key(user_id, document_id)
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    query = select(Summary).join(Document).where(
        Document.project.has(Project.user_id == user_id)
    )
    
    if document_id:
        query = query.where(Summary.document_id == document_id)
    
    result = await db.execute(query)
    summaries = result.scalars().all()
    payload = [_summary_payload(summary) for summary in summaries]
    ttl = (
        settings.CACHE_SUMMARIES_TTL_SECONDS
        if payload
        else settings.CACHE_SUMMARIES_EMPTY_TTL_SECONDS
    )
    await set_json(cache_key, payload, ttl)
    
    return payload


@router.get("/{summary_id}", response_model=SummaryResponse)
async def get_summary(
    summary_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific summary by ID."""
    result = await db.execute(
        select(Summary).join(Document).where(
            Summary.id == summary_id,
            Document.project.has(Project.user_id == user_id)
        )
    )
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found or access denied"
        )
    
    return summary
