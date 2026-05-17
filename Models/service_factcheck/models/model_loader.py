import logging
from functools import lru_cache

from sentence_transformers import CrossEncoder

from config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_nli_model() -> CrossEncoder:
    logger.info("Loading NLI model: %s", settings.NLI_MODEL)
    model = CrossEncoder(settings.NLI_MODEL)
    logger.info("NLI model ready")
    return model
