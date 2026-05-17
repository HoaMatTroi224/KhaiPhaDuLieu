import io
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from inference.summarize import generate_summary, get_generator
from inference.pdf_extractor import extract_text_from_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_generator()
    yield

app = FastAPI(title="Summarize Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SummarizeTextRequest(BaseModel):
    text: str = Field(..., min_length=50, max_length=20000)

class SummarizeResponse(BaseModel):
    summary: str
    input_chars: int
    output_tokens: int
    latency_ms: float
    source: str   # "text" hoặc "pdf"


@app.get("/health")
def health():
    return {"status": "ok", "service": "summarize"}


# ─── Endpoint 1: Nhận raw text ───
@app.post("/api/v1/summarize", response_model=SummarizeResponse)
def summarize_text(request: SummarizeTextRequest):
    t0 = time.perf_counter()
    try:
        result = generate_summary(request.text)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(500, "Model inference failed")

    return SummarizeResponse(
        summary=result["summary"],
        input_chars=len(request.text),
        output_tokens=result["output_tokens"],
        latency_ms=round((time.perf_counter() - t0) * 1000, 1),
        source="text"
    )


# ─── Endpoint 2: Nhận file PDF ───
@app.post("/api/v1/summarize/pdf", response_model=SummarizeResponse)
async def summarize_pdf(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(422, "Chỉ chấp nhận file .pdf")
    if file.size and file.size > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(413, "File quá lớn, tối đa 20MB")

    t0 = time.perf_counter()

    # Đọc bytes
    pdf_bytes = await file.read()

    # Extract text từ PDF
    try:
        raw_text = extract_text_from_pdf(pdf_bytes)
    except Exception as e:
        logger.error(f"PDF extract error: {e}")
        raise HTTPException(422, f"Không đọc được PDF: {str(e)}")

    if len(raw_text) < 100:
        raise HTTPException(422, "PDF không có đủ nội dung text (có thể là PDF scan/ảnh)")

    logger.info(f"PDF extracted: {len(raw_text)} chars (Map-Reduce will handle chunking)")

    # Summarize (Map-Reduce tự xử lý text dài)
    try:
        result = generate_summary(raw_text)
    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        raise HTTPException(500, "Model inference failed")

    return SummarizeResponse(
        summary=result["summary"],
        input_chars=len(raw_text),
        output_tokens=result["output_tokens"],
        latency_ms=round((time.perf_counter() - t0) * 1000, 1),
        source="pdf"
    )