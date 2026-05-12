# routers/summaries.py (tiếp theo)
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..dependencies import get_current_user_id
from ..database import get_db
from ..models import Project, Document, Summary
from ..schemas import SummaryCreate, SummaryResponse, SummaryGenerate
from typing import List, Optional
from uuid import UUID, uuid4
# from datetime import datetime
import logging
# from ..services.extractor import FileExtractor
# from ..services.generator import SummaryGenerator
# from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/summaries", tags=["summaries"])


# =============================================================================
# ENDPOINTS
# =============================================================================

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
    query = select(Summary).join(Document).where(
        Document.project.has(Project.user_id == user_id)
    )
    
    if document_id:
        query = query.where(Summary.document_id == document_id)
    
    result = await db.execute(query)
    summaries = result.scalars().all()
    
    return summaries


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


# @router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
# async def generate_summary(
#     background_tasks: BackgroundTasks,
#     request: SummaryGenerate,
#     user_id: UUID = Depends(get_current_user_id),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Trigger summary generation for one or multiple documents.
    
#     Flow:
#     1. Extract metadata & content from PDF via FileExtractor
#     2. Update documents table with extracted fields
#     3. Generate AI summary via SummaryGenerator
#     4. Store results in summaries table
    
#     Returns 202 Accepted - processing happens in background.
#     """
    
#     # Validate documents belong to user
#     doc_ids = request.document_ids
#     result = await db.execute(
#         select(Document).where(
#             Document.id.in_(doc_ids),
#             Document.project.has(Project.user_id == user_id)
#         )
#     )
#     documents = result.scalars().all()
    
#     if len(documents) != len(doc_ids):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="One or more documents not found or access denied"
#         )
    
#     # Khởi tạo services
#     extractor = FileExtractor(storage_path="")
#     generator = SummaryGenerator()
    
#     async def process_document(doc: Document):
#         """Inner function để xử lý từng document trong background."""
#         try:
#             # Cập nhật storage_path cho extractor
#             extractor.storage_path = doc.file_path
            
#             # Step 1: Extract & update document metadata
#             await _extract_and_update_document(db, doc, extractor)
            
#             # Step 2: Generate summary
#             await _generate_summary_for_document(db, doc, generator, user_id)
            
#         except Exception as e:
#             logger.error(f"Background processing failed for doc {doc.id}: {str(e)}")
#             # Có thể update status field của document để frontend biết lỗi
#             doc.status = "failed"
#             await db.commit()
    
#     for doc in documents:
#         background_tasks.add_task(process_document, doc)
    
#     return {"document_ids": [str(d.id) for d in documents]}


# async def _get_document(
#     db: AsyncSession, 
#     document_id: UUID, 
#     user_id: UUID
# ) -> Document:
#     """Utility để lấy document thuộc về user, trả về 404 nếu không tìm thấy."""
#     result = await db.execute(
#         select(Document).where(
#             Document.id == document_id,
#             Document.project.has(Project.user_id == user_id)
#         )
#     )
#     doc = result.scalar_one_or_none()
#     if not doc:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Document not found or access denied"
#         )
#     return doc


# async def _extract_and_update_document(
#     db: AsyncSession,
#     document: Document,
#     extractor: FileExtractor
# ) -> dict:
#     """
#     Chạy pipeline extraction và cập nhật metadata vào bảng documents.
#     Trả về dict chứa extracted data.
#     """
#     try:
#         # Chạy full extraction pipeline
#         extracted = extractor.extract()
        
#         # Cập nhật các trường metadata vào document
#         document.title = extracted.get("title") or document.title
#         document.authors = extracted.get("authors") or document.authors
#         document.abstract = extracted.get("abstract") or document.abstract
#         # document.keywords = extracted.get("keywords") or document.keywords
#         document.extracted_content = extracted.get("content") or document.extracted_content
#         document.is_processed = True
#         document.updated_at = datetime.utcnow()
        
#         await db.commit()
#         await db.refresh(document)
        
#         logger.info(f"Extracted metadata for document {document.id}")
#         return extracted
        
#     except Exception as e:
#         await db.rollback()
#         logger.error(f"Extraction failed for document {document.id}: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to extract document: {str(e)}"
#         )
#     finally:
#         extractor.cleanup()


# async def _generate_summary_for_document(
#     db: AsyncSession,
#     document: Document,
#     generator: SummaryGenerator,
#     user_id: UUID
# ) -> Summary:
#     """Tạo summary từ nội dung document đã extract và lưu vào DB."""
    
#     # Chuẩn bị context: ưu tiên extracted_content, fallback về abstract
#     context = document.extracted_content
#     if not context:
#         raise ValueError("No content available for summary generation")
    
#     # Gọi LLM để generate summary
#     summary_text = await generator.generate_summary(context=context)
    
#     # Tạo record Summary mới
#     summary = Summary(
#         id=uuid4(),
#         user_id=user_id,
#         document_id=document.id,
#         summary_text=summary_text,
#         created_at=datetime.utcnow()
#     )
    
#     db.add(summary)
#     await db.commit()
#     await db.refresh(summary)
    
#     logger.info(f"Generated summary {summary.id} for document {document.id}")
#     return summary


