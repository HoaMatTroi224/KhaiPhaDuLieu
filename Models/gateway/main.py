import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()

SUMMARIZE_URL = "http://summarize:8001"   
FACTCHECK_URL = "http://factcheck:8002"   


@app.post("/api/v1/summarize")
async def gateway_summarize(request: dict):
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(f"{SUMMARIZE_URL}/api/v1/summarize", json=request)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            raise HTTPException(503, "Summarize service timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)


@app.post("/api/v1/factcheck")
async def gateway_factcheck(request: dict):
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{FACTCHECK_URL}/verify", json=request)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            raise HTTPException(503, "Factcheck service timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
