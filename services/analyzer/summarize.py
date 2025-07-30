import os 
import logging 
from openai import OpenAI
from dotenv import load_dotenv
from rouge_score import rouge_scorer

load_dotenv()

logger = logging.getLogger("analyzer.summarize")
logger.setLevel(logging.INFO)

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)


def summarize_articles(text: str) -> tuple[str, float]:
    logger.debug("Starting article summarization.")
    try:
        response = _client.chat.completions.create(
            model= os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            messages=[{"role": "user", "content": f"Please write a concise summary of the following text:\n\n{text}"}],
        )
        summary = response.choices[0].message.content.strip()
        logger.debug("Received summary from OpenAI API.")
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {e}")
        summary = ""
    
    scores = _scorer.score(text, summary)
    relevance = scores["rougeL"].fmeasure
    logger.debug(f"Calculated relevance score: {relevance:.3f}")
    return summary, relevance