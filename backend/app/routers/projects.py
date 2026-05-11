from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..dependencies import get_current_user_id
from ..database import get_db
from ..models import Project, Document, DocumentType, DocumentStatus
from ..schemas import ProjectInitialize, ProjectUpdate, ProjectResponse, ProjectFinalize
from typing import List
from uuid import UUID, uuid4
from datetime import datetime

router = APIRouter(prefix="/projects", tags=["projects"])

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
    await db.refresh(project)
    return project

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

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
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
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
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
    
    await db.delete(project)
    await db.commit()

