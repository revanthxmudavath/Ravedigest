from openai import OpenAI
from rouge_score import rouge_scorer

from shared.app_logging.logger import get_logger
from shared.config.settings import get_settings
from shared.utils.retry import retry

logger = get_logger("analyzer.summarize")

# Get configuration
settings = get_settings()
_client = OpenAI(api_key=settings.openai.api_key)
_scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

@retry(retryable_exceptions=(Exception,))
def summarize_articles(text: str) -> tuple[str, float]:
    """Summarize article text using OpenAI API with retry logic."""
    logger.debug("Starting article summarization.")
    
    try:
        response = _client.chat.completions.create(
            model=settings.openai.model,
            messages=[{"role": "user", "content": f"Please write a concise summary of the following text:\n\n{text}"}],
            max_tokens=settings.openai.max_tokens,
            temperature=settings.openai.temperature
        )
        summary = response.choices[0].message.content.strip()
        logger.debug("Received summary from OpenAI API.")

    except Exception as e:
        logger.error(f"OpenAI API call failed for article summarization: {e}")
        raise  # Re-raise to trigger retry mechanism
    
    # Calculate relevance score using ROUGE
    try:
        scores = _scorer.score(text, summary)
        relevance = scores["rougeL"].fmeasure
        logger.debug(f"Calculated relevance score: {relevance:.3f}")
    except Exception as e:
        logger.error(f"Error calculating relevance score: {e}")
        relevance = 0.0
    
    return summary, relevance