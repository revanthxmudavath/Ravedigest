from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from shared.app_logging.logger import get_logger
from shared.config.settings import get_settings

logger = get_logger("analyzer.filter")

# Get configuration
settings = get_settings()
_KEYWORDS = settings.service.developer_keywords
_THRESHOLD = settings.service.cosine_similarity_threshold

# Initialize vectorizer and keyword embeddings
vectorizer = TfidfVectorizer().fit(_KEYWORDS)
_kw_vecs = vectorizer.transform(_KEYWORDS)
logger.info(
    f"Loaded {len(_KEYWORDS)} keyword embeddings for filtering with threshold {_THRESHOLD}"
)


def mark_developer_focus(title: str, summary: str) -> bool:
    """Check if article has developer focus using keyword matching and cosine similarity."""
    text = (title + " " + summary).lower()
    logger.debug(f"Checking developer focus for text: {text[:100]}...")

    # Stage 1: Direct keyword matching
    for kw in _KEYWORDS:
        if kw.lower() in text:
            logger.debug(f"Keyword '{kw}' found in text.")
            return True

    # Stage 2: Cosine similarity check
    try:
        doc_vec = vectorizer.transform([text])
        sims = cosine_similarity(doc_vec, _kw_vecs).flatten()
        max_sim = sims.max()
        logger.debug(f"Max cosine similarity with keywords: {max_sim:.3f}")

        is_developer_focused = bool(max_sim > _THRESHOLD)
        if is_developer_focused:
            logger.debug(
                f"Article marked as developer-focused (similarity: {max_sim:.3f})"
            )

        return is_developer_focused

    except Exception as e:
        logger.error(f"Error in cosine similarity calculation: {e}")
        return False
