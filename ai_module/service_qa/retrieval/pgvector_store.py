import re
import unicodedata
import psycopg2
from pgvector.psycopg2 import register_vector
from langchain_core.documents import Document
from typing import List, Dict, Any
from config.config import settings
from embedding.embedder import get_embedding_model
from langchain_text_splitters import RecursiveCharacterTextSplitter


def clean_vietnamese_text(text: str) -> str:
    """
    Làm sạch văn bản tiếng Việt trích xuất từ PDF.
    Theo hàm clean_vietnamese_text trong tài liệu RAG System:
    - Chuẩn hóa Unicode về dạng NFC
    - Loại bỏ ký tự điều khiển (null bytes, control chars)
    - Gộp khoảng trắng thừa và dòng trống
    """
    # Chuẩn hóa Unicode NFC cho tiếng Việt
    text = unicodedata.normalize("NFC", text)
    # Loại bỏ ký tự null và control characters (giữ lại \n \t)
    text = "".join(
        char for char in text
        if not unicodedata.category(char).startswith("C") or char in "\n\t"
    )
    # Gộp khoảng trắng thừa
    text = re.sub(r"\s+", " ", text)
    # Gộp nhiều dòng trống liên tiếp thành 1
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.strip()


class CustomPGVectorStore:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.embeddings = get_embedding_model()

    def _get_connection(self):
        if not settings.PG_CONN_STRING:
            raise ValueError("PG_CONN_STRING chưa được cấu hình trong file .env")
        conn = psycopg2.connect(settings.PG_CONN_STRING)
        register_vector(conn)
        return conn

    def add_documents(self, documents: List[Document], document_id: str) -> int:
        """
        Làm sạch text, cắt chunk và lưu vào PGVector.
        Chunk size 400/120 tối ưu cho tiếng Việt theo tài liệu RAG.
        """
        # Làm sạch text từng trang trước khi chunk
        for doc in documents:
            doc.page_content = clean_vietnamese_text(doc.page_content)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
            length_function=len,
        )
        chunks = splitter.split_documents(documents)

        # Bỏ các chunk quá ngắn (< 20 ký tự) — không có giá trị ngữ nghĩa
        chunks = [c for c in chunks if len(c.page_content.strip()) > 20]

        if not chunks:
            return 0

        # Batch embedding: 1 request duy nhất
        texts = [chunk.page_content for chunk in chunks]
        embeddings_list = self.embeddings.embed_documents(texts)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings_list)):
                    cur.execute("""
                        INSERT INTO document_chunks (document_id, project_id, chunk_text, chunk_index, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (document_id, self.project_id, chunk.page_content, idx, embedding))
            conn.commit()

        return len(chunks)

    def similarity_search(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """
        Tìm kiếm ngữ nghĩa Top-K chunks, trả về kèm metadata nguồn để trích dẫn.

        intfloat/multilingual-e5-base yêu cầu prefix "query: " trước câu hỏi
        để đạt chất lượng retrieval tốt nhất.
        """
        k = k or settings.TOP_K_CHUNKS
        prefixed_query = f"query: {query}"
        query_embedding = self.embeddings.embed_query(prefixed_query)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # HAVING score >= threshold lọc bỏ chunks không liên quan
                # 0.45 là ngưỡng thực nghiệm cho E5-multilingual (cosine similarity)
                cur.execute("""
                    SELECT dc.chunk_text,
                           dc.document_id,
                           dc.chunk_index,
                           d.file_name,
                           (1 - (dc.embedding <=> %s::vector)) AS score
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    WHERE dc.project_id = %s
                      AND (1 - (dc.embedding <=> %s::vector)) >= %s
                    ORDER BY dc.embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, self.project_id, query_embedding,
                      settings.MIN_SIMILARITY_SCORE, query_embedding, k))

                rows = cur.fetchall()

        return [
            {
                "text": row[0],
                "document_id": str(row[1]),
                "chunk_index": row[2],
                "file_name": row[3],
                "score": float(row[4]),
            }
            for row in rows
        ]
