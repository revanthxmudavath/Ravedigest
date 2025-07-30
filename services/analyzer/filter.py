import os
import logging 
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("analyzer.filter")
logger.setLevel(logging.INFO)


_KEYWORDS = ["ai", "machine learning", "deep learning", "neural network", "ai engineering", "developer", "programming", "mcp", "langchain", "openai", "anthropic"]

vectorizer = TfidfVectorizer().fit(_KEYWORDS)
_kw_vecs = vectorizer.transform(_KEYWORDS)
logger.info("Loaded keyword embeddings for filtering.")

def mark_developer_focus(title: str, summary: str) -> bool:
    text = (title + ". " + summary).lower()
    logger.debug(f"Checking developer focus for text: {text}")

    for kw in _KEYWORDS:
        if kw.lower() in text:
            logger.debug(f"Keyword '{kw}' found in text.")
            return True
    
    doc_vec = vectorizer.transform([text])
    sims = cosine_similarity(doc_vec, _kw_vecs).flatten()
    max_sim = sims.max()
    logger.debug(f"Max cosine similarity with keywords: {max_sim:.3f}")


    return bool(max_sim > 0.6)
