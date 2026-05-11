from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
from ..database import get_db
from ..models import Document, Project
# from ..schemas import DocumentCreate, DocumentResponse
# from ..schemas import DocumentListCreate, DocumentResponse
from ..schemas import DocumentResponse
from ..dependencies import get_current_user_id

router = APIRouter(prefix="/documents", tags=["Documents"])

# @router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
# async def create_document(
#     payload: DocumentCreate,
#     user_id: UUID = Depends(get_current_user_id),
#     db: AsyncSession = Depends(get_db)
# ):
#     result = await db.execute(
#         select(Project)
#         .where(
#             Project.user_id == user_id,
#             Project.id == payload.project_id
#         )
#     )

#     project = result.scalar_one_or_none()
#     if not project:
#         raise HTTPException(403, "Project not found")
    
#     document = Document(
#         user_id=user_id,
#         **payload.model_dump()
#     )

#     db.add(document)
#     await db.commit()
#     await db.refresh(document)
#     return document

# @router.post("/", response_model=List[DocumentResponse], status_code=status.HTTP_201_CREATED)
# async def create_documents(
#     payload: DocumentListCreate,
#     user_id: UUID = Depends(get_current_user_id),
#     db: AsyncSession = Depends(get_db)
# ):
#     result = await db.execute(
#         select(Project).where(
#             Project.user_id == user_id,
#             Project.id == payload.project_id
#         )
#     )

#     project = result.scalar_one_or_none()
#     if not project:
#         raise HTTPException(status_code=403, detail="Project not found")

#     documents = []
#     for doc_data in payload.documents:
#         document = Document(
#             user_id=user_id,
#             project_id=payload.project_id,
#             **doc_data.model_dump()
#         )

#         documents.append(document)
    
#     db.add_all(documents)
#     await db.commit()
#     for doc in documents:
#         await db.refresh(doc)

#     return documents
    

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

