"""Retry utilities for handling transient failures."""

import time
import logging
from functools import wraps
from typing import Callable, Optional, Type, Union, Tuple

from .exceptions import GrowattError, GrowattAPIError

logger = logging.getLogger(__name__)

def retry_with_backoff(
    retries: int = 3,
    backoff_in_seconds: int = 1,
    max_backoff_in_seconds: int = 30,
    exceptions_to_check: Union[Type[Exception], Tuple[Type[Exception], ...]] = GrowattError,
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        retries: Number of times to retry the wrapped function
        backoff_in_seconds: Initial backoff time in seconds
        max_backoff_in_seconds: Maximum backoff time in seconds
        exceptions_to_check: Exception or tuple of exceptions to catch
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Initialize variables
            attempt = 0
            backoff = min(backoff_in_seconds, max_backoff_in_seconds)
            
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except exceptions_to_check as e:
                    attempt += 1
                    
                    if attempt == retries:
                        logger.error(
                            f"Failed to execute {func.__name__} after {retries} attempts. "
                            f"Final error: {str(e)}"
                        )
                        raise
                    
                    # Calculate next backoff
                    backoff = min(backoff * 2, max_backoff_in_seconds)
                    
                    logger.warning(
                        f"Attempt {attempt} failed for {func.__name__}. "
                        f"Retrying in {backoff} seconds... Error: {str(e)}"
                    )
                    
                    time.sleep(backoff)
            
            return None  # Should never reach here due to raise in last attempt
        
        return wrapper
    
    return decorator