import time 
import logging 
from typing import Callable, Type 
from requests.exceptions import RequestException
from httpx import HTTPStatusError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def retry_with_backoff(
        func: Callable,
        retries: int = 3,
        backoff: float = 1.0,
        exceptions: tuple[Type[Exception], ...] = (RequestException, HTTPStatusError)
        ):
    
    for attempt in range(1, retries + 1):
        try:
            return func()
        except exceptions as e:
            if attempt == retries:
                logger.error("❌ Max retries reached. Failing.")
                raise 
            wait_time = backoff * ( 2 ** (attempt - 1))
            logger.warning( "⚠️ Attempt %d failed: %s. Retrying in %.1fs...", attempt, str(e), wait_time)
            time.sleep(wait_time)