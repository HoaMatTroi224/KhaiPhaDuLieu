from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, UploadFile, File, Depends, HTTPException, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from retrieval.pgvector_store import CustomPGVectorStore
from generation.generator import AIContentGenerator
from langchain_community.document_loaders import PyPDFLoader
from data_access.supabase_client import SupabaseDB
import tempfile
import os
import PyPDF2
import logging
import httpx
from typing import List, Optional
from config.config import settings

FACTCHECK_SERVICE_URL = os.getenv("FACTCHECK_SERVICE_URL", "") 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_client: SupabaseDB = None
generator: AIContentGenerator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo các dependency nặng sau khi server đã sẵn sàng."""
    global db_client, generator
    logger.info("Đang khởi tạo Supabase client...")
    db_client = SupabaseDB()
    logger.info("Đang khởi tạo AI Generator...")
    generator = AIContentGenerator()
    # Tự động fix documents bị kẹt 'processing' do server crash lần trước
    _recover_stuck_documents()
    logger.info("Khởi tạo hoàn tất.")
    yield


def _recover_stuck_documents():
    """
    Khi server restart, kiểm tra documents bị kẹt 'processing'.
    Nếu đã có chunks trong PGVector → đánh dấu 'completed'.
    Nếu không có chunks → đánh dấu 'failed' để user biết cần upload lại.
    """
    import psycopg2
    from pgvector.psycopg2 import register_vector
    try:
        stuck = (
            db_client.supabase.table("documents")
            .select("id, file_name")
            .eq("status", "processing")
            .execute()
        )
        if not stuck.data:
            return
        conn = psycopg2.connect(settings.PG_CONN_STRING)
        register_vector(conn)
        for doc in stuck.data:
            doc_id = doc["id"]
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE document_id = %s",
                    (doc_id,)
                )
            count = cur.fetchone()[0]
            new_status = "completed" if count > 0 else "failed"
            db_client.update_document_status(doc_id, new_status)
            logger.info(f"[RECOVER] '{doc['file_name']}' → {new_status} ({count} chunks)")
        conn.close()
    except Exception as e:
        logger.warning(f"[RECOVER] Không thể tự recover documents: {e}")

app = FastAPI(title="QA Service", version="2.0.0", lifespan=lifespan)


def get_current_user(authorization: str = Header(...)) -> dict:
    """Xác thực JWT token từ header Authorization: Bearer <token>"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    return db_client.verify_jwt_token(token)


def get_mock_user() -> dict:
    """Mock user — chỉ dùng khi test cục bộ, xóa/comment khi deploy thật"""
    return {"sub": "00000000-0000-0000-0000-000000000001"}


def validate_pdf_file(file: UploadFile, content: bytes) -> None:
    """Kiểm tra file có đúng là PDF không bằng magic bytes và PyPDF2."""
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File '{file.filename}' quá lớn. Tối đa {settings.MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    # Kiểm tra PDF magic bytes: mọi file PDF đều bắt đầu bằng %PDF
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail=f"File '{file.filename}' không phải PDF")

    try:
        import io
        PyPDF2.PdfReader(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail=f"File '{file.filename}' bị hỏng hoặc không hợp lệ")


def process_documents_background(
    files_data: List[dict],  # [{"content": bytes, "filename": str}]
    project_id: str,
    user_id: str,
):
    """
    Xử lý nhiều tài liệu PDF trong background:
    1. Upload lên Supabase Storage
    2. Lưu metadata vào bảng documents
    3. Chunk + embed → lưu vào PGVector (document_chunks)
    4. Cập nhật status = 'completed'

    Không còn sinh tóm tắt tự động — tập trung hoàn toàn vào việc
    chuẩn bị vector cho Q&A đa tài liệu.
    """
    for file_data in files_data:
        file_bytes = file_data["content"]
        file_name = file_data["filename"]
        tmp_path = None
        document_id = None
        try:
            # 1. Upload lên Supabase Storage
            file_url = db_client.upload_file_to_storage(file_bytes, project_id, file_name)

            # 2. Lưu metadata — trích xuất text để lưu extracted_content
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            loader = PyPDFLoader(tmp_path)
            docs = loader.load()
            extracted_text = "\n".join([doc.page_content for doc in docs])
            # Xóa null bytes — PostgreSQL không chấp nhận ký tự \u0000
            extracted_text = extracted_text.replace("\x00", "")

            document_id = db_client.save_document_metadata(
                file_name=file_name,
                file_url=file_url,
                extracted_content=extracted_text,
                project_id=project_id,
                user_id=user_id,
            )
            if not document_id:
                raise Exception(f"Không thể lưu metadata cho file '{file_name}'")

            # 3. Chunk + embed → PGVector
            vector_store = CustomPGVectorStore(project_id)
            chunks_count = vector_store.add_documents(docs, document_id)

            # 4. Cập nhật trạng thái hoàn thành
            db_client.update_document_status(document_id, "completed")
            logger.info(f"[OK] '{file_name}' → {chunks_count} chunks | document_id={document_id}")

        except Exception as e:
            logger.error(f"[FAIL] '{file_name}': {e}")
            if document_id:
                db_client.update_document_status(document_id, "failed")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)


@app.get("/health")
async def health_check():
    """Health check endpoint cho Docker/orchestrator"""
    return {"status": "healthy", "service": "qa", "version": "2.0.0"}


@app.post("/process-document/")
async def process_documents(
    files: List[UploadFile] = File(...),
    project_id: str = Form(...),
    background_tasks: BackgroundTasks = None,
    # user: dict = Depends(get_current_user),
    user: dict = Depends(get_mock_user),
):
    """
    Upload nhiều file PDF cùng lúc cho một project.
    Tất cả file sẽ được chunk, embed và gán chung project_id.
    Xử lý bất đồng bộ trong background — response trả về ngay lập tức.
    """
    user_id = user.get("sub")

    # Đọc và validate toàn bộ file trước khi vào background
    files_data = []
    for file in files:
        content = await file.read()
        validate_pdf_file(file, content)
        files_data.append({"content": content, "filename": file.filename})

    background_tasks.add_task(
        process_documents_background,
        files_data,
        project_id,
        user_id,
    )

    return JSONResponse(
        status_code=202,
        content={
            "message": f"{len(files_data)} file đã được nhận, đang xử lý trong background",
            "project_id": project_id,
            "files": [f["filename"] for f in files_data],
        }
    )


@app.post("/ask/")
async def ask_question(
    project_id: str,
    thread_id: str,
    question: str,
    # user: dict = Depends(get_current_user),
    user: dict = Depends(get_mock_user),
):
    """
    Hỏi đáp dựa trên tài liệu (Cross-Document RAG).

    Pipeline:
    1. Embed câu hỏi → tìm Top-K chunks liên quan nhất trong toàn bộ project (PGVector)
    2. Đóng gói tất cả chunks vào prompt (stuffing) kèm nhãn nguồn [S1], [S2],...
    3. Gemini sinh câu trả lời, tự động trích dẫn nguồn trong văn bản
    4. Trả về answer + danh sách citations (file, đoạn, điểm tương đồng)

    Response:
      - answer: câu trả lời với nhãn [S1][S2] nhúng trong văn bản
      - citations: các nguồn được trích dẫn (file_name, chunk_index, document_id, relevance_score)
      - chunks_retrieved: tổng số chunks đưa vào context
    """
    user_id = user.get("sub")

    # 1. Lưu câu hỏi vào chat_history
    db_client.save_chat_message(project_id, thread_id, user_id, question, role="user")

    # 2. Cross-document RAG: tìm Top-K chunks trong toàn bộ project
    retriever = CustomPGVectorStore(project_id)
    chunks = retriever.similarity_search(question)  # dùng TOP_K_CHUNKS từ config

    if not chunks:
        answer_data = {
            "answer": "Tôi không tìm thấy tài liệu nào trong project này. Vui lòng upload tài liệu trước.",
            "citations": [],
            "chunks_retrieved": 0,
        }
        db_client.save_chat_message(project_id, thread_id, user_id, answer_data["answer"], role="assistant")
        return answer_data

    # 3. Lấy lịch sử chat để AI có ngữ cảnh hội thoại
    chat_history = db_client.get_chat_history(project_id, thread_id, limit=6)

    # 4. Sinh câu trả lời với trích dẫn nguồn (stuffing toàn bộ chunks vào prompt)
    result = await generator.answer_question(chunks, question, chat_history)

    # 5. Fact-check câu trả lời trước khi trả về (nếu service_factcheck đang chạy)
    factcheck_result = await _call_factcheck(result["answer"], chunks)

    # 6. Lưu câu trả lời vào chat_history
    db_client.save_chat_message(project_id, thread_id, user_id, result["answer"], role="assistant")

    response = {
        "answer": result["answer"],
        "citations": result["citations"],
        "chunks_retrieved": len(chunks),
        "fact_check": factcheck_result,
    }

    # Thêm cảnh báo nếu bị REFUTED
    if factcheck_result and factcheck_result.get("label") == "REFUTED":
        response["warning"] = (
            f"⚠️ Câu trả lời này có thể không chính xác so với tài liệu. "
            f"{factcheck_result.get('explanation', '')}"
        )
    elif factcheck_result and factcheck_result.get("label") == "NEI":
        response["disclaimer"] = "ℹ️ Thông tin chưa được kiểm chứng đầy đủ từ tài liệu."

    return response


async def _call_factcheck(answer: str, chunks: list) -> Optional[dict]:
    """
    Gọi service_factcheck để kiểm tra câu trả lời.
    Trả về None nếu service không sẵn sàng (graceful degradation).
    """
    if not FACTCHECK_SERVICE_URL:
        return None
    try:
        evidence = [c["text"] for c in chunks[:10]]  # top 10 chunks làm evidence
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{FACTCHECK_SERVICE_URL}/verify",
                json={"claim": answer, "evidence": evidence},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Factcheck service không khả dụng, bỏ qua: {e}")
        return None
