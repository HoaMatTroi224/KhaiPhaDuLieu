import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from serving.schemas import VerifyRequest, VerifyResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Warming up NLI model...")
    from models.model_loader import get_nli_model
    get_nli_model()
    logger.info("Model ready!")
    yield


app = FastAPI(title="Fact-Check NLI Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    from models.model_loader import get_nli_model
    try:
        get_nli_model()
        return {"status": "ok", "model_loaded": True}
    except Exception:
        return {"status": "error", "model_loaded": False}


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest):
    if not req.claim.strip():
        raise HTTPException(status_code=400, detail="claim không được để trống")
    if not req.evidence:
        raise HTTPException(status_code=400, detail="evidence không được để trống")
    try:
        from inference.nli import verify as _verify
        return _verify(req.claim, req.evidence)
    except Exception as e:
        logger.error("Inference error: %s", e)
        raise HTTPException(status_code=500, detail="Lỗi inference")
