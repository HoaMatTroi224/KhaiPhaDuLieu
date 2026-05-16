import asyncio
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.documents import Document as LangchainDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import settings
from ..models import DocumentChunk, Document as DbDocument
from .embedder import get_embedding_model


class PGVectorStore:
    def __init__(self, db: AsyncSession, project_id: str):
        self.db = db
        self.project_id = project_id
        self.embeddings = get_embedding_model()

    def _split_documents(
        self,
        documents: List[LangchainDocument],
    ) -> List[LangchainDocument]:
        """
        Chunk tài liệu bằng cùng cấu hình đang dùng cho pgvector.
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
            length_function=len,
        )

        chunks = splitter.split_documents(documents)

        chunks = [
            c for c in chunks
            if len(c.page_content.strip()) > 20
        ]

        return chunks

    async def build_chunk_objects(
        self,
        documents: List[LangchainDocument],
        document_id: str,
    ) -> List[DocumentChunk]:
        """
        Chunk + embedding nhưng chưa ghi DB, để caller có thể chạy song song
        với các tác vụ khác và commit trong một transaction riêng.
        """
        chunks = self._split_documents(documents)

        if not chunks:
            return []

        texts = [chunk.page_content for chunk in chunks]

        embeddings_list = await asyncio.to_thread(
            self.embeddings.embed_documents,
            texts,
        )

        chunk_objects = []

        for idx, (chunk, embedding) in enumerate(
            zip(chunks, embeddings_list)
        ):
            chunk_objects.append(
                DocumentChunk(
                    document_id=document_id,
                    project_id=self.project_id,
                    chunk_text=chunk.page_content,
                    chunk_index=idx,
                    embedding=embedding,
                )
            )

        return chunk_objects

    async def add_documents(
        self,
        documents: List[LangchainDocument],
        document_id: str,
    ) -> int:
        """
        Chunk + embedding + lưu vào pgvector bằng SQLAlchemy async.
        """
        chunk_objects = await self.build_chunk_objects(
            documents=documents,
            document_id=document_id,
        )

        if not chunk_objects:
            return 0

        self.db.add_all(chunk_objects)

        await self.db.commit()

        return len(chunk_objects)

        

    async def similarity_search(
        self,
        query: str,
        k: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search bằng pgvector + SQLAlchemy async.
        """

        k = k or settings.TOP_K_CHUNKS

        query_embedding = self.embeddings.embed_query(
            query
        )

        score = (
            1 - DocumentChunk.embedding.cosine_distance(query_embedding)
        ).label("score")

        base_stmt = (
            select(
                DocumentChunk.chunk_text,
                DocumentChunk.document_id,
                DocumentChunk.chunk_index,
                DbDocument.file_name,
                score,
            )
            .join(
                DbDocument,
                DocumentChunk.document_id == DbDocument.id,
            )
            .where(
                DocumentChunk.project_id == self.project_id
            )
            .order_by(
                DocumentChunk.embedding.cosine_distance(
                    query_embedding
                )
            )
            .limit(k)
        )

        stmt = base_stmt.where(
            score >= settings.MIN_SIMILARITY_SCORE
        )

        result = await self.db.execute(stmt)

        rows = result.all()

        if not rows:
            fallback_result = await self.db.execute(base_stmt)
            rows = fallback_result.all()

        return [
            {
                "text": row.chunk_text,
                "document_id": str(row.document_id),
                "chunk_index": row.chunk_index,
                "file_name": row.file_name,
                "score": float(row.score),
            }
            for row in rows
        ]
