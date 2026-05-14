from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import settings
from ..models import DocumentChunk, Document
from .embedder import get_embedding_model


class PGVectorStore:
    def __init__(self, db: AsyncSession, project_id: str):
        self.db = db
        self.project_id = project_id
        self.embeddings = get_embedding_model()

    async def add_documents(
        self,
        documents: List[Document],
        document_id: str,
    ) -> int:
        """
        Chunk + embedding + lưu vào pgvector bằng SQLAlchemy async.
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

        if not chunks:
            return 0

        texts = [chunk.page_content for chunk in chunks]

        embeddings_list = self.embeddings.embed_documents(texts)

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

        prefixed_query = f"query: {query}"

        query_embedding = self.embeddings.embed_query(
            prefixed_query
        )

        score = (
            1 - DocumentChunk.embedding.cosine_distance(query_embedding)
        ).label("score")

        stmt = (
            select(
                DocumentChunk.chunk_text,
                DocumentChunk.document_id,
                DocumentChunk.chunk_index,
                Document.file_name,
                score,
            )
            .join(
                Document,
                DocumentChunk.document_id == Document.id,
            )
            .where(
                DocumentChunk.project_id == self.project_id
            )
            .where(
                score >= settings.MIN_SIMILARITY_SCORE
            )
            .order_by(
                DocumentChunk.embedding.cosine_distance(
                    query_embedding
                )
            )
            .limit(k)
        )

        result = await self.db.execute(stmt)

        rows = result.all()

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