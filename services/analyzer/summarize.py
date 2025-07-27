import os 
import logging 
import trafilatura
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("analyzer.summarize")
logger.setLevel(logging.INFO)

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize_articles(text: str) -> tuple[str, float]:
    logger.debug("Starting article summarization.")
    try:
        response = _client.chat.completions.create(
            model= os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": f"Please write a concise summary of the following text:\n\n{text}"}],
        )
        summary = response.choices[0].message.content.strip()
        logger.debug("Received summary from OpenAI API.")
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {e}")
        summary = ""
    
    relevance = float(len(summary)) / max(1, len(text))  # To be improved wuith Cosine Similarity TF-IDF
    logger.info("Computed relevance score.")
    return summary, relevance