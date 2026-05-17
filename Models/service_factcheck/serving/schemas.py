from pydantic import BaseModel


class VerifyRequest(BaseModel):
    claim: str
    evidence: list[str]


class VerifyResponse(BaseModel):
    label: str                  # SUPPORTED | REFUTED | NEI
    confidence: float
    probs: dict[str, float]
    needs_stage2: bool
    threshold: float
    chunks_used: int
