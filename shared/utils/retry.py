"""
Retry utilities with exponential backoff for RaveDigest services.
Provides robust error handling and retry mechanisms.
"""

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, Union

from shared.app_logging.logger import get_logger
from shared.config.settings import get_settings

logger = get_logger(__name__)


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for retry attempt with exponential backoff and jitter."""
    delay = config.base_delay * (config.backoff_factor ** attempt)
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        # Add random jitter to prevent thundering herd
        jitter_range = delay * 0.1
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0, delay)


def retry(
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    backoff_factor: Optional[float] = None,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retrying function calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Callback function called on each retry attempt
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            settings = get_settings()
            config = RetryConfig(
                max_retries=max_retries or settings.service.max_retries,
                base_delay=base_delay or settings.service.retry_delay,
                max_delay=max_delay or settings.service.retry_delay * 10,
                backoff_factor=backoff_factor or settings.service.retry_backoff_factor,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions
            )
            
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        logger.error(f"Function {func.__name__} failed after {config.max_retries} retries: {e}")
                        raise RetryError(f"Function {func.__name__} failed after {config.max_retries} retries") from e
                    
                    delay = calculate_delay(attempt, config)
                    logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}. Retrying in {delay:.2f}s")
                    
                    if on_retry:
                        on_retry(e, attempt + 1)
                    
                    
                    time.sleep(delay)
                except Exception as e:
                    # Non-retryable exception, re-raise immediately
                    logger.error(f"Function {func.__name__} failed with non-retryable exception: {e}")
                    raise
            
            # This should never be reached, but just in case
            raise RetryError(f"Function {func.__name__} failed after {config.max_retries} retries") from last_exception
        
        return wrapper
    return decorator


def async_retry(
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    backoff_factor: Optional[float] = None,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retrying async function calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Callback function called on each retry attempt
    
    Returns:
        Decorated async function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            settings = get_settings()
            config = RetryConfig(
                max_retries=max_retries or settings.service.max_retries,
                base_delay=base_delay or settings.service.retry_delay,
                max_delay=max_delay or settings.service.retry_delay * 10,
                backoff_factor=backoff_factor or settings.service.retry_backoff_factor,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions
            )
            
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        logger.error(f"Async function {func.__name__} failed after {config.max_retries} retries: {e}")
                        raise RetryError(f"Async function {func.__name__} failed after {config.max_retries} retries") from e
                    
                    delay = calculate_delay(attempt, config)
                    logger.warning(f"Async function {func.__name__} failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}. Retrying in {delay:.2f}s")
                    
                    if on_retry:
                        on_retry(e, attempt + 1)
                    
                    await asyncio.sleep(delay)
                except Exception as e:
                    # Non-retryable exception, re-raise immediately
                    logger.error(f"Async function {func.__name__} failed with non-retryable exception: {e}")
                    raise
            
            # This should never be reached, but just in case
            raise RetryError(f"Async function {func.__name__} failed after {config.max_retries} retries") from last_exception
        
        return wrapper
    return decorator


def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    **kwargs
) -> Any:
    """
    Execute a function with retry logic and exponential backoff.
    
    Args:
        func: Function to execute
        *args: Arguments to pass to function
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        **kwargs: Keyword arguments to pass to function
    
    Returns:
        Function result
    
    Raises:
        RetryError: If all retry attempts are exhausted
    """
    settings = get_settings()
    config = RetryConfig(
        max_retries=max_retries or settings.service.max_retries,
        base_delay=base_delay or settings.service.retry_delay
    )
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if attempt == config.max_retries:
                logger.error(f"Function {func.__name__} failed after {config.max_retries} retries: {e}")
                raise RetryError(f"Function {func.__name__} failed after {config.max_retries} retries") from e
            
            delay = calculate_delay(attempt, config)
            logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}. Retrying in {delay:.2f}s")
            
            
            time.sleep(delay)
    
    # This should never be reached
    raise RetryError(f"Function {func.__name__} failed after {config.max_retries} retries") from last_exception


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = get_logger("circuit_breaker")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.logger.info("Circuit breaker reset to CLOSED")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
