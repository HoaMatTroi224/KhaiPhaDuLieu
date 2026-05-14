import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..dependencies import get_current_user_id
from ..database import get_db, AsyncSessionLocal
from ..models import Project, Document, DocumentStatus
from ..schemas import ProjectResponse, ProjectFinalize
from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from ..services_summary.file_processor import process_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


async def process_document_wrapper(document_id: UUID, user_id: UUID) -> None:
    """
    Starlette chạy background tasks tuần tự; nếu một task ném exception thì các task sau
    không được gọi. Wrapper này bắt lỗi để mỗi PDF trong finalize vẫn được xử lý độc lập.
    """
    try:
        await process_document(document_id, user_id)
    except Exception:
        logger.exception(
            "Background processing failed for document_id=%s user_id=%s",
            document_id,
            user_id,
        )
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(status=DocumentStatus.failed)
                )
                await db.commit()
        except Exception:
            logger.exception(
                "Could not mark document_id=%s as failed",
                document_id,
            )

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.updated_at.desc())
    )

    projects = result.scalars().all()
    return projects

@router.get("/recent", response_model=List[ProjectResponse])
async def get_recent_projects(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.updated_at.desc())
        .limit(5)
    )

    projects = result.scalars().all()
    return projects

@router.post("/initialize", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def initialize_project(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    project = Project(
        user_id=user_id,
        name="Untitled Project",
        collection_name=f"{user_id}_{uuid4().hex}",
        is_draft=True
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.put("/{project_id}/finalize")
async def finalize_project(
    project_id: UUID,
    payload: ProjectFinalize,  
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.is_draft == True 
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    project.name = payload.name
    project.domain = payload.domain
    project.is_draft = False  
    project.updated_at = datetime.utcnow()

    documents = []
    for doc_meta in payload.documents:
        document = Document(
            user_id=user_id,
            project_id=project_id,
            **doc_meta.model_dump()
        )

        documents.append(document)

    db.add_all(documents)
    await db.commit()
    for doc in documents:
        await db.refresh(doc)

    for doc in documents:
        background_tasks.add_task(
            process_document_wrapper,
            doc.id,
            user_id,
        )
        
    await db.refresh(project)
    
    return {
        "project": project,
        "documents": documents
    }

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project)
        .where(
            Project.user_id == user_id,
            Project.id == project_id
        )
    )

    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

