from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings


def _retryable_http_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False


class SummaryGenerator:
    """Gọi API ViT5 fine-tuned (Cloud Run) để tóm tắt bài báo."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or settings.VIT5_SUMMARIZE_API_URL).rstrip("/")

    def _summarize_url(self) -> str:
        return f"{self._base_url}/api/v1/summarize"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception(_retryable_http_error),
        reraise=True,
    )
    async def generate_summary(self, text: str) -> dict[str, Any]:
        """
        Returns:
            dict với keys: summary, input_tokens, output_tokens (theo SummarizeResponse API).
        """
        if not text or not text.strip():
            raise ValueError("Input text không được để trống")

        payload = {"text": text.strip()}
        timeout = httpx.Timeout(settings.VIT5_SUMMARIZE_TIMEOUT_S, connect=30.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                self._summarize_url(),
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        summary = data.get("summary")
        if not summary or not str(summary).strip():
            raise ValueError("API tóm tắt trả về summary rỗng")

        return {
            "summary": str(summary).strip(),
            "input_tokens": int(data.get("input_tokens", 0)),
            "output_tokens": int(data.get("output_tokens", 0)),
        }
