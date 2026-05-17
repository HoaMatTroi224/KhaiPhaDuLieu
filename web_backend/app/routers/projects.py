import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..dependencies import get_current_user_id
from ..database import get_db, AsyncSessionLocal
from ..models import Project, Document, DocumentStatus
from ..schemas import ProjectResponse, ProjectFinalize
from ..config import settings
from ..cache import delete_keys, get_json, set_json
from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from ..services_summary.file_processor import process_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


def _projects_cache_key(user_id: UUID) -> str:
    return f"user:{user_id}:projects"


def _recent_projects_cache_key(user_id: UUID) -> str:
    return f"user:{user_id}:projects:recent"


def _project_cache_key(user_id: UUID, project_id: UUID) -> str:
    return f"user:{user_id}:project:{project_id}"


def _project_documents_cache_key(user_id: UUID, project_id: UUID) -> str:
    return f"user:{user_id}:project:{project_id}:documents"


def _document_summaries_cache_key(user_id: UUID, document_id: UUID) -> str:
    return f"user:{user_id}:document:{document_id}:summaries"


async def _invalidate_project_caches(user_id: UUID, project_id: UUID | None = None) -> None:
    keys = [
        _projects_cache_key(user_id),
        _recent_projects_cache_key(user_id),
    ]
    if project_id is not None:
        keys.extend([
            _project_cache_key(user_id, project_id),
            _project_documents_cache_key(user_id, project_id),
        ])
    await delete_keys(*keys)


def _project_payload(project: Project) -> dict:
    return ProjectResponse.model_validate(project).model_dump(mode="json")


async def _mark_document_status(document_id: UUID, status_value: DocumentStatus) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            return

        document.status = status_value
        await db.commit()
        await _invalidate_project_caches(document.user_id, document.project_id)
        await delete_keys(_document_summaries_cache_key(document.user_id, document.id))


async def process_document_wrapper(document_id: UUID, user_id: UUID) -> None:
    """
    Starlette chạy background tasks tuần tự; nếu một task ném exception thì các task sau
    không được gọi. Wrapper này bắt lỗi để mỗi PDF trong finalize vẫn được xử lý độc lập.
    """
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
            logger.exception(
                "Could not mark document_id=%s as failed",
                document_id,
            )

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    cache_key = _projects_cache_key(user_id)
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.updated_at.desc())
    )

    projects = result.scalars().all()
    payload = [_project_payload(project) for project in projects]
    await set_json(cache_key, payload, settings.CACHE_PROJECTS_TTL_SECONDS)
    return payload

@router.get("/recent", response_model=List[ProjectResponse])
async def get_recent_projects(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    cache_key = _recent_projects_cache_key(user_id)
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.updated_at.desc())
        .limit(5)
    )

    projects = result.scalars().all()
    payload = [_project_payload(project) for project in projects]
    await set_json(cache_key, payload, settings.CACHE_PROJECTS_TTL_SECONDS)
    return payload

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
    await _invalidate_project_caches(user_id)
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
        doc_data = doc_meta.model_dump()
        doc_data["status"] = DocumentStatus.uploaded
        document = Document(
            user_id=user_id,
            project_id=project_id,
            **doc_data
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
    await _invalidate_project_caches(user_id, project_id)
    
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
    cache_key = _project_cache_key(user_id, project_id)
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

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
    payload = _project_payload(project)
    await set_json(cache_key, payload, settings.CACHE_PROJECT_DETAIL_TTL_SECONDS)
    return payload

