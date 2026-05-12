from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import Project, Document, Summary
from uuid import UUID
from datetime import datetime
import logging
from .extractor import FileExtractor
from .generator import SummaryGenerator
from ..config import settings
from ..database import AsyncSessionLocal
logger = logging.getLogger(__name__)



async def _get_document(
    db: AsyncSession, 
    document_id: UUID, 
    user_id: UUID
) -> Document:
    """Utility để lấy document thuộc về user, trả về 404 nếu không tìm thấy."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.project.has(Project.user_id == user_id)
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("Document not found")
    return doc


async def _extract_and_update_document(
    db: AsyncSession,
    document: Document,
    extractor: FileExtractor
) -> dict:
    """
    Chạy pipeline extraction và cập nhật metadata vào bảng documents.
    Trả về dict chứa extracted data.
    """
    try:
        # Chạy full extraction pipeline
        extracted = extractor.extract()
        
        # Cập nhật các trường metadata vào document
        document.title = extracted.get("title") or document.title
        document.authors = extracted.get("authors") or document.authors
        document.abstract = extracted.get("abstract") or document.abstract
        # document.keywords = extracted.get("keywords") or document.keywords
        document.extracted_content = extracted.get("content") or document.extracted_content
        document.is_processed = True
        document.updated_at = datetime.utcnow()
        
        logger.info(f"Extracted metadata for document {document.id}")
        return extracted
        
    except Exception as e:
        logger.error(f"Extraction failed for document {document.id}: {str(e)}")
        raise ValueError("Failed to extract and update document")


async def _generate_summary_for_document(
    db: AsyncSession,
    document: Document,
    generator: SummaryGenerator,
    user_id: UUID
) -> Summary:
    """Tạo summary từ nội dung document đã extract và lưu vào DB."""
    
    # Chuẩn bị context: ưu tiên extracted_content, fallback về abstract
    context = document.extracted_content
    if not context:
        raise ValueError("No content available for summary generation")
    
    # Gọi LLM để generate summary
    summary_text = await generator.generate_summary(context=context)
    
    # Tạo record Summary mới
    summary = Summary(
        user_id=user_id,
        document_id=document.id,
        summary_text=summary_text,
        created_at=datetime.utcnow()
    )
    
    db.add(summary)
    
    logger.info(f"Generated summary {summary.id} for document {document.id}")
    return summary

async def process_document(
    document_id: UUID,
    user_id: UUID
):
    async with AsyncSessionLocal() as db:
        try:
            document = await _get_document(
                db=db,
                document_id=document_id,
                user_id=user_id
            )
            
            extractor = FileExtractor(storage_path=document.file_path)
            generator = SummaryGenerator()
            await _extract_and_update_document(
                db=db,
                document=document,
                extractor=extractor
            )

            await _generate_summary_for_document(
                db=db,
                document=document,
                user_id=user_id,
                generator=generator
            )

            await db.commit()
            await db.refresh(document)

            logger.info(f"Successfully processed document {document_id}")
            return document
        except ValueError as e:
            # Lỗi business logic: not found, no content,...
            await db.rollback()
            logger.warning(f"Business error for {document_id}: {e}")
            raise
        except Exception as e:
            # Lỗi hệ thống: DB, network, AI API timeout,...
            await db.rollback()
            logger.error(f"System error processing {document_id}: {type(e).__name__}")
            raise
        finally:
            # Luôn dọn sạch tài nguyên dù thành công hay ko
            extractor.cleanup()
            
