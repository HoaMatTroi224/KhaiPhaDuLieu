from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
from ..database import get_db
from ..models import Document, Project
from ..schemas import DocumentResponse
from ..dependencies import get_current_user_id

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document)
        .where(
            Document.user_id == user_id,
            Document.project_id == project_id
        )
    )
    
    return result.scalars().all()

