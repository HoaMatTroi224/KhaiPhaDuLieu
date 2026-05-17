import json
import logging
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis

from .config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def init_cache() -> None:
    global _redis
    if not settings.REDIS_URL:
        logger.info("Redis cache disabled: REDIS_URL is empty")
        return

    try:
        client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        await client.ping()
        _redis = client
        logger.info("Redis cache connected")
    except Exception:
        _redis = None
        logger.warning("Redis cache unavailable; continuing without cache", exc_info=True)


async def close_cache() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def is_cache_enabled() -> bool:
    return _redis is not None


async def get_json(key: str) -> Any | None:
    if _redis is None:
        return None

    try:
        cached = await _redis.get(key)
        if cached is None:
            return None
        return json.loads(cached)
    except Exception:
        logger.warning("Redis GET failed for key=%s", key, exc_info=True)
        return None


async def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    if _redis is None:
        return

    try:
        encoded = json.dumps(
            jsonable_encoder(value),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        await _redis.set(key, encoded, ex=ttl_seconds)
    except Exception:
        logger.warning("Redis SET failed for key=%s", key, exc_info=True)


async def delete_keys(*keys: str) -> None:
    if _redis is None or not keys:
        return

    try:
        await _redis.delete(*keys)
    except Exception:
        logger.warning("Redis DEL failed for keys=%s", keys, exc_info=True)
