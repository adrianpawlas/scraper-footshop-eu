import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

logger = logging.getLogger(__name__)

def retry_on_failure(max_attempts: int = 3, backoff_factor: float = 2.0):
    """Decorator for retrying functions on failure."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff_factor),
            retry=retry_if_exception_type((requests.RequestException, Exception)),
            before_sleep=lambda retry_state: logger.warning(
                f"Retrying {func.__name__} in {retry_state.next_action.sleep} seconds "
                f"(attempt {retry_state.attempt_number}/{max_attempts})"
            )
        )
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff_factor),
            retry=retry_if_exception_type((requests.RequestException, Exception)),
            before_sleep=lambda retry_state: logger.warning(
                f"Retrying {func.__name__} in {retry_state.next_action.sleep} seconds "
                f"(attempt {retry_state.attempt_number}/{max_attempts})"
            )
        )
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

class RateLimiter:
    """Simple rate limiter to prevent overwhelming servers."""

    def __init__(self, requests_per_second: float = 1.0):
        self.requests_per_second = requests_per_second
        self.last_request_time = 0
        self.min_interval = 1.0 / requests_per_second

    async def wait_if_needed(self):
        """Wait if necessary to maintain rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()

    def wait_if_needed_sync(self):
        """Synchronous version of wait_if_needed."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            time.sleep(wait_time)

        self.last_request_time = time.time()

def validate_product_data(data: dict) -> bool:
    """Validate that product data has required fields."""
    required_fields = ['id', 'title', 'image_url']

    for field in required_fields:
        if not data.get(field):
            logger.warning(f"Missing required field: {field}")
            return False

    return True

def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize string by removing problematic characters."""
    if not text:
        return ""

    # Remove null bytes and other problematic characters
    sanitized = text.replace('\x00', '').replace('\r', ' ').replace('\n', ' ')

    # Strip whitespace
    sanitized = sanitized.strip()

    # Truncate if too long
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length - 3] + "..."

    return sanitized

def chunk_list(lst: list, chunk_size: int):
    """Split a list into chunks of specified size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]
