from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Optional, Literal, List
from datetime import date, datetime
from uuid import UUID
from .models import DocumentStatus, DocumentType

# ---------- Auth ----------
class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    status: bool
    last_login: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: Optional[str]

# ---------- Project ----------
class ProjectInitialize(BaseModel):
    name: str
    domain: Optional[str] = None
    # description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None

class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    domain: Optional[str]
    description: Optional[str]
    collection_name: str
    created_at: datetime
    updated_at: datetime
    is_draft: bool

    model_config = ConfigDict(from_attributes=True)

# Payload sent from frontend to backend when click Generate Summary:
class DocumentMeta(BaseModel):
    file_name: str
    file_path: str
    file_url: str
    file_type: DocumentType
    file_size: int


class ProjectFinalize(BaseModel):
    name: str  # project title to finalize
    domain: Optional[str] = None  # project tag to finalize

    documents: List[DocumentMeta]  # documents metadata to create records

# ---------- Document ----------
# class DocumentCreate(BaseModel):
#     project_id: UUID
#     file_name: str
#     file_path: str
#     file_url: str
#     file_type: DocumentType
#     file_size: int

# class DocumentMetaData(BaseModel):
#     file_name: str
#     file_path: str
#     file_url: str
#     file_type: DocumentType
#     file_size: int

# class DocumentListCreate(BaseModel):
#     project_id: UUID
#     documents: List[DocumentMetaData]

class DocumentResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: UUID
    file_url: Optional[str]
    file_path: Optional[str]
    file_name: Optional[str]
    file_type: Optional[DocumentType]
    file_size: Optional[int]
    upload_time: datetime
    status: DocumentStatus
    # is_private: bool
    title: Optional[str]
    authors: Optional[str]
    abstract: Optional[str]
    # keywords: Optional[str]
    publication_date: Optional[date]
    extracted_content: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class DocumentUpdate(BaseModel):
    title: Optional[str]
    authors: Optional[str]
    abstract: Optional[str]
    # keywords: Optional[str]
    publication_date: Optional[date]
    extracted_content: Optional[str]


# ---------- Summary ----------
class SummaryCreate(BaseModel):
    document_id: Optional[UUID] = None
    summary_text: str
    summary_type: Optional[str] = None
    original_text: Optional[str] = None

class SummaryGenerate(BaseModel):
    document_ids: List[UUID] = Field(..., min_length=1, max_length=10)

class SummaryResponse(BaseModel):
    id: UUID
    user_id: UUID
    document_id: Optional[UUID]
    summary_text: str
    summary_type: Optional[str]
    original_text: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ---------- Chat ----------

class ChatMessageCreate(BaseModel):
    project_id: UUID
    thread_id: UUID
    content: str
    role: str = "user"

class ChatMessageResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: UUID
    thread_id: UUID
    role: str
    content: str
    citations: Optional[List[dict[str, Any]]] = None
    chunks_retrieved: Optional[int] = None
    fact_check: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ---------- Note ----------
class NoteCreate(BaseModel):
    document_id: Optional[UUID] = None
    title: Optional[str] = None
    content: str

class NoteResponse(BaseModel):
    id: UUID
    user_id: UUID
    document_id: Optional[UUID]
    title: Optional[str]
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


