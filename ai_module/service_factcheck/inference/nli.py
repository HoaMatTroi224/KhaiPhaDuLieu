import numpy as np

from config.settings import settings
from models.model_loader import get_nli_model

# CrossEncoder label order: contradiction=0, entailment=1, neutral=2
_LABEL_MAP = {0: "REFUTED", 1: "SUPPORTED", 2: "NEI"}


def verify(claim: str, evidence_chunks: list[str]) -> dict:
    if not evidence_chunks:
        return {
            "label": "NEI",
            "confidence": 1.0,
            "probs": {"SUPPORTED": 0.0, "REFUTED": 0.0, "NEI": 1.0},
            "needs_stage2": True,
            "threshold": settings.NEI_THRESHOLD,
            "chunks_used": 0,
        }

    model = get_nli_model()
    chunks = evidence_chunks[: settings.MAX_EVIDENCE_CHUNKS]
    pairs = [(claim, chunk) for chunk in chunks]

    # apply_softmax=True → scores đã là probabilities, shape: (n_chunks, 3)
    scores = model.predict(pairs, apply_softmax=True)
    if scores.ndim == 1:
        scores = scores[np.newaxis, :]

    # Aggregate: max cho REFUTED/SUPPORTED (evidence mạnh nhất thắng),
    # mean cho NEI (an toàn hơn — tránh NEI do 1 chunk không liên quan)
    agg = np.array([
        float(np.max(scores[:, 0])),   # contradiction → REFUTED
        float(np.max(scores[:, 1])),   # entailment   → SUPPORTED
        float(np.mean(scores[:, 2])),  # neutral      → NEI
    ])
    agg_probs = agg / agg.sum()  # normalize lại để tổng = 1.0

    pred_idx = int(np.argmax(agg_probs))
    label = _LABEL_MAP[pred_idx]
    confidence = round(float(agg_probs[pred_idx]), 4)

    # Ngưỡng per-label: nếu không đủ chắc → hạ về NEI
    label_threshold = getattr(settings, f"{label}_THRESHOLD")
    if confidence < label_threshold:
        label = "NEI"
        confidence = round(float(agg_probs[2]), 4)

    return {
        "label": label,
        "confidence": confidence,
        "probs": {
            "SUPPORTED": round(float(agg_probs[1]), 4),
            "REFUTED":   round(float(agg_probs[0]), 4),
            "NEI":       round(float(agg_probs[2]), 4),
        },
        "needs_stage2": confidence < settings.CONFIDENCE_THRESHOLD or label == "NEI",
        "threshold": label_threshold,
        "chunks_used": len(chunks),
    }
