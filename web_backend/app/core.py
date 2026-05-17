from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
from .services_chat.retrieval import recover_stuck_documents
from .services_chat.chat_generator import ChatGenerator
from .database import AsyncSessionLocal
from .cache import close_cache, init_cache

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_cache()

    logger.info("Loading AI model...")
    app.state.chat_generator = ChatGenerator()

    logger.info("Recovering stuck documents...")
    async with AsyncSessionLocal() as db:
        await recover_stuck_documents(db=db)

    yield

    logger.info("Shutting down...")
    await close_cache()
