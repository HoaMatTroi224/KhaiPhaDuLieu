import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, BigInteger,
    ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base

class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"

class DocumentType(str, enum.Enum):
    pdf = "pdf"
    txt = "txt"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    status = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    projects = relationship("Project", back_populates="owner")
    documents = relationship("Document", back_populates="owner")
    summaries = relationship("Summary", back_populates="owner")
    chat_history = relationship("ChatHistory", back_populates="owner")
    notes = relationship("Note", back_populates="owner")

class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    # name = Column(String)
    domain = Column(String)
    description = Column(Text)
    collection_name = Column(String, unique=True, nullable=False)
    # collection_name = Column(String, unique=True)
    is_draft = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project")
    chat_history = relationship("ChatHistory", back_populates="project")

class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(Text)
    file_name = Column(String)
    file_path = Column(Text)
    file_type = Column(Enum(DocumentType, name="document_type"))
    file_size = Column(BigInteger)
    upload_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    status = Column(Enum(DocumentStatus, name="document_status"), default=DocumentStatus.uploaded)
    # is_private = Column(Boolean, default=True)
    title = Column(String)
    authors = Column(String)
    abstract = Column(String)
    # keywords = Column(String)
    publication_date = Column(DateTime)
    extracted_content = Column(Text)

    owner = relationship("User", back_populates="documents")
    project = relationship("Project", back_populates="documents")
    summaries = relationship("Summary", back_populates="document")
    notes = relationship("Note", back_populates="document")

class Summary(Base):
    __tablename__ = "summaries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    summary_text = Column(Text, nullable=False)
    summary_type = Column(String)
    original_text = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    owner = relationship("User", back_populates="summaries")
    document = relationship("Document", back_populates="summaries")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    thread_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' hoặc 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    owner = relationship("User", back_populates="chat_history")
    project = relationship("Project", back_populates="chat_history")

class Note(Base):
    __tablename__ = "notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    title = Column(String)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    owner = relationship("User", back_populates="notes")
    document = relationship("Document", back_populates="notes")